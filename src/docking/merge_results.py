# -*- coding: utf-8 -*-
"""Fusion d'un CSV de docking recent avec une version precedente (docking cible)."""
import csv
from pathlib import Path


def merge_csv(previous, new):
    """Ajoute au CSV `new` les lignes de `previous` dont la molecule n'y figure pas.
    Les nouvelles lignes gagnent. Retourne le nombre de lignes conservees.
    Ne fait rien si les en-tetes different (autre couple de cibles)."""
    previous, new = Path(previous), Path(new)
    if not previous.is_file() or not new.is_file():
        return 0
    with previous.open(newline="", encoding="utf-8") as h:
        r1 = csv.DictReader(h)
        prev_fields = list(r1.fieldnames or [])
        prev_rows = list(r1)
    with new.open(newline="", encoding="utf-8") as h:
        r2 = csv.DictReader(h)
        new_fields = list(r2.fieldnames or [])
        new_rows = list(r2)
    if not new_fields or set(prev_fields) != set(new_fields) or "molecule" not in new_fields:
        return 0
    new_names = {str(r.get("molecule", "")).strip() for r in new_rows}
    kept = [r for r in prev_rows if str(r.get("molecule", "")).strip() not in new_names]
    with new.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=new_fields)
        w.writeheader()
        for row in kept + new_rows:
            w.writerow({k: row.get(k, "") for k in new_fields})
    return len(kept)
