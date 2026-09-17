# -*- coding: utf-8 -*-
"""
src/analysis/pocket_detector.py

Detection de poches via fpocket (appel subprocess), pattern calque sur
src/visualization/plip_runner.py : travail dans un dossier dedie, jamais
dans le dossier source des recepteurs.

fpocket doit etre installe et accessible dans le PATH (commande `fpocket`).

Comportement :
- fpocket est appele avec -i MIN_ALPHA_SPHERES pour que les poches
  microscopiques (replis de surface sans interet pharmacologique) ne
  soient meme pas generees. S'applique a n'importe quel recepteur
  (precharge ou importe).
- Chaque poche retournee contient le contenu BRUT du fichier
  pocket<N>_vert.pqr produit par fpocket (`alpha_spheres_pqr`) : ce
  fichier PQR contient chaque sphere alpha avec son propre centre et
  son propre rayon. Le viewer 3D charge ce PQR directement dans
  3Dmol.js et calcule une vraie surface VDW dessus, ce qui donne une
  forme de cavite continue et lisse (comme dans les figures de
  publication fpocket / PyMOL), au lieu d'un nuage de petites boules
  visibles individuellement.
- Tous les descripteurs numeriques de <n>_info.txt sont remontes
  (score, druggability, hydrophobicite, polarite, volume, SASA,
  nombre de spheres alpha, etc.).

API :
    detect_pockets(receptor_pdb, workdir, min_alpha_spheres=20) -> list[dict]
        Chaque poche : {
            "pocket_id": int,
            "descriptors": {"score": float, "druggability_score": float, ...},
            "center": [x, y, z],
            "radius": float,
            "alpha_spheres_pqr": str,  # contenu brut de pocket<N>_vert.pqr
        }
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

# Nombre minimum de spheres alpha pour qu'une poche soit conservee par
# fpocket lui-meme (flag -i). En dessous, ce sont des micro-cavites de
# surface sans interet pour y loger un ligand. A ajuster si besoin.
MIN_ALPHA_SPHERES = 20

_POCKET_HEADER_RE = re.compile(r"^Pocket\s+(\d+)\s*:", re.IGNORECASE)
_DESCRIPTOR_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 ._/\-]*?)\s*:\s*([\-\d.]+)\s*$")


def _parse_info_txt(info_path: Path) -> dict:
    """
    Parse <n>_info.txt produit par fpocket. Retourne
    {pocket_id: {descriptor_key: float, ...}, ...} avec TOUS les
    descripteurs numeriques listes par fpocket pour chaque poche.
    """
    descriptors: dict = {}
    if not info_path.exists():
        return descriptors

    current_id = None
    for raw_line in info_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        header_match = _POCKET_HEADER_RE.match(raw_line.strip())
        if header_match:
            current_id = int(header_match.group(1))
            descriptors[current_id] = {}
            continue

        if current_id is None:
            continue

        desc_match = _DESCRIPTOR_RE.match(raw_line)
        if not desc_match:
            continue

        key = desc_match.group(1).strip()
        norm_key = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
        try:
            descriptors[current_id][norm_key] = float(desc_match.group(2))
        except ValueError:
            continue

    return descriptors


def _pocket_geometry_from_atm_pdb(atm_pdb: Path):
    """
    Calcule le centre (centroide des spheres alpha) et un rayon
    englobant depuis pocket<N>_atm.pdb. Sert uniquement a cadrer la
    camera / avoir un point de reference ; le rendu visuel utilise
    `alpha_spheres_pqr`, pas ce rayon englobant.
    """
    xs, ys, zs = [], [], []

    for line in atm_pdb.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not (line.startswith("ATOM") or line.startswith("HETATM")):
            continue
        try:
            x = float(line[30:38])
            y = float(line[38:46])
            z = float(line[46:54])
        except ValueError:
            continue
        xs.append(x)
        ys.append(y)
        zs.append(z)

    if not xs:
        return None

    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    cz = sum(zs) / len(zs)

    radius = max(
        ((x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2) ** 0.5
        for x, y, z in zip(xs, ys, zs)
    )
    radius = max(radius, 3.0)

    return [cx, cy, cz], radius


def detect_pockets(receptor_pdb, workdir, min_alpha_spheres: int = MIN_ALPHA_SPHERES):
    """
    Lance fpocket sur `receptor_pdb` et retourne la liste des poches
    detectees, triees par score de druggabilite decroissant.
    `workdir` est un dossier de travail dedie (jamais le dossier
    source du recepteur).

    Le flag -i (min_alpha_spheres) est passe directement a fpocket :
    les micro-poches sont ecartees a la source, pour n'importe quel
    recepteur (precharge ou importe) affiche dans le viewer.
    """
    receptor_pdb = Path(receptor_pdb)
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    local_pdb = workdir / receptor_pdb.name
    shutil.copy2(receptor_pdb, local_pdb)

    subprocess.run(
        ["fpocket", "-f", str(local_pdb), "-i", str(min_alpha_spheres)],
        check=True,
    )

    out_dir = workdir / f"{local_pdb.stem}_out"
    if not out_dir.exists():
        raise RuntimeError(
            f"fpocket n'a produit aucun dossier de resultats attendu : {out_dir}"
        )

    info_descriptors = _parse_info_txt(out_dir / f"{local_pdb.stem}_info.txt")

    pockets_dir = out_dir / "pockets"
    if not pockets_dir.exists():
        raise RuntimeError(f"Dossier des poches introuvable : {pockets_dir}")

    results = []
    for atm_pdb in sorted(pockets_dir.glob("pocket*_atm.pdb")):
        match = re.search(r"pocket(\d+)_atm\.pdb", atm_pdb.name)
        if not match:
            continue
        pocket_id = int(match.group(1))

        geometry = _pocket_geometry_from_atm_pdb(atm_pdb)
        if geometry is None:
            continue
        center, radius = geometry

        vert_pqr = pockets_dir / f"pocket{pocket_id}_vert.pqr"
        alpha_spheres_pqr = (
            vert_pqr.read_text(encoding="utf-8", errors="ignore")
            if vert_pqr.exists() else ""
        )

        results.append(
            {
                "pocket_id": pocket_id,
                "descriptors": info_descriptors.get(pocket_id, {}),
                "center": center,
                "radius": radius,
                "alpha_spheres_pqr": alpha_spheres_pqr,
            }
        )

    results.sort(
        key=lambda p: p["descriptors"].get("druggability_score", -1.0),
        reverse=True,
    )
    return results
