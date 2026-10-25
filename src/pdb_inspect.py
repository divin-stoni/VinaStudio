# -*- coding: utf-8 -*-
"""
pdb_inspect.py

Inspection et nettoyage d'un PDB brut pour le docking (sans Qt).

- inspect_pdb : fiche de la structure (titre, methode, resolution, chaines,
  chaines identiques, residus manquants, eaux, ions, ligands, chaine liante).
- write_clean_pdb : ne garde que les chaines choisies, une seule conformation
  alternative, le premier modele, MSE converti en MET, sans eau ni ligands.
- convert_to_pdbqt : conversion Open Babel (executable embarque ou PATH).
"""

from __future__ import annotations

import difflib
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from src.grid_fit import _NOT_LIGAND, _WATER

CONTACT_CUTOFF = 4.5
MIN_LIGAND_ATOMS = 6

_IONS = {
    "NA", "K", "CL", "MG", "ZN", "CA", "MN", "FE", "FE2", "CU", "CU1", "NI",
    "CO", "CD", "BR", "IOD", "HG", "LI", "RB", "CS", "SR", "BA", "YB", "PT",
    "AU", "AG",
}
_AA3_TO_1 = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C", "GLN": "Q",
    "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I", "LEU": "L", "LYS": "K",
    "MET": "M", "PHE": "F", "PRO": "P", "SER": "S", "THR": "T", "TRP": "W",
    "TYR": "Y", "VAL": "V", "HID": "H", "HIE": "H", "HIP": "H", "CYX": "C",
    "ASH": "D", "GLH": "E", "LYN": "K",
}
_MODRES = {
    "MSE": "M", "SEP": "S", "TPO": "T", "PTR": "Y", "CSO": "C", "CME": "C",
    "HYP": "P", "MLY": "K", "M3L": "K", "KCX": "K", "LLP": "K", "PCA": "Q",
    "CSD": "C", "OCS": "C", "SMC": "C", "ALY": "K", "FME": "M",
}


@dataclass
class ChainInfo:
    chain: str
    molecule: str = ""
    n_res: int = 0
    n_atoms: int = 0
    seq: str = ""
    missing: int = 0
    group: int = 0
    contacts: dict = field(default_factory=dict)


@dataclass
class LigandInfo:
    key: str
    resname: str
    chain: str
    num: int
    n_atoms: int
    name: str
    xyz: np.ndarray
    best_chain: str = ""
    best_contacts: int = 0

    @property
    def label(self) -> str:
        return f"{self.resname} {self.num} (chaîne {self.chain})"


@dataclass
class PdbReport:
    path: str
    title: str = ""
    method: str = ""
    resolution: float | None = None
    organism: str = ""
    chains: dict = field(default_factory=dict)
    ligands: list = field(default_factory=list)
    n_water: int = 0
    ions: dict = field(default_factory=dict)
    additives: dict = field(default_factory=dict)
    modified: dict = field(default_factory=dict)
    altloc_residues: int = 0
    has_h: bool = False
    n_models: int = 1
    mutation: bool = False
    warnings: list = field(default_factory=list)
    suggested_chains: list = field(default_factory=list)
    suggested_ligand: str = ""

    def ligand_by_key(self, key):
        for lig in self.ligands:
            if lig.key == key:
                return lig
        return None

    def one_per_group(self) -> list:
        seen, out = set(), []
        for c in self.chains.values():
            if c.group not in seen:
                seen.add(c.group)
                out.append(c.chain)
        return out


# ------------------------------------------------------------------ outils
def _kv_records(lines):
    text = " ".join(l.strip() for l in lines)
    out, cur = [], {}
    for tok in text.split(";"):
        tok = tok.strip()
        if ":" not in tok:
            continue
        k, v = tok.split(":", 1)
        k, v = k.strip().upper(), v.strip()
        if k == "MOL_ID":
            if cur:
                out.append(cur)
            cur = {}
        cur[k] = v
    if cur:
        out.append(cur)
    return out


def _count_contacts(coords, lig, cutoff=CONTACT_CUTOFF) -> int:
    if len(coords) == 0 or len(lig) == 0:
        return 0
    c2 = cutoff * cutoff
    n = 0
    for i in range(0, len(coords), 2000):
        blk = coords[i:i + 2000]
        d2 = ((blk[:, None, :] - lig[None, :, :]) ** 2).sum(axis=2)
        n += int((d2.min(axis=1) <= c2).sum())
    return n


def _similar(a: str, b: str) -> bool:
    if a == b:
        return True
    if not a or not b or min(len(a), len(b)) < 20:
        return False
    if abs(len(a) - len(b)) > 0.1 * max(len(a), len(b)):
        return False
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio() >= 0.97


def _group_chains(chains: dict) -> None:
    reps = []
    for ch in chains.values():
        gid = None
        for g, s in reps:
            if _similar(ch.seq, s):
                gid = g
                break
        if gid is None:
            gid = len(reps) + 1
            reps.append((gid, ch.seq))
        ch.group = gid


# --------------------------------------------------------------- inspection
def inspect_pdb(path) -> PdbReport:
    path = Path(path)
    rep = PdbReport(path=str(path))
    title, expdta, compnd, source = [], [], [], []
    hetnam, missing = {}, {}
    in465 = False
    res_order, res_seen, chain_xyz = {}, {}, {}
    het_groups = {}
    mod_keys = {}
    altloc_keys = set()
    n_models = 0

    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            rec = line[:6]
            if rec == "TITLE ":
                title.append(line[10:80].strip())
            elif rec == "EXPDTA":
                expdta.append(line[10:80].strip())
            elif rec == "COMPND":
                compnd.append(line[10:80].rstrip("\r\n"))
            elif rec == "SOURCE":
                source.append(line[10:80].rstrip("\r\n"))
            elif rec == "HETNAM":
                hid = line[11:14].strip()
                if hid:
                    hetnam[hid] = (hetnam.get(hid, "") + " " + line[15:70].strip()).strip()
            elif rec == "REMARK":
                num = line[7:10].strip()
                if num == "2":
                    m = re.search(r"RESOLUTION\.\s+([0-9]+\.?[0-9]*)", line)
                    if m:
                        rep.resolution = float(m.group(1))
                elif num == "465":
                    if re.search(r"RES\s+C\s+SSSEQ", line):
                        in465 = True
                    elif in465:
                        m = re.match(
                            r"REMARK 465\s+(?:\d+\s+)?([A-Z0-9]{2,3})\s+(\S)\s+(-?\d+)\w?\s*$",
                            line,
                        )
                        if m:
                            missing[m.group(2)] = missing.get(m.group(2), 0) + 1
            elif rec == "MODEL ":
                n_models += 1
            elif rec == "ENDMDL":
                break
            elif rec == "ATOM  " or rec == "HETATM":
                if len(line) < 54:
                    continue
                try:
                    x = float(line[30:38])
                    y = float(line[38:46])
                    z = float(line[46:54])
                    resnum = int(line[22:26])
                except ValueError:
                    continue
                het = rec == "HETATM"
                atom = line[12:16].strip().upper()
                alt = line[16:17]
                resname = line[17:20].strip().upper()
                chain = line[21:22].strip() or "_"
                icode = line[26:27].strip()
                elem = line[76:78].strip().upper() if len(line) >= 78 else ""
                if elem:
                    is_h = elem in ("H", "D")
                else:
                    is_h = bool(re.match(r"^\d?H", atom)) and resname not in _IONS
                if is_h:
                    rep.has_h = True
                if alt.strip():
                    altloc_keys.add((chain, resnum, icode))

                if het and resname not in _MODRES:
                    g = het_groups.setdefault(
                        (resname, chain, resnum, icode), {"xyz": []})
                    g["xyz"].append((x, y, z))
                    continue

                key = (chain, resnum, icode)
                seen = res_seen.setdefault(chain, set())
                if key not in seen:
                    seen.add(key)
                    res_order.setdefault(chain, []).append(resname)
                    if het:
                        mod_keys.setdefault(resname, set()).add(key)
                chain_xyz.setdefault(chain, []).append((x, y, z))

    rep.n_models = max(1, n_models)
    rep.title = " ".join(title).strip()
    rep.method = "; ".join(e for e in expdta if e).strip()
    rep.altloc_residues = len(altloc_keys)
    rep.modified = {k: len(v) for k, v in mod_keys.items()}

    mol_by_chain = {}
    for r in _kv_records(compnd):
        chs = [c.strip() for c in r.get("CHAIN", "").split(",") if c.strip()]
        for c in chs:
            mol_by_chain[c] = r.get("MOLECULE", "")
        if r.get("MUTATION", "").upper().startswith("YES"):
            rep.mutation = True
    for r in _kv_records(source):
        if r.get("ORGANISM_SCIENTIFIC"):
            rep.organism = r["ORGANISM_SCIENTIFIC"].title()
            break

    for c, names in res_order.items():
        seq = "".join(_AA3_TO_1.get(n) or _MODRES.get(n) or "X" for n in names)
        rep.chains[c] = ChainInfo(
            chain=c,
            molecule=mol_by_chain.get(c, "").title(),
            n_res=len(names),
            n_atoms=len(chain_xyz.get(c, [])),
            seq=seq,
            missing=missing.get(c, 0),
        )
    _group_chains(rep.chains)

    ligands = []
    for (resname, chain, num, icode), g in het_groups.items():
        n = len(g["xyz"])
        if resname in _WATER:
            rep.n_water += 1
        elif resname in _IONS or n == 1:
            rep.ions[resname] = rep.ions.get(resname, 0) + 1
        elif resname in _NOT_LIGAND or n < MIN_LIGAND_ATOMS:
            rep.additives[resname] = rep.additives.get(resname, 0) + 1
        else:
            ligands.append(LigandInfo(
                key=f"{resname}:{chain}:{num}{icode}",
                resname=resname, chain=chain, num=num, n_atoms=n,
                name=hetnam.get(resname, "").title(),
                xyz=np.asarray(g["xyz"], dtype=float),
            ))
    ligands.sort(key=lambda l: -l.n_atoms)
    rep.ligands = ligands[:12]

    arrays = {c: np.asarray(v, dtype=float) for c, v in chain_xyz.items()}
    for lig in rep.ligands:
        best, best_n = "", 0
        for c, arr in arrays.items():
            n = _count_contacts(arr, lig.xyz)
            if n and c in rep.chains:
                rep.chains[c].contacts[lig.key] = n
            if n > best_n:
                best, best_n = c, n
        lig.best_chain, lig.best_contacts = best, best_n

    # suggestions
    big = [c for c in rep.chains.values() if c.n_res >= 30] or list(rep.chains.values())
    bound = [l for l in rep.ligands if l.best_contacts > 0]
    if bound:
        rep.suggested_ligand = bound[0].key
        rep.suggested_chains = [bound[0].best_chain]
    else:
        if rep.ligands:
            rep.suggested_ligand = rep.ligands[0].key
        firsts = []
        seen_groups = set()
        for c in big:
            if c.group not in seen_groups:
                seen_groups.add(c.group)
                firsts.append(c.chain)
        rep.suggested_chains = firsts

    # avertissements
    if rep.resolution is not None and rep.resolution > 3.5:
        rep.warnings.append(
            f"Résolution faible ({rep.resolution:.2f} Å) : positions des chaînes latérales peu fiables.")
    if rep.n_models > 1:
        rep.warnings.append(
            f"Structure à {rep.n_models} modèles (RMN) : seul le premier sera utilisé.")
    miss = [f"{c.chain} ({c.missing})" for c in rep.chains.values() if c.missing]
    if miss:
        rep.warnings.append("Résidus non résolus (boucles manquantes) : " + ", ".join(miss) + ".")
    if rep.altloc_residues:
        rep.warnings.append(
            f"{rep.altloc_residues} résidu(s) avec conformations alternatives : une seule sera gardée.")
    if rep.mutation:
        rep.warnings.append("La structure contient des mutations par rapport à la séquence native.")
    if rep.has_h:
        rep.warnings.append("Le fichier contient déjà des hydrogènes.")
    if not rep.ligands:
        rep.warnings.append(
            "Aucun ligand co-cristallisé : la grid box sera centrée sur la protéine, "
            "à placer ensuite avec « Ajustement précis ».")
    return rep


# ----------------------------------------------------------------- nettoyage
def _mse_to_met(line: str) -> str:
    out = "ATOM  " + line[6:17] + "MET" + line[20:]
    if out[12:16].strip().upper() == "SE":
        out = out[:12] + " SD " + out[16:]
    if len(out) >= 78 and out[76:78].strip().upper() == "SE":
        out = out[:76] + " S" + out[78:]
    return out


def write_clean_pdb(src, dst, chains, convert_mse=True, single_altloc=True) -> dict:
    keep = set(chains)
    kept = []
    stats = {
        "atoms": 0, "hetero_removed": 0, "water_removed": 0,
        "altloc_dropped": 0, "mse_converted": 0, "other_chain_atoms": 0,
        "models_ignored": False,
    }
    chosen_alt = {}
    with open(src, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            rec = line[:6]
            if rec == "ENDMDL":
                stats["models_ignored"] = True
                break
            if rec == "ATOM  " or rec == "HETATM":
                chain = line[21:22].strip() or "_"
                resname = line[17:20].strip().upper()
                if rec == "HETATM":
                    if resname == "MSE" and convert_mse and chain in keep:
                        line = _mse_to_met(line)
                        stats["mse_converted"] += 1
                    elif resname in _WATER:
                        stats["water_removed"] += 1
                        continue
                    else:
                        stats["hetero_removed"] += 1
                        continue
                if chain not in keep:
                    stats["other_chain_atoms"] += 1
                    continue
                alt = line[16:17]
                if single_altloc and alt.strip():
                    key = (chain, line[22:27])
                    chosen = chosen_alt.setdefault(key, alt)
                    if alt != chosen:
                        stats["altloc_dropped"] += 1
                        continue
                    line = line[:16] + " " + line[17:]
                if not line.endswith("\n"):
                    line += "\n"
                kept.append(line)
                stats["atoms"] += 1
            elif rec.startswith("TER"):
                ch = line[21:22].strip()
                if not ch or ch in keep:
                    kept.append("TER\n")
    kept.append("END\n")
    Path(dst).write_text("".join(kept), encoding="utf-8")
    return stats


def convert_to_pdbqt(clean_pdb, pdbqt, protonate=False):
    """(ok, message). Open Babel : runtime embarque ou PATH, sans fenetre console."""
    from src import mol3d
    exe, env = mol3d.find_obabel()
    if not exe:
        return False, ("Open Babel (obabel) est introuvable : ni dans obabel_runtime, "
                       "ni dans le PATH.")
    cmd = [exe, str(clean_pdb), "-O", str(pdbqt), "-xr", "--partialcharge", "gasteiger"]
    if protonate:
        cmd += ["-p", "7.4"]
    extra = {"stdin": subprocess.DEVNULL}
    if sys.platform.startswith("win"):
        extra["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                            timeout=120, env=env, **extra)
    except subprocess.TimeoutExpired:
        return False, "Open Babel a dépassé le délai de 120 s."
    except OSError as exc:
        return False, f"Lancement d'Open Babel impossible ({type(exc).__name__}: {exc})."
    if cp.returncode != 0 or not Path(pdbqt).exists():
        return False, "Open Babel n'a pas pu convertir le fichier nettoyé en PDBQT :\n\n" + (
            cp.stderr.strip() or "(pas de détail)")
    try:
        from src.docking.receptor_validator import validate_receptor_pdbqt
        _rep = validate_receptor_pdbqt(pdbqt, fix=True)
    except Exception:
        _rep = None
    if _rep is not None and not _rep["ok"]:
        return False, ("Le récepteur converti n'est pas utilisable par Vina :\n\n"
                       + "\n".join(_rep["errors"]))
    return True, ""


def write_import_report(path, report, choice, stats, ligand=None, box=None):
    L = ["Rapport d'import du récepteur", ""]
    L.append(f"Fichier source : {report.path}")
    if report.title:
        L.append(f"Titre : {report.title}")
    if report.method:
        L.append("Méthode : " + report.method
                 + (f" ; résolution {report.resolution:.2f} Å" if report.resolution else ""))
    if report.organism:
        L.append(f"Organisme : {report.organism}")
    L += ["", "Chaînes conservées : " + ", ".join(choice["chains"]),
          f"Atomes conservés : {stats['atoms']}", "", "Retiré ou modifié :"]
    L.append(f"  eaux retirées : {stats['water_removed']} atome(s)")
    L.append(f"  autres hétéroatomes (ions, ligands, additifs) retirés : {stats['hetero_removed']} atome(s)")
    L.append(f"  atomes d'autres chaînes retirés : {stats['other_chain_atoms']}")
    L.append(f"  conformations alternatives écartées : {stats['altloc_dropped']} atome(s)")
    L.append(f"  sélénométhionine convertie en méthionine : {stats['mse_converted']} atome(s)")
    if stats["models_ignored"]:
        L.append("  modèles suivants ignorés (premier modèle seul)")
    L.append("  hydrogènes ajoutés à la conversion : " + ("oui (pH 7,4)" if choice["protonate"] else "non"))
    if ligand is not None and box is not None:
        L += ["", f"Grid box proposée autour du ligand {ligand.label} ({ligand.name or 'nom inconnu'})",
              f"  marge : {choice['margin']:.1f} Å",
              "  centre : " + ", ".join(f"{v:.2f}" for v in box["center"]),
              "  taille : " + ", ".join(f"{v:.1f}" for v in box["size"])]
    else:
        L += ["", "Grid box : centroïde de la protéine (aucun ligand choisi), à ajuster."]
    Path(path).write_text("\n".join(L) + "\n", encoding="utf-8")
    return path
