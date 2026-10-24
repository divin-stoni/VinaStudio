# -*- coding: utf-8 -*-
"""Recalcule le bilan du banc avec l'echelle noyau/queues (sans relancer Vina)."""
import csv, sys
from pathlib import Path
sys.path.insert(0, ".")
from src import redocking_core as rc, validation_levels as vl

B = Path("redocking_runs/bench2")
rows = [r for r in csv.DictReader(open(B / "resultats.csv", encoding="utf-8"))
        if r["statut"] == "ok"]
ANSI = {"vert": "\033[32m", "jaune": "\033[33m", "orange": "\033[38;5;208m", "rouge": "\033[31m"}
out, count = [], {}
print(f"{'PDB':<6}{'fam.':<6}{'RMSD1':>7}{'noyau':>7}{'queues':>8}{'noyau at.':>11}  niveau")
for r in sorted(rows, key=lambda r: (r["famille"], r["pdb"])):
    tag = r["ligand"].replace(":", "_")
    try:
        ci = rc.analyse(B / r["pdb"], tag)
    except Exception as exc:
        print(f"{r['pdb']:<6}erreur : {exc}")
        continue
    s = ci["resume"]
    v = {"rmsd_top": float(r["rmsd_pose1"]), "n_site": int(r["n_site"]),
         "n_modes": int(r["n_modes"])}
    lvl = vl.level_from_validation(v, ci)
    col, sym, label = vl.LEVELS[lvl]
    q = "-" if s["rmsd_tail"] is None else f"{s['rmsd_tail']:.2f}"
    diff = abs(ci["poses"][0]["rmsd_global"] - v["rmsd_top"])
    warn = "  (ecart avec le CSV !)" if diff > 0.05 else ""
    print(f"{r['pdb']:<6}{r['famille']:<6}{v['rmsd_top']:>7.2f}{s['rmsd_core']:>7.2f}{q:>8}"
          f"{str(s['n_core']) + '/' + str(s['n_atoms']):>11}  {ANSI[lvl]}{sym} {label}\033[0m{warn}")
    count.setdefault(r["famille"], {}).setdefault(lvl, 0)
    count[r["famille"]][lvl] += 1
    out.append({"pdb": r["pdb"], "famille": r["famille"], "rmsd_pose1": v["rmsd_top"],
                "rmsd_noyau": round(s["rmsd_core"], 2), "rmsd_queues": q,
                "atomes_noyau": s["n_core"], "atomes_total": s["n_atoms"],
                "mode_coupure": s["mode"], "niveau": lvl})
with open(B / "resultats_noyau.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
    w.writeheader()
    w.writerows(out)
print("\nRecapitulatif par niveau :")
tot = {}
for fam, d in count.items():
    print(f"  {fam:<6}", {k: d.get(k, 0) for k in ("vert", "jaune", "orange", "rouge")})
    for k, n in d.items():
        tot[k] = tot.get(k, 0) + n
print("  TOTAL ", {k: tot.get(k, 0) for k in ("vert", "jaune", "orange", "rouge")})
print("\nSeul le vert valide. Le jaune est un descripteur secondaire ajoute apres observation.")
