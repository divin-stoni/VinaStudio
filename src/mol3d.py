# -*- coding: utf-8 -*-
"""
mol3d.py

Generation 3D locale autonome (aucun serveur, rien a installer a part).

Moteurs essayes dans l'ordre, molecule par molecule restante :
  1. Open Babel (executable obabel, runtime embarque ou PATH)
  2. RDKit (dans le processus : ETKDG puis MMFF/UFF)
  3. Open Babel via ses liaisons Python (pybel, dans le processus)

generate_3d(blocks) prend {cid: bloc SDF 2D} et retourne
({cid: bloc SDF 3D}, info) ; info contient les lignes de diagnostic.
diagnostic() decrit l'environnement (pour diagnostiquer Windows).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

OBABEL_TIMEOUT = 900


def _frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _popen_extra() -> dict:
    extra = {"stdin": subprocess.DEVNULL}
    if sys.platform.startswith("win"):
        extra["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return extra


# ----------------------------------------------------------------- SDF utils
def sdf_blocks(content: str) -> dict:
    """Decoupe un SDF (texte) en {cid: bloc}. Le titre de chaque bloc est le CID."""
    out = {}
    for raw in content.split("$$$$"):
        blk = raw.strip("\r\n")
        if not blk.strip():
            continue
        first = blk.splitlines()[0].strip()
        if first.isdigit():
            out[int(first)] = blk + "\n$$$$\n"
    return out


def is_3d(block: str) -> bool:
    """True si au moins un atome a une coordonnee z non nulle."""
    try:
        lines = block.splitlines()
        n_atoms = int(lines[3][0:3])
        return any(abs(float(l[20:30])) > 1e-4 for l in lines[4:4 + n_atoms])
    except (ValueError, IndexError):
        return False


# ------------------------------------------------------------ localisation obabel
def _roots() -> list:
    roots = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass))
    if _frozen():
        roots.append(Path(sys.executable).resolve().parent)
    roots.append(Path(__file__).resolve().parent.parent)
    seen, out = set(), []
    for r in roots:
        if str(r) not in seen:
            seen.add(str(r))
            out.append(r)
    return out


def _data_dir(rt: Path):
    base = rt / "share" / "openbabel"
    if not base.is_dir():
        return None
    for d in [base] + sorted(p for p in base.iterdir() if p.is_dir()):
        if (d / "element.txt").exists():
            return d
    return base


def _env_for_bundled(exe: Path, rt: Path) -> dict:
    env = os.environ.copy()
    data = _data_dir(rt)
    if data is not None:
        env["BABEL_DATADIR"] = str(data)
    cand = rt / "lib" / "openbabel"
    if cand.is_dir():
        env["BABEL_LIBDIR"] = str(cand)
    else:
        obf = next(rt.rglob("*.obf"), None)
        if obf is not None:
            env["BABEL_LIBDIR"] = str(obf.parent)
    env["PATH"] = str(exe.parent) + os.pathsep + env.get("PATH", "")
    return env


def find_obabel():
    """Retourne (chemin de l'executable ou None, environnement a utiliser)."""
    names = ("obabel.exe", "obabel") if sys.platform.startswith("win") else ("obabel",)
    if _frozen():
        try:
            from src.tools.runtime_env import configure_bundled_runtime
            configure_bundled_runtime()
        except Exception:
            pass
    else:
        found = shutil.which("obabel")
        if found:
            return found, os.environ.copy()

    for root in _roots():
        rt = root / "obabel_runtime"
        if not rt.is_dir():
            continue
        for sub in ("bin", ""):
            for n in names:
                p = (rt / sub / n) if sub else (rt / n)
                if p.is_file():
                    return str(p), _env_for_bundled(p, rt)
        for n in names:
            for p in sorted(rt.glob("**/" + n)):
                if p.is_file():
                    return str(p), _env_for_bundled(p, rt)

    found = shutil.which("obabel")
    if found:
        return found, os.environ.copy()
    return None, os.environ.copy()


# ------------------------------------------------------------------- moteurs
def _engine_obabel(blocks):
    exe, env = find_obabel()
    if not exe:
        return {}, "exécutable introuvable (obabel_runtime et PATH)"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        src = tmp / "in2d.sdf"
        dst = tmp / "out3d.sdf"
        src.write_text("".join(blocks.values()), encoding="utf-8")
        try:
            cp = subprocess.run(
                [exe, str(src), "-O", str(dst), "--gen3d", "-h"],
                capture_output=True, timeout=OBABEL_TIMEOUT, env=env,
                **_popen_extra(),
            )
        except subprocess.TimeoutExpired:
            return {}, f"délai dépassé ({OBABEL_TIMEOUT} s)"
        except (OSError, subprocess.SubprocessError) as exc:
            return {}, f"lancement impossible ({type(exc).__name__}: {exc})"
        out = {}
        if dst.exists():
            text = dst.read_text(encoding="utf-8", errors="replace")
            for cid, blk in sdf_blocks(text).items():
                if cid in blocks and is_3d(blk):
                    out[cid] = blk
        note = ""
        if not out:
            err = (cp.stderr or b"").decode("utf-8", "replace").strip()
            note = f"code de retour {cp.returncode}" + (f" ; {err[-300:]}" if err else "")
        return out, note


def _engine_rdkit(blocks):
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except Exception as exc:
        return {}, f"indisponible ({type(exc).__name__}: {exc})"
    out, bad = {}, 0
    for cid, blk in blocks.items():
        try:
            molblock = blk[:blk.index("M  END") + 6]
            mol = Chem.MolFromMolBlock(molblock, removeHs=False)
            if mol is None:
                bad += 1
                continue
            mol = Chem.AddHs(mol)
            if AllChem.EmbedMolecule(mol, randomSeed=42) != 0:
                if AllChem.EmbedMolecule(mol, randomSeed=42, useRandomCoords=True) != 0:
                    bad += 1
                    continue
            try:
                if AllChem.MMFFOptimizeMolecule(mol, maxIters=2000) == -1:
                    AllChem.UFFOptimizeMolecule(mol, maxIters=2000)
            except Exception:
                pass
            mol.SetProp("_Name", str(cid))
            out[cid] = Chem.MolToMolBlock(mol) + "$$$$\n"
        except Exception:
            bad += 1
    return out, (f"{bad} échec(s) de plongement 3D" if bad else "")


def _engine_pybel(blocks):
    try:
        try:
            from src.tools.plip_worker import _fix_babel_datadir_for_python_bindings
            _fix_babel_datadir_for_python_bindings()
        except Exception:
            pass
        from openbabel import pybel
    except Exception as exc:
        return {}, f"indisponible ({type(exc).__name__}: {exc})"
    out, bad = {}, 0
    for cid, blk in blocks.items():
        try:
            mol = pybel.readstring("sdf", blk.replace("$$$$", "").strip() + "\n")
            mol.addh()
            mol.make3D(forcefield="mmff94", steps=50)
            mol.title = str(cid)
            txt = mol.write("sdf")
            if not is_3d(txt):
                bad += 1
                continue
            out[cid] = txt if txt.rstrip().endswith("$$$$") else txt.rstrip() + "\n$$$$\n"
        except Exception:
            bad += 1
    return out, (f"{bad} échec(s)" if bad else "")


_ENGINES = (
    ("Open Babel (exécutable)", _engine_obabel),
    ("RDKit", _engine_rdkit),
    ("Open Babel (pybel)", _engine_pybel),
)


def generate_3d(blocks: dict):
    """{cid: bloc 2D} -> ({cid: bloc 3D}, {'used', 'diag', 'failed'})."""
    todo = dict(blocks)
    out, used, diag = {}, {}, []
    if not todo:
        return out, {"used": used, "diag": diag, "failed": []}
    for name, engine in _ENGINES:
        if not todo:
            break
        try:
            res, note = engine(todo)
        except Exception as exc:
            res, note = {}, f"erreur inattendue ({type(exc).__name__}: {exc})"
        for cid, blk in res.items():
            out[cid] = blk
            used[cid] = name
            todo.pop(cid, None)
        line = f"{name} : {len(res)} molécule(s) convertie(s)"
        if note:
            line += f" ; {note}"
        diag.append(line)
    return out, {"used": used, "diag": diag, "failed": sorted(todo)}


# ---------------------------------------------------------------- diagnostic
def diagnostic() -> list:
    lines = [
        f"Python {sys.version.split()[0]} ; plateforme {sys.platform} ; "
        f"mode package : {'oui' if _frozen() else 'non'}"
    ]
    mp = getattr(sys, "_MEIPASS", None)
    if mp:
        lines.append(f"Dossier temporaire du package : {mp}")

    exe, env = find_obabel()
    if exe:
        lines.append(f"Open Babel (exécutable) : {exe}")
        for k in ("BABEL_DATADIR", "BABEL_LIBDIR"):
            if env.get(k):
                lines.append(f"  {k} = {env[k]}")
        try:
            cp = subprocess.run([exe, "-V"], capture_output=True, timeout=30,
                                env=env, **_popen_extra())
            txt = ((cp.stdout or b"") + (cp.stderr or b"")).decode("utf-8", "replace").strip()
            lines.append(f"  sortie de -V (code {cp.returncode}) : {txt[:300]}")
        except Exception as exc:
            lines.append(f"  lancement impossible : {type(exc).__name__}: {exc}")
    else:
        lines.append("Open Babel (exécutable) : introuvable (obabel_runtime et PATH)")

    try:
        from rdkit import rdBase
        lines.append(f"RDKit : disponible (version {rdBase.rdkitVersion})")
    except Exception as exc:
        lines.append(f"RDKit : indisponible ({type(exc).__name__}: {exc})")

    try:
        from openbabel import openbabel as ob
        lines.append(f"pybel / liaisons Open Babel : disponibles (version {ob.OBReleaseVersion()})")
    except Exception as exc:
        lines.append(f"pybel / liaisons Open Babel : indisponibles ({type(exc).__name__}: {exc})")
    return lines
