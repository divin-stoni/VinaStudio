# -*- coding: utf-8 -*-
"""
bench_redocking.py (v2) : banc de validation par re-docking sur plusieurs pompes RND.
La famille d'une chaine est lue dans le fichier PDB (DBREF / UniProt), pas deduite de la recherche.

  python bench_redocking.py --dry-run     # selection seule, sans docking
  python bench_redocking.py               # selection + docking (reprise auto)
  python bench_redocking.py --summary     # recalcule le bilan depuis le CSV
"""
import argparse, csv, math, re, sys, time
from pathlib import Path
import numpy as np
import requests

sys.path.insert(0, ".")
from src import pdb_inspect as pi, redocking as rd, grid_fit, guide_assistant as ga

# ----------------------------------------------------------------------------
# CRITERES FIXES AVANT LE DOCKING (ne pas les modifier apres avoir vu les resultats)
# ----------------------------------------------------------------------------
# famille : (gene, taxon UniProt, repli nom de molecule, repli organisme)
FAMILLES = {
    "AcrB": ("acrB", 562, r"acrb|acriflavine resistance protein b", None),
    "MexB": ("mexB", 287, r"mexb", None),
    "AdeB": ("adeB", 470, r"adeb", None),
    "CmeB": ("cmeB", 197, r"cmeb|efflux pump membrane transporter", r"campylobacter"),
}
ACCS = {f: set() for f in FAMILLES}     # rempli depuis UniProt

MAX_RES = 3.2
LIG_ATOMES = (12, 70)
MIN_CONTACTS = 10
MIN_FRAC_CHAINE = 0.8
MAX_B_RATIO = ga.B_RATIO_BAD
MARGE = 8.0
CAP_MEME_LIGAND = 2
PARAMS = {"exhaustiveness": 32, "num_modes": 9, "energy_range": 3.0, "seed": 2024}
EXCLUS_CODES = set(ga.LIKELY_NOT_LIGANDS)
# garde-fou : le nom de molecule du PDB doit ressembler a une pompe RND (en plus de l'accession UniProt)
POMPE_NOM = r"efflux|multidrug|resistance protein|acr[ab]|mex[ab]|ade[ab]|cme[ab]|membrane transporter"

BASE = Path("redocking_runs/bench2")
CSV_RES = BASE / "resultats.csv"
CSV_EXC = BASE / "exclusions.csv"
COLS = ["famille", "pdb", "resolution", "ligand", "resname", "chaine", "n_atomes",
        "contacts", "ratio_B", "rmsd_pose1", "rmsd_meilleur", "valide", "site_retrouve",
        "n_site", "n_modes", "dist_centres", "part_atomes_2A", "score_pose1", "duree_s", "statut"]
ATTR_ACC = "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession"


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


# ------------------------------------------------------------------ recherche
def uniprot_accessions(gene, taxon):
    try:
        r = requests.get("https://rest.uniprot.org/uniprotkb/search", timeout=30, params={
            "query": f"gene_exact:{gene} AND taxonomy_id:{taxon}",
            "fields": "accession,protein_name", "format": "tsv", "size": 100})
    except Exception as exc:
        print(f"  UniProt {gene}: {type(exc).__name__}")
        return []
    if r.status_code != 200:
        print(f"  UniProt {gene}: HTTP {r.status_code}")
        return []
    out = []
    for l in r.text.strip().splitlines()[1:]:
        p = l.split("\t")
        if len(p) >= 2 and p[0]:
            out.append((p[0], p[1]))
    return out


def _requete(noeud, rows):
    return {"query": {"type": "group", "logical_operator": "and", "nodes": [
        noeud,
        {"type": "terminal", "service": "text", "parameters": {
            "attribute": "rcsb_entry_info.resolution_combined",
            "operator": "less_or_equal", "value": MAX_RES}},
        {"type": "terminal", "service": "text", "parameters": {
            "attribute": "rcsb_entry_info.nonpolymer_entity_count",
            "operator": "greater", "value": 0}}]},
        "return_type": "entry",
        "request_options": {"paginate": {"start": 0, "rows": rows},
                            "sort": [{"sort_by": "rcsb_entry_info.resolution_combined",
                                      "direction": "asc"}]}}


def _post(q):
    r = requests.post("https://search.rcsb.org/rcsbsearch/v2/query", json=q, timeout=30)
    if r.status_code == 200:
        return [x["identifier"] for x in r.json().get("result_set", [])]
    if r.status_code != 204:
        print(f"  RCSB: HTTP {r.status_code}")
    return None if r.status_code not in (200, 204) else []


def search_rcsb(accs, rows):
    if not accs:
        return []
    noeud = {"type": "terminal", "service": "text", "parameters": {
        "attribute": ATTR_ACC, "operator": "in", "value": sorted(accs)[:50]}}
    ids = _post(_requete(noeud, rows))
    if ids is not None:
        return ids
    ids = []                                   # repli : une requete par accession
    for a in sorted(accs)[:10]:
        noeud = {"type": "terminal", "service": "text", "parameters": {
            "attribute": ATTR_ACC, "operator": "exact_match", "value": a}}
        for i in (_post(_requete(noeud, rows)) or []):
            if i not in ids:
                ids.append(i)
    return ids


# ---------------------------------------------------------------- famille
def lire_dbref(pdb):
    d = {}
    with open(pdb, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if line.startswith("DBREF "):
                m = re.search(r"\bUNP\s+(\w+)", line)
                if m:
                    d[line[12:13].strip() or "_"] = m.group(1)
            elif line.startswith(("ATOM", "HETATM")):
                break
    return d


def famille_chaine(dbref, chain, molecule, organisme):
    acc = dbref.get(chain)
    if acc:
        for fam, s in ACCS.items():
            if acc in s:
                return fam
    for fam, (_g, _t, motif, org) in FAMILLES.items():
        if re.search(motif, molecule or "", re.I) and (
                org is None or re.search(org, organisme or "", re.I)):
            return fam
    return None


def evaluer(code, pdb):
    rep = pi.inspect_pdb(pdb)
    dbref = lire_dbref(pdb)
    meilleur, raisons = None, []
    for lig in rep.ligands:
        if lig.resname in EXCLUS_CODES or ga.is_lipid_like(lig):
            raisons.append(f"{lig.resname}: lipide/detergent")
            continue
        if not (LIG_ATOMES[0] <= lig.n_atoms <= LIG_ATOMES[1]):
            raisons.append(f"{lig.resname}: taille {lig.n_atoms}")
            continue
        if lig.best_contacts < MIN_CONTACTS:
            raisons.append(f"{lig.resname}: {lig.best_contacts} contacts")
            continue
        total = sum(c.contacts.get(lig.key, 0) for c in rep.chains.values()) or 1
        if lig.best_contacts / total < MIN_FRAC_CHAINE:
            raisons.append(f"{lig.resname}: ligand partage entre chaines")
            continue
        ch = rep.chains.get(lig.best_chain)
        fam = famille_chaine(dbref, lig.best_chain, ch.molecule if ch else "", rep.organism)
        if fam is not None and not re.search(POMPE_NOM, (ch.molecule if ch else "") or "", re.I):
            raisons.append(f"{lig.resname}: molecule '{(ch.molecule if ch else '?')[:40]}' incompatible avec une pompe")
            fam = None
        if fam is None:
            raisons.append(f"{lig.resname}: chaine '{(ch.molecule if ch else '?')[:45]}' "
                           f"(UniProt {dbref.get(lig.best_chain, '?')}) hors des 4 familles")
            continue
        bl, bp = ga.ligand_bfactors(pdb, lig)
        if not (bl and bp):
            raisons.append(f"{lig.resname}: facteur B inconnu")
            continue
        ratio = bl / bp
        if ratio > MAX_B_RATIO:
            raisons.append(f"{lig.resname}: B x{ratio:.1f}")
            continue
        cand = {"famille": fam, "pdb": code, "resolution": rep.resolution, "lig": lig,
                "ratio": ratio, "path": pdb, "rep": rep}
        if meilleur is None or lig.best_contacts > meilleur["lig"].best_contacts:
            meilleur = cand
    if meilleur:
        return meilleur, ""
    return None, "; ".join(raisons[:4]) or "aucun ligand"


def selectionner(args):
    BASE.mkdir(parents=True, exist_ok=True)
    codes = []
    for fam, (gene, taxon, _m, _o) in FAMILLES.items():
        brut = uniprot_accessions(gene, taxon)
        ACCS[fam] = {a for a, n in brut if re.search(POMPE_NOM, n or "", re.I) and not re.search(r"gyrase|topoisomerase", n or "", re.I)}
        for a, n in brut:
            print(f"    UniProt {a} : {(n or '?')[:58]} -> " + ("garde" if a in ACCS[fam] else "REJETE (nom hors famille)"))
        ids = search_rcsb(ACCS[fam], args.per_family)
        print(f"{fam}: {len(ACCS[fam])} accession(s) UniProt, {len(ids)} entree(s) RCSB a <= {MAX_RES} A avec ligand")
        codes += [i for i in ids if i not in codes]
    for c in (args.codes or []):
        if c.upper() not in codes:
            codes.append(c.upper())

    retenus, exclus = {f: [] for f in FAMILLES}, []
    for code in codes:
        try:
            pdb = BASE / f"{code}.pdb"
            if not pdb.exists():
                rd._download_pdb(code, BASE)
            cand, raison = evaluer(code, pdb)
        except Exception as exc:
            exclus.append((code, "?", f"erreur {type(exc).__name__}"))
            continue
        if cand is None:
            exclus.append((code, "?", raison))
        else:
            retenus[cand["famille"]].append(cand)

    finals = {}
    for fam, lst in retenus.items():
        lst.sort(key=lambda c: (c["resolution"] or 9, c["pdb"]))
        compte, garde = {}, []
        for c in lst:
            k = c["lig"].resname
            if compte.get(k, 0) >= CAP_MEME_LIGAND:
                exclus.append((c["pdb"], fam, f"redondant ({k} deja {CAP_MEME_LIGAND} fois)"))
                continue
            compte[k] = compte.get(k, 0) + 1
            garde.append(c)
        for c in garde[args.cap_family:]:
            exclus.append((c["pdb"], fam, f"au-dela du plafond par famille ({args.cap_family})"))
        finals[fam] = garde[:args.cap_family]
    ordre, i = [], 0
    while len(ordre) < args.max_total and any(i < len(v) for v in finals.values()):
        for fam in FAMILLES:
            if i < len(finals[fam]) and len(ordre) < args.max_total:
                ordre.append(finals[fam][i])
        i += 1
    pris = {c["pdb"] for c in ordre}
    for fam, v in finals.items():
        for c in v:
            if c["pdb"] not in pris:
                exclus.append((c["pdb"], fam, "au-dela du plafond total"))
    with open(CSV_EXC, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["pdb", "famille", "raison"])
        w.writerows(exclus)
    return ordre, exclus


# ---------------------------------------------------------------- docking
def deja_fait():
    if not CSV_RES.exists():
        return set()
    with open(CSV_RES, newline="", encoding="utf-8") as fh:
        return {(r["pdb"], r["ligand"]) for r in csv.DictReader(fh)}


def ajouter(row):
    nouveau = not CSV_RES.exists()
    with open(CSV_RES, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        if nouveau:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in COLS})


def docker(c, cpu):
    lig, code = c["lig"], c["pdb"]
    work = BASE / code
    work.mkdir(exist_ok=True)
    row = {"famille": c["famille"], "pdb": code, "resolution": c["resolution"],
           "ligand": lig.key, "resname": lig.resname, "chaine": lig.best_chain,
           "n_atomes": lig.n_atoms, "contacts": lig.best_contacts,
           "ratio_B": round(c["ratio"], 2)}
    t0 = time.perf_counter()
    try:
        clean = work / f"{code}_{lig.best_chain}.pdb"
        pi.write_clean_pdb(c["path"], clean, [lig.best_chain], True, True)
        pdbqt = work / f"{code}_{lig.best_chain}.pdbqt"
        ok, msg = pi.convert_to_pdbqt(clean, pdbqt, protonate=True)
        if not ok:
            row["statut"] = "conversion: " + msg[:80]
            return row
        pdbqt.write_text("".join(l for l in open(pdbqt) if l.startswith(("ATOM", "HETATM"))))
        center, size, _ = grid_fit.box_from_coords(lig.xyz, MARGE)
        res = rd.redock(pdbqt, [float(v) for v in center], [float(v) for v in size],
                        dict(PARAMS, cpu=cpu), c["path"], lig.key, work)
    except Exception as exc:
        row["statut"] = f"erreur {type(exc).__name__}: {exc}"[:120]
        return row
    row["duree_s"] = round(time.perf_counter() - t0)
    if not res.ok:
        row["statut"] = ("echec: " + res.message)[:120]
        return row
    ratio_site = (res.n_site / res.n_modes) if res.n_modes else 0
    row.update({
        "rmsd_pose1": round(res.rmsd_top, 2), "rmsd_meilleur": round(res.rmsd_best, 2),
        "valide": bool(res.passed), "n_site": res.n_site, "n_modes": res.n_modes,
        "site_retrouve": ratio_site >= 0.5,
        "dist_centres": round(res.center_dist_top, 2) if res.center_dist_top is not None else "",
        "part_atomes_2A": round(res.frac_2a_top, 2) if res.frac_2a_top is not None else "",
        "score_pose1": round(res.affinity_top, 2), "statut": "ok"})
    return row


def bilan():
    if not CSV_RES.exists():
        print("Aucun resultat.")
        return
    with open(CSV_RES, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    ok = [r for r in rows if r["statut"] == "ok"]
    ko = [r for r in rows if r["statut"] != "ok"]
    print("=" * 78)
    print("BILAN DU BANC DE RE-DOCKING")
    print("=" * 78)
    print(f"{'PDB':<6}{'fam.':<6}{'res':>5} {'ligand':<14}{'B x':>5}{'RMSD 1':>8}{'meill.':>8}{'site':>6}  verdict")
    for r in sorted(ok, key=lambda r: (r["famille"], r["pdb"])):
        v = r["valide"] == "True"
        verdict = "VALIDE" if v else ("site retrouve" if r["site_retrouve"] == "True" else "echec")
        print(f"{r['pdb']:<6}{r['famille']:<6}{float(r['resolution'] or 0):>5.2f} {r['ligand']:<14}"
              f"{r['ratio_B']:>5}{r['rmsd_pose1']:>8}{r['rmsd_meilleur']:>8}"
              f"{r['n_site']+'/'+r['n_modes']:>6}  {verdict}")
    if ko:
        print("\nNon evalues (erreur technique) : " + ", ".join(f"{r['pdb']} ({r['statut'][:40]})" for r in ko))

    def ligne(nom, lst):
        n = len(lst)
        if n == 0:
            return
        a = sum(r["valide"] == "True" for r in lst)
        b = sum(float(r["rmsd_meilleur"]) < rd.RMSD_THRESHOLD for r in lst)
        s = sum(r["site_retrouve"] == "True" for r in lst)
        la, ha = wilson(a, n)
        print(f"{nom:<8} n={n:<3} pose n°1 < 2 A : {a}/{n} ({100*a/n:.0f} %, IC95 {100*la:.0f}-{100*ha:.0f} %)"
              f" | meilleure des {PARAMS['num_modes']} : {b}/{n} | site retrouve : {s}/{n}")
    print()
    ligne("GLOBAL", ok)
    for fam in FAMILLES:
        ligne(fam, [r for r in ok if r["famille"] == fam])
    print("\nRappel : re-docking dans le cas le plus favorable (boite centree sur le ligand du cristal,")
    print("chaine liante seule, hydrogenes ajoutes). Ce n'est pas un test de cross-docking.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="selection seule")
    ap.add_argument("--summary", action="store_true", help="bilan depuis le CSV")
    ap.add_argument("--max-total", type=int, default=24)
    ap.add_argument("--per-family", type=int, default=100, help="entrees RCSB examinees par famille")
    ap.add_argument("--cap-family", type=int, default=10, help="complexes max par famille (les mieux resolus)")
    ap.add_argument("--cpu", type=int, default=4)
    ap.add_argument("--codes", nargs="*", help="codes PDB supplementaires a examiner")
    args = ap.parse_args()
    BASE.mkdir(parents=True, exist_ok=True)
    if args.summary:
        bilan()
        return
    print("CRITERES : resolution <= %.1f A ; ligand %d-%d atomes ; >= %d contacts ; >= %d %% sur la chaine liante ;"
          " B(ligand)/B(chaine) <= %.1f ; pas de lipide/detergent ; <= %d entrees par (famille, ligand)"
          % (MAX_RES, LIG_ATOMES[0], LIG_ATOMES[1], MIN_CONTACTS, 100 * MIN_FRAC_CHAINE, MAX_B_RATIO, CAP_MEME_LIGAND))
    ordre, exclus = selectionner(args)
    print(f"\n{len(ordre)} complexe(s) retenu(s), {len(exclus)} ecarte(s) (raisons : {CSV_EXC})\n")
    print(f"{'PDB':<6}{'fam.':<6}{'res':>5} {'ligand':<14}{'at.':>4}{'contacts':>9}{'B x':>6}  molecule de la chaine liante")
    for c in ordre:
        l = c["lig"]
        _ch = c["rep"].chains.get(l.best_chain)
        print(f"{c['pdb']:<6}{c['famille']:<6}{(c['resolution'] or 0):>5.2f} {l.key:<14}{l.n_atoms:>4}{l.best_contacts:>9}{c['ratio']:>6.2f}  {(_ch.molecule if _ch else '?')[:40]}")
    for fam in FAMILLES:
        print(f"  {fam}: {sum(1 for c in ordre if c['famille'] == fam)} retenu(s)")
    if args.dry_run:
        print("\nSelection seule : aucun docking lance.")
        return
    fait = deja_fait()
    for i, c in enumerate(ordre, 1):
        if (c["pdb"], c["lig"].key) in fait:
            print(f"[{i}/{len(ordre)}] {c['pdb']} deja fait, ignore")
            continue
        print(f"[{i}/{len(ordre)}] {c['pdb']} / {c['lig'].key} ({c['famille']})...", flush=True)
        row = docker(c, args.cpu)
        ajouter(row)
        print("   ", row.get("statut"), row.get("rmsd_pose1", ""), flush=True)
    bilan()


if __name__ == "__main__":
    main()
