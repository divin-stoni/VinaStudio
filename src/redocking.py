# -*- coding: utf-8 -*-
"""
redocking.py

Validation d'un recepteur par re-docking du ligand co-cristallise (sans Qt).

Etapes : extraction du ligand depuis le PDB d'origine -> PDBQT (Open Babel,
hydrogenes ajoutes) -> Vina avec la grid box et les parametres du profil ->
RMSD sur les atomes lourds, sans superposition, contre la pose du cristal.

Limite connue : le RMSD est calcule atome par atome dans l'ordre du PDBQT.
Pour un ligand symetrique (cycle retourne), il peut etre surestime.
Aucun appariement automatique n'est fait : il minimiserait le RMSD sans
respecter les liaisons et donnerait un resultat trop optimiste.

Utilisation :
    python -m src.redocking receptor_profiles/acrb_site2_ecoli.json
    python -m src.redocking receptor_profiles/acrb_site2_ecoli.json --ligand ET:A:3002
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

RMSD_THRESHOLD = 2.0
_H_TYPES = {"H", "HD", "HS"}


@dataclass
class RedockingResult:
    ok: bool
    message: str = ""
    passed: bool = False
    rmsd_top: float | None = None
    rmsd_best: float | None = None
    best_mode_index: int | None = None
    affinity_top: float | None = None
    n_heavy: int = 0
    n_modes: int = 0
    duration: float = 0.0
    out_pdbqt: str = ""
    reference_pdb: str = ""
    warnings: list = field(default_factory=list)
    center_dist_top: float | None = None
    n_site: int = 0
    frac_2a_top: float | None = None

    def summary(self) -> str:
        if not self.ok:
            return "Re-docking impossible : " + self.message
        verdict = "VALIDE" if self.passed else "NON VALIDE"
        txt = (f"{verdict} : RMSD pose n°1 = {self.rmsd_top:.2f} Å "
               f"(seuil {RMSD_THRESHOLD:.1f} Å) ; meilleur RMSD parmi "
               f"{self.n_modes} poses = {self.rmsd_best:.2f} Å (pose {self.best_mode_index}) ; "
               f"score pose n°1 = {self.affinity_top:.2f} kcal/mol ; "
               f"{self.n_heavy} atomes lourds comparés.")
        for w in self.warnings:
            txt += "\n  ⚠ " + w
        return txt


# ---------------------------------------------------------------- ligand
def extract_ligand_pdb(src, key: str, dst) -> int:
    """Ecrit dans dst les HETATM du ligand `RESNAME:CHAINE:NUM[ICODE]`
    (une seule conformation alternative). Retourne le nombre d'atomes."""
    try:
        resname, chain, numicode = key.split(":")
    except ValueError:
        raise ValueError(f"Cle de ligand invalide : {key!r} (attendu RES:CHAINE:NUM)")
    out, alt_chosen = [], None
    with open(src, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            rec = line[:6]
            if rec == "ENDMDL":
                break
            if rec != "HETATM":
                continue
            if line[17:20].strip().upper() != resname.upper():
                continue
            if (line[21:22].strip() or "_") != chain:
                continue
            if (line[22:26].strip() + line[26:27].strip()) != numicode:
                continue
            alt = line[16:17]
            if alt.strip():
                if alt_chosen is None:
                    alt_chosen = alt
                elif alt != alt_chosen:
                    continue
                line = line[:16] + " " + line[17:]
            out.append(line if line.endswith("\n") else line + "\n")
    if out:
        out.append("END\n")
        Path(dst).write_text("".join(out), encoding="utf-8")
    return len(out) - 1 if out else 0


def ligand_pdb_to_pdbqt(pdb, pdbqt):
    """(ok, message). Open Babel, hydrogenes ajoutes, charges Gasteiger."""
    from src.tools.obabel_locator import resolve_obabel_executable, obabel_subprocess_env
    exe = resolve_obabel_executable()
    if exe == "obabel":
        exe = shutil.which("obabel") or exe
    cmd = [exe, str(pdb), "-O", str(pdbqt), "-h", "--partialcharge", "gasteiger"]
    extra = {}
    if sys.platform.startswith("win"):
        extra["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                            timeout=120, env=obabel_subprocess_env(),
                            stdin=subprocess.DEVNULL, **extra)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Open Babel : {type(exc).__name__}: {exc}"
    if cp.returncode != 0 or not Path(pdbqt).exists() or Path(pdbqt).stat().st_size == 0:
        return False, "Open Babel n'a pas converti le ligand : " + (cp.stderr.strip() or "(pas de détail)")
    return True, ""


# ----------------------------------------------------------------- pdbqt
def read_pdbqt_models(path):
    """Liste de (affinite|None, coordonnees des atomes lourds) par modele.
    Un fichier sans MODEL (ligand d'entree) donne un seul modele."""
    models, cur, aff = [], None, None
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if line.startswith("MODEL"):
                cur, aff = [], None
            elif line.startswith("REMARK VINA RESULT"):
                try:
                    aff = float(line.split()[3])
                except (IndexError, ValueError):
                    aff = None
            elif line.startswith(("ATOM", "HETATM")):
                parts = line.split()
                if not parts or parts[-1] in _H_TYPES:
                    continue
                try:
                    xyz = (float(line[30:38]), float(line[38:46]), float(line[46:54]))
                except ValueError:
                    continue
                if cur is None:
                    cur = []
                cur.append(xyz)
            elif line.startswith("ENDMDL"):
                if cur is not None:
                    models.append((aff, np.asarray(cur, dtype=float)))
                cur, aff = None, None
    if cur:
        models.append((aff, np.asarray(cur, dtype=float)))
    return models


def rmsd(a, b) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.shape != b.shape or len(a) == 0:
        raise ValueError(f"Formes differentes : {a.shape} et {b.shape}")
    return float(np.sqrt(((a - b) ** 2).sum(axis=1).mean()))


# ------------------------------------------------------------------ vina
_COV_RADIUS = {"C": 0.76, "N": 0.71, "O": 0.66, "S": 1.05, "P": 1.07,
               "F": 0.57, "Cl": 1.02, "Br": 1.20, "I": 1.39}
_ADTYPE_ELEMENT = {"A": "C", "NA": "N", "OA": "O", "SA": "S"}
_MAX_AUTOMORPHISMS = 5000


def read_pdbqt_heavy_types(path):
    """Types AutoDock des atomes lourds du premier modele (meme ordre que read_pdbqt_models)."""
    types, started = [], False
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if line.startswith(("ATOM", "HETATM")):
                parts = line.split()
                if not parts or parts[-1] in _H_TYPES:
                    continue
                types.append(parts[-1])
                started = True
            elif started and line.startswith("ENDMDL"):
                break
    return types


def _bond_matrix(xyz, types):
    n = len(types)
    rad = np.array([_COV_RADIUS.get(_ADTYPE_ELEMENT.get(t, t), 0.8) for t in types])
    d = np.linalg.norm(xyz[:, None, :] - xyz[None, :, :], axis=2)
    adj = d < 1.15 * (rad[:, None] + rad[None, :])
    np.fill_diagonal(adj, False)
    return adj


def _automorphisms(types, adj, cap=_MAX_AUTOMORPHISMS):
    """Permutations des atomes qui conservent types et liaisons (retour arriere, plafonne)."""
    n = len(types)
    deg = adj.sum(axis=1)
    order, seen = [], set()
    for start in range(n):
        if start in seen:
            continue
        queue = [start]
        seen.add(start)
        while queue:
            u = queue.pop(0)
            order.append(u)
            for v in np.nonzero(adj[u])[0]:
                if int(v) not in seen:
                    seen.add(int(v))
                    queue.append(int(v))
    results, mapping, used = [], {}, set()

    def rec(k):
        if len(results) >= cap:
            return
        if k == n:
            results.append([mapping[i] for i in range(n)])
            return
        i = order[k]
        for j in range(n):
            if j in used or types[j] != types[i] or deg[j] != deg[i]:
                continue
            if all(adj[i][a] == adj[j][mapping[a]] for a in mapping):
                mapping[i] = j
                used.add(j)
                rec(k + 1)
                del mapping[i]
                used.discard(j)

    rec(0)
    return np.asarray(results, dtype=int) if results else np.arange(n)[None, :]


def rmsd_symmetric(ref_xyz, types, poses_xyz):
    """RMSD sans superposition, minimum sur les permutations d'atomes equivalents
    (memes types, memes liaisons). Les liaisons viennent du ligand du cristal.
    Retourne (liste de RMSD, nombre de permutations testees)."""
    ref_xyz = np.asarray(ref_xyz, float)
    perms = _automorphisms(types, _bond_matrix(ref_xyz, types))
    out = []
    for xyz in poses_xyz:
        xyz = np.asarray(xyz, float)
        diff = xyz[perms] - ref_xyz[None, :, :]
        out.append(float(np.sqrt((diff ** 2).sum(axis=2).mean(axis=1)).min()))
    return out, len(perms)


SITE_RADIUS = 3.0


def atom_fraction_within(ref_xyz, types, xyz, cutoff=2.0):
    """Part des atomes a moins de `cutoff` A du cristal, pour la permutation
    d'atomes equivalents qui minimise le RMSD (pas de superposition)."""
    ref_xyz = np.asarray(ref_xyz, float)
    xyz = np.asarray(xyz, float)
    perms = _automorphisms(types, _bond_matrix(ref_xyz, types))
    d = np.sqrt(((xyz[perms] - ref_xyz[None, :, :]) ** 2).sum(axis=2))
    best = int(np.sqrt((d ** 2).mean(axis=1)).argmin())
    return float((d[best] <= cutoff).mean())


def run_vina(receptor, ligand_pdbqt, center, size, params, out_pdbqt, timeout=3600):
    from src.docking.vina_engine import resolve_vina_executable
    exe = resolve_vina_executable()
    exe = shutil.which(exe) or exe
    cmd = [exe, "--receptor", str(receptor), "--ligand", str(ligand_pdbqt),
           "--center_x", str(center[0]), "--center_y", str(center[1]), "--center_z", str(center[2]),
           "--size_x", str(size[0]), "--size_y", str(size[1]), "--size_z", str(size[2]),
           "--exhaustiveness", str(params.get("exhaustiveness", 32)),
           "--num_modes", str(params.get("num_modes", 9)),
           "--energy_range", str(params.get("energy_range", 3.0)),
           "--seed", str(params.get("seed", 2024)),
           "--out", str(out_pdbqt), "--verbosity", "1"]
    if int(params.get("cpu", 0) or 0) > 0:
        cmd += ["--cpu", str(int(params["cpu"]))]
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=timeout, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Vina : {type(exc).__name__}: {exc}"
    if cp.returncode != 0 or not Path(out_pdbqt).exists():
        tail = (cp.stdout or cp.stderr or "").strip()[-600:]
        return False, f"Vina a échoué (code {cp.returncode}) : {tail}"
    return True, ""


# ---------------------------------------------------------------- coeur
def redock(receptor_pdbqt, center, size, params, source_pdb, ligand_key, workdir) -> RedockingResult:
    t0 = time.perf_counter()
    work = Path(workdir)
    work.mkdir(parents=True, exist_ok=True)
    tag = ligand_key.replace(":", "_")

    ref_pdb = work / f"{tag}_cristal.pdb"
    n = extract_ligand_pdb(source_pdb, ligand_key, ref_pdb)
    if n == 0:
        return RedockingResult(False, f"ligand {ligand_key} introuvable dans {source_pdb}.")

    lig_pdbqt = work / f"{tag}_cristal.pdbqt"
    ok, msg = ligand_pdb_to_pdbqt(ref_pdb, lig_pdbqt)
    if not ok:
        return RedockingResult(False, msg)
    ref_models = read_pdbqt_models(lig_pdbqt)
    if not ref_models:
        return RedockingResult(False, "le PDBQT du ligand ne contient aucun atome lourd.")
    ref_xyz = ref_models[0][1]
    ref_types = read_pdbqt_heavy_types(lig_pdbqt)

    res = RedockingResult(True, n_heavy=len(ref_xyz), reference_pdb=str(ref_pdb))
    half = np.asarray(size, float) / 2.0
    if (np.abs(ref_xyz - np.asarray(center, float)) > half).any():
        res.warnings.append("une partie du ligand du cristal est hors de la grid box : "
                            "le re-docking ne peut pas le retrouver entièrement.")

    out_pdbqt = work / f"{tag}_redock_out.pdbqt"
    ok, msg = run_vina(receptor_pdbqt, lig_pdbqt, center, size, params, out_pdbqt)
    if not ok:
        return RedockingResult(False, msg)
    res.out_pdbqt = str(out_pdbqt)

    poses = read_pdbqt_models(out_pdbqt)
    if not poses:
        return RedockingResult(False, "aucune pose dans la sortie de Vina.")
    if any(len(xyz) != len(ref_xyz) for _, xyz in poses):
        return RedockingResult(False, "nombre d'atomes lourds différent entre le ligand et les poses.")

    ordered = [rmsd(xyz, ref_xyz) for _, xyz in poses]
    try:
        values, n_perm = rmsd_symmetric(ref_xyz, ref_types, [xyz for _, xyz in poses])
        values = [min(a, b) for a, b in zip(values, ordered)]
    except Exception:
        values, n_perm = ordered, 1
    if n_perm > 1 and abs(values[0] - ordered[0]) > 0.01:
        res.warnings.append(
            f"RMSD tenant compte des symétries du ligand ({n_perm} permutations d'atomes "
            f"équivalents testées) : {values[0]:.2f} Å contre {ordered[0]:.2f} Å dans l'ordre "
            "strict des atomes.")
    best = int(np.argmin(values))
    res.n_modes = len(poses)
    try:
        _cd = [float(np.linalg.norm(xyz.mean(axis=0) - ref_xyz.mean(axis=0))) for _, xyz in poses]
        res.center_dist_top = _cd[0]
        res.n_site = sum(1 for c in _cd if c < SITE_RADIUS)
        res.frac_2a_top = atom_fraction_within(ref_xyz, ref_types, poses[0][1], RMSD_THRESHOLD)
    except Exception:
        pass
    res.rmsd_top = values[0]
    res.rmsd_best = values[best]
    res.best_mode_index = best + 1
    res.affinity_top = poses[0][0]
    res.passed = values[0] < RMSD_THRESHOLD
    res.duration = time.perf_counter() - t0
    if not res.passed and res.rmsd_best < RMSD_THRESHOLD:
        res.warnings.append("la bonne pose existe parmi les modes mais n'est pas classée première : "
                            "la fonction de score ne la favorise pas pour ce site.")
    return res


# ------------------------------------------------------------------- CLI
def _download_pdb(code, dest_dir):
    import requests
    resp = requests.get(f"https://files.rcsb.org/download/{code}.pdb", timeout=30,
                        headers={"User-Agent": "VinaStudio"})
    if resp.status_code != 200:
        raise RuntimeError(f"RCSB : HTTP {resp.status_code} pour {code}")
    dest = Path(dest_dir) / f"{code}.pdb"
    dest.write_bytes(resp.content)
    return dest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validation d'un profil par re-docking.")
    ap.add_argument("profile", help="fichier JSON du profil (receptor_profiles/*.json)")
    ap.add_argument("--pdb", help="PDB d'origine (sinon téléchargé via source_pdb)")
    ap.add_argument("--ligand", help="ligand de référence, ex. ET:A:3002 (sinon liste)")
    ap.add_argument("--workdir", help="dossier de travail")
    ap.add_argument("--cpu", type=int, help="remplace le nombre de CPU du profil")
    args = ap.parse_args(argv)

    data = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    work = Path(args.workdir or Path("redocking_runs") / data["profile_id"])
    work.mkdir(parents=True, exist_ok=True)

    pdb = Path(args.pdb) if args.pdb else None
    if pdb is None:
        code = (data.get("source_pdb") or "").strip().upper()
        if not code:
            print("Pas de source_pdb dans le profil : donne --pdb.")
            return 2
        print(f"Téléchargement de {code}…")
        pdb = _download_pdb(code, work)

    if not args.ligand:
        from src import pdb_inspect
        rep = pdb_inspect.inspect_pdb(pdb)
        print("Ligands trouvés (relance avec --ligand CLE) :")
        for lig in rep.ligands:
            print(f"  {lig.key:<16} {lig.n_atoms:>3} atomes, chaîne liante {lig.best_chain or '?'}"
                  f" ({lig.best_contacts} contacts) {lig.name}")
        return 0

    receptor = Path(data["pdbqt_path"])
    if not receptor.is_absolute():
        receptor = Path.cwd() / receptor
    params = dict(data.get("docking_params") or {})
    if args.cpu is not None:
        params["cpu"] = args.cpu
    box = data["grid_box"]
    print(f"Re-docking de {args.ligand} dans {receptor.name} (exhaustiveness "
          f"{params.get('exhaustiveness', 32)})… cela peut prendre plusieurs minutes.")
    res = redock(receptor, box["center"], box["size"], params, pdb, args.ligand, work)
    print(res.summary())
    if res.ok:
        print(f"Fichiers : {work}")
    return 0 if res.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
