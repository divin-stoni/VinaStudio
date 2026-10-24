# -*- coding: utf-8 -*-
"""Donnees completes d'un re-docking : une ligne par pose, pour l'analyse."""
import csv
from pathlib import Path
import numpy as np
from src import redocking as rd


def pose_table(work, tag):
    work = Path(work)
    ref = np.asarray(rd.read_pdbqt_models(work / f"{tag}_cristal.pdbqt")[0][1], float)
    types = rd.read_pdbqt_heavy_types(work / f"{tag}_cristal.pdbqt")
    models = rd.read_pdbqt_models(work / f"{tag}_redock_out.pdbqt")
    perms = rd._automorphisms(types, rd._bond_matrix(ref, types))
    rows = []
    for k, (aff, xyz) in enumerate(models, 1):
        xyz = np.asarray(xyz, float)
        d = np.sqrt(((xyz[perms] - ref[None]) ** 2).sum(axis=2))
        best = int(np.sqrt((d ** 2).mean(axis=1)).argmin())
        cd = float(np.linalg.norm(xyz.mean(axis=0) - ref.mean(axis=0)))
        rows.append({
            "pose": k,
            "energie_kcal_mol": float(aff),
            "rmsd_sym": float(np.sqrt((d[best] ** 2).mean())),
            "dist_centres": cd,
            "part_atomes_sous_seuil": float((d[best] <= rd.RMSD_THRESHOLD).mean()),
            "dans_le_site": bool(cd < rd.SITE_RADIUS),
        })
    return rows


def write_csv(rows, path):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
