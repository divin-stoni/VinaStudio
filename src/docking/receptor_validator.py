# -*- coding: utf-8 -*-
"""
receptor_validator.py

Validation (et nettoyage optionnel) d'un récepteur PDBQT avant docking Vina.

Vina refuse un récepteur rigide qui contient une ligne autre que
ATOM / HETATM / TER / END / REMARK (ex. HEADER, COMPND, CRYST1, CONECT,
ROOT, BRANCH). Ce module :
  - retire ces lignes (avec fix=True, copie .orig conservée) ;
  - vérifie le type d'atome AutoDock de chaque ligne atomique ;
  - vérifie qu'il y a assez d'atomes ;
  - vérifie que la boîte de docking contient bien des atomes du récepteur ;
  - signale les HETATM (ions, cofacteurs, résidus modifiés).
"""

from __future__ import annotations

import argparse
import shutil
from collections import Counter
from pathlib import Path

ALLOWED_TAGS = ("ATOM", "HETATM", "TER", "END", "REMARK")

AD_TYPES = {
    "H", "HD", "HS", "C", "A", "N", "NA", "NS", "OA", "OS", "F",
    "MG", "P", "SA", "S", "CL", "CA", "MN", "FE", "ZN", "BR", "I",
}


def validate_receptor_pdbqt(path, center=None, size=None, fix=False, min_atoms=100):
    path = Path(path)
    report = {
        "path": str(path),
        "ok": True,
        "errors": [],
        "warnings": [],
        "removed": {},
        "atoms": 0,
        "hetatm": {},
        "fixed": False,
    }

    if not path.is_file():
        report["ok"] = False
        report["errors"].append("fichier introuvable")
        return report

    kept = []
    coords = []
    removed = Counter()
    bad_types = Counter()
    unusual_types = Counter()
    het = Counter()
    unreadable = 0

    for raw in path.read_text(errors="ignore").splitlines():
        if not raw.strip():
            continue
        tag = raw[:6].strip()
        if tag not in ALLOWED_TAGS:
            removed[tag or "?"] += 1
            continue
        if tag in ("ATOM", "HETATM"):
            try:
                xyz = (float(raw[30:38]), float(raw[38:46]), float(raw[46:54]))
            except ValueError:
                unreadable += 1
                continue
            coords.append(xyz)
            ad_type = raw[77:79].strip().upper()
            if ad_type not in AD_TYPES:
                # Un type qui ressemble à un élément (ex. SE pour la
                # sélénométhionine) est accepté en pratique par Vina : simple
                # avertissement. Un type vide ou absurde reste une erreur.
                if ad_type.isalpha() and len(ad_type) <= 2:
                    unusual_types[ad_type] += 1
                else:
                    bad_types[ad_type or "?"] += 1
            if tag == "HETATM":
                het[raw[17:20].strip() or "?"] += 1
        kept.append(raw)

    report["atoms"] = len(coords)
    report["removed"] = dict(removed)
    report["hetatm"] = dict(het)

    if unreadable:
        report["errors"].append(f"{unreadable} ligne(s) atomique(s) aux coordonnées illisibles")
    if bad_types:
        report["errors"].append(
            "types d'atomes AutoDock invalides : "
            + ", ".join(f"{k} (x{v})" for k, v in bad_types.items())
        )
    if unusual_types:
        report["warnings"].append(
            "types d'atomes inhabituels (acceptés par Vina en pratique) : "
            + ", ".join(f"{k} (x{v})" for k, v in unusual_types.items())
        )
    if len(coords) < min_atoms:
        report["errors"].append(
            f"seulement {len(coords)} atomes (minimum {min_atoms}) : récepteur invalide"
        )

    if center is not None and size is not None and coords:
        lo = [c - s / 2 for c, s in zip(center, size)]
        hi = [c + s / 2 for c, s in zip(center, size)]
        inside = sum(
            1 for (x, y, z) in coords
            if lo[0] <= x <= hi[0] and lo[1] <= y <= hi[1] and lo[2] <= z <= hi[2]
        )
        report["atoms_in_box"] = inside
        if inside == 0:
            report["errors"].append(
                "la boîte de docking ne contient aucun atome du récepteur "
                "(centre hors de la structure) : le docking se ferait dans le vide"
            )
        elif inside < 20:
            report["warnings"].append(
                f"seulement {inside} atomes du récepteur dans la boîte de docking"
            )

    if het:
        report["warnings"].append(
            "HETATM dans le récepteur : "
            + ", ".join(f"{k} (x{v})" for k, v in het.items())
        )

    if removed:
        detail = ", ".join(f"{k} (x{v})" for k, v in removed.items())
        if fix:
            backup = path.with_suffix(path.suffix + ".orig")
            if not backup.exists():
                shutil.copy2(path, backup)
            path.write_text("\n".join(kept) + "\n")
            report["fixed"] = True
            report["warnings"].append(f"lignes interdites par Vina retirées : {detail}")
        else:
            report["errors"].append(f"lignes interdites par Vina : {detail} (à retirer)")

    report["ok"] = not report["errors"]
    return report


def format_report(report) -> str:
    status = "OK" if report["ok"] else "ERREUR"
    lines = [f"[{status}] {report['path']} ({report['atoms']} atomes)"]
    lines += [f"   erreur : {e}" for e in report["errors"]]
    lines += [f"   avertissement : {w}" for w in report["warnings"]]
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Valide des récepteurs PDBQT (sans rien modifier sauf --fix).")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--center", nargs=3, type=float)
    parser.add_argument("--size", nargs=3, type=float)
    parser.add_argument("--fix", action="store_true")
    args = parser.parse_args()
    for f in args.files:
        print(format_report(validate_receptor_pdbqt(f, args.center, args.size, fix=args.fix)))
