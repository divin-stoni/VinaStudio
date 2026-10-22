# -*- coding: utf-8 -*-
"""
grid_fit.py

Calculs purs (sans Qt) pour ajuster la grid box : lecture PDB/PDBQT/SDF,
selection de residus, boite englobante + marge, statistiques de la boite.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

import numpy as np

_WATER = {"HOH", "WAT", "H2O", "DOD", "TIP", "SOL"}
_NOT_LIGAND = _WATER | {
    "SO4", "PO4", "GOL", "EDO", "PEG", "PGE", "PG4", "1PE", "ACT", "DMS",
    "FMT", "NO3", "TRS", "MPD", "BME", "CIT", "TLA", "EPE", "MES", "IMD",
    "IOD", "CL", "NA", "MG", "ZN", "CA", "K", "MN", "FE", "CU", "NI", "CO",
    "CD", "BR",
}
_ONE_TO_THREE = {
    "A": "ALA", "R": "ARG", "N": "ASN", "D": "ASP", "C": "CYS", "Q": "GLN",
    "E": "GLU", "G": "GLY", "H": "HIS", "I": "ILE", "L": "LEU", "K": "LYS",
    "M": "MET", "F": "PHE", "P": "PRO", "S": "SER", "T": "THR", "W": "TRP",
    "Y": "TYR", "V": "VAL",
}
_ALIASES = {
    "HID": "HIS", "HIE": "HIS", "HIP": "HIS", "HSD": "HIS", "HSE": "HIS",
    "HSP": "HIS", "CYX": "CYS", "CYM": "CYS", "ASH": "ASP", "GLH": "GLU",
    "LYN": "LYS",
}


@dataclass
class Structure:
    xyz: np.ndarray
    res_idx: np.ndarray
    chain: list
    num: list
    icode: list
    name: list
    hetero: list
    hetero_arr: np.ndarray


_CACHE: dict = {}


def load_structure(path) -> Structure:
    """Lit un PDB ou PDBQT (premier modele). Mis en cache par chemin + date."""
    path = str(path)
    mtime = os.path.getmtime(path)
    hit = _CACHE.get(path)
    if hit and hit[0] == mtime:
        return hit[1]

    coords, idx = [], []
    keys: dict = {}
    chain, num, icode, name, hetero = [], [], [], [], []

    with open(path, "r", errors="ignore") as fh:
        for line in fh:
            if line.startswith("ENDMDL"):
                break
            rec = line[:6]
            if rec != "ATOM  " and rec != "HETATM":
                continue
            if len(line) < 54:
                continue
            if line[16:17] not in (" ", "", "A", "1"):
                continue
            try:
                x = float(line[30:38])
                y = float(line[38:46])
                z = float(line[46:54])
                n = int(line[22:26])
            except ValueError:
                continue
            rn = line[17:20].strip().upper()
            ch = line[21:22].strip()
            ic = line[26:27].strip()
            het = rec == "HETATM"
            key = (ch, n, ic, rn, het)
            i = keys.get(key)
            if i is None:
                i = len(chain)
                keys[key] = i
                chain.append(ch)
                num.append(n)
                icode.append(ic)
                name.append(rn)
                hetero.append(het)
            coords.append((x, y, z))
            idx.append(i)

    if not coords:
        raise ValueError(f"Aucun atome lisible dans {os.path.basename(path)}.")

    st = Structure(
        np.asarray(coords, dtype=float),
        np.asarray(idx, dtype=np.int64),
        chain, num, icode, name, hetero,
        np.asarray(hetero, dtype=bool),
    )
    _CACHE[path] = (mtime, st)
    return st


_TOKEN = re.compile(
    r"^(?:(?P<c1>[A-Za-z0-9]):)?\s*(?P<name>[A-Za-z]{1,3})?[\s\-_.]*"
    r"(?P<num>-?\d+)(?P<ic>[A-Za-z])?\s*(?::(?P<c2>[A-Za-z0-9]))?$"
)


def parse_residue_query(text: str) -> list:
    parts = [p.strip() for p in re.split(r"[,;\n]+", text or "") if p.strip()]
    if not parts:
        raise ValueError("Saisis au moins un résidu (ex. GLY22, PHE178, A:VAL139).")
    specs = []
    for p in parts:
        m = _TOKEN.match(p)
        if not m:
            raise ValueError(
                f"Résidu non reconnu : « {p} » (formats : 22, GLY22, G22, A:GLY22, GLY22:B)."
            )
        name = (m.group("name") or "").upper()
        if name:
            if len(name) == 1:
                name = _ONE_TO_THREE.get(name)
            elif len(name) == 2:
                name = None
            if not name:
                raise ValueError(f"Nom de résidu inconnu dans « {p} ».")
            name = _ALIASES.get(name, name)
        specs.append({
            "raw": p,
            "chain": m.group("c1") or m.group("c2") or "",
            "name": name or "",
            "num": int(m.group("num")),
            "icode": (m.group("ic") or "").upper(),
        })
    return specs


def select_residues(st: Structure, specs: list):
    """Retourne (indices de residus, notes). Leve ValueError si introuvable."""
    chosen, notes = [], []
    for s in specs:
        hits = [i for i, n in enumerate(st.num)
                if n == s["num"] and st.name[i] not in _WATER]
        if s["icode"]:
            hits = [i for i in hits if st.icode[i].upper() == s["icode"]]
        if s["chain"]:
            hits = [i for i in hits if st.chain[i].upper() == s["chain"].upper()]
        if s["name"]:
            hits = [i for i in hits
                    if _ALIASES.get(st.name[i], st.name[i]) == s["name"]]
        if not hits:
            found = [f"{st.name[i]}{st.num[i]}" for i, n in enumerate(st.num)
                     if n == s["num"]][:3]
            hint = (f" (au numéro {s['num']}, le fichier contient : {', '.join(found)})"
                    if found else "")
            raise ValueError(f"Résidu « {s['raw']} » introuvable{hint}.")
        chains = sorted({st.chain[i] for i in hits})
        if len(chains) > 1 and not s["chain"]:
            first = hits[0]
            hits = [i for i in hits if st.chain[i] == st.chain[first]]
            notes.append(
                f"{s['raw']} existe dans les chaînes {', '.join(c or '?' for c in chains)} : "
                f"chaîne {st.chain[first] or '?'} retenue (précise-la, ex. B:{s['raw']})."
            )
        chosen.extend(hits)
    return chosen, notes


def coords_of(st: Structure, residue_indices) -> np.ndarray:
    mask = np.isin(st.res_idx, list(residue_indices))
    return st.xyz[mask]


def find_ligand(st: Structure):
    """Indice du plus gros residu HETATM hors eau/ions/additifs (>= 6 atomes)."""
    counts = np.bincount(st.res_idx, minlength=len(st.name))
    best = None
    for i, (het, nm) in enumerate(zip(st.hetero, st.name)):
        if not het or nm in _NOT_LIGAND or counts[i] < 6:
            continue
        if best is None or counts[i] > counts[best]:
            best = i
    return best


def read_ligand_file(path) -> np.ndarray:
    path = str(path)
    ext = os.path.splitext(path)[1].lower()
    if ext in (".pdb", ".pdbqt", ".ent"):
        return load_structure(path).xyz
    if ext in (".sdf", ".mol"):
        with open(path, "r", errors="ignore") as fh:
            lines = fh.read().splitlines()
        if len(lines) < 5:
            raise ValueError("Fichier SDF/MOL vide ou tronqué.")
        if "V3000" in lines[3]:
            raise ValueError("Format MOL V3000 non pris en charge : exporte en V2000 ou en PDB.")
        try:
            n = int(lines[3][0:3])
            pts = []
            for ln in lines[4:4 + n]:
                try:
                    pts.append((float(ln[0:10]), float(ln[10:20]), float(ln[20:30])))
                except ValueError:
                    p = ln.split()
                    pts.append((float(p[0]), float(p[1]), float(p[2])))
        except (ValueError, IndexError):
            raise ValueError("Coordonnées SDF/MOL illisibles.")
        if not pts:
            raise ValueError("Aucun atome dans le fichier SDF/MOL.")
        return np.asarray(pts, dtype=float)
    raise ValueError("Extension non prise en charge (SDF, MOL, PDB, PDBQT).")


def box_from_coords(xyz, margin, min_size=1.0, max_size=200.0):
    xyz = np.asarray(xyz, dtype=float)
    lo = xyz.min(axis=0)
    hi = xyz.max(axis=0)
    center = (lo + hi) / 2.0
    size = (hi - lo) + 2.0 * float(margin)
    clamped = bool(np.any(size > max_size) or np.any(size < min_size))
    return center, np.clip(size, min_size, max_size), clamped


def box_stats(st: Structure, center, size) -> dict:
    c = np.asarray(center, dtype=float)
    s = np.asarray(size, dtype=float)
    lo, hi = c - s / 2.0, c + s / 2.0
    inside = np.all((st.xyz >= lo) & (st.xyz <= hi), axis=1)
    n = len(st.name)
    total = np.bincount(st.res_idx, minlength=n)
    ins = np.bincount(st.res_idx[inside], minlength=n)
    prot = ~st.hetero_arr
    return {
        "volume": float(np.prod(s)),
        "n_in": int(((ins > 0) & prot).sum()),
        "n_cut": int((((ins > 0) & (ins < total)) & prot).sum()),
    }


def receptor_bbox_contains(st: Structure, center, tol=15.0) -> bool:
    c = np.asarray(center, dtype=float)
    lo = st.xyz.min(axis=0) - tol
    hi = st.xyz.max(axis=0) + tol
    return bool(np.all(c >= lo) and np.all(c <= hi))
