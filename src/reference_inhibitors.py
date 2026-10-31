# -*- coding: utf-8 -*-
"""Inhibiteurs et ligands de reference : classification, selection, telechargement tracable."""
import datetime
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = Path(__file__).resolve().parent / "data" / "reference_inhibitors.json"
OUT_ROOT = ROOT / "docking" / "ligands" / "references"
PUBCHEM = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
RCSB_LIG = "https://files.rcsb.org/ligands/download/{code}_ideal.sdf"
UA = {"User-Agent": "VinaStudio/1.0 (reference inhibitors)"}

# noms a essayer dans PubChem, par compose de la liste
QUERIES = {
    "D13-9001 / ABI-PP": [],
    "MBX2319": ["MBX2319"],
    "PAbetaN (phenylalanine-arginine beta-naphthylamide)":
        ["Phe-Arg beta-naphthylamide", "phenylalanine arginine beta-naphthylamide"],
    "1-(1-naphthylmethyl)-piperazine (NMP)": ["1-(1-naphthylmethyl)piperazine"],
    "Berberine": ["berberine"],
}
FAMILIES = {"mexb": "MexB", "acrb": "AcrB", "adeb": "AdeB", "cmeb": "CmeB"}


def load_catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def family_of(text):
    t = (text or "").lower()
    for k, v in FAMILIES.items():
        if k in t:
            return v
    return None


def pdb_code_from(path, fallback=None):
    stem = Path(str(path)).stem.upper()
    if re.fullmatch(r"[0-9][A-Z0-9]{3}", stem):
        return stem
    fb = (fallback or "").strip().upper()
    return fb if re.fullmatch(r"[0-9][A-Z0-9]{3}", fb) else None


def classify_crystal(cat, pdb_code, resname):
    """(role, entree du catalogue ou None, verifie)."""
    code, res = (pdb_code or "").upper(), (resname or "").upper()
    for c in cat["composes"]:
        for e in c.get("pdb", []):
            if e["code"].upper() == code and e["ligand"].upper() == res:
                return "inhibiteur", c, bool(e.get("verifie", False))
    for e in cat.get("ligands_cristal_connus", []):
        if e["pdb"].upper() == code and e["ligand"].upper() == res:
            role = "substrat" if e["role"].startswith("substrat") else e["role"]
            return role, e, bool(e.get("verifie", False))
    return "inconnu", None, False


def propose(cat, family, crystal_compound=None, total=3):
    """Inhibiteurs documentes pour la pompe, sans le compose du cristal."""
    need = total - (1 if crystal_compound is not None else 0)
    pool = [c for c in cat["composes"]
            if family in c.get("pompes", []) and c is not crystal_compound
            and family not in c.get("exclut", [])]
    return pool[:need], max(0, need - len(pool))


def _get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def _slug(name):
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")[:40] or "compose"


def fetch_compound(job, dest_dir):
    """Telecharge la structure d'un compose. Leve RuntimeError si introuvable."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now().isoformat(timespec="seconds")
    base = {k: job.get(k) for k in ("nom", "role", "refs", "verifie", "pompes", "source_info")}
    path = dest_dir / (_slug(job["nom"]) + ".sdf")
    errors = []
    for e in job.get("pdb", []):
        url = RCSB_LIG.format(code=e["ligand"])
        try:
            txt = _get(url)
            if "$$$$" in txt:
                path.write_text(txt, encoding="utf-8")
                return dict(base, fichier=str(path), source="RCSB ligand " + e["ligand"],
                            url=url, dimension="3D", cid=None, date=now)
        except Exception as exc:
            errors.append(f"RCSB {e['ligand']}: {type(exc).__name__}")
    for q in job.get("queries", []):
        qq = urllib.parse.quote(q)
        for rt in ("3d", "2d"):
            url = f"{PUBCHEM}/compound/name/{qq}/SDF?record_type={rt}"
            try:
                txt = _get(url)
            except Exception as exc:
                errors.append(f"PubChem '{q}' {rt}: {type(exc).__name__}")
                continue
            if "$$$$" not in txt:
                continue
            cid = None
            try:
                cid = json.loads(_get(f"{PUBCHEM}/compound/name/{qq}/cids/JSON"))[
                    "IdentifierList"]["CID"][0]
            except Exception:
                pass
            if cid is not None:
                # Le CID devient le nom de fichier canonique : il est stable,
                # sans ambiguïté et directement recherchable sur PubChem.
                path = dest_dir / f"CID_{cid}.sdf"
            path.write_text(txt, encoding="utf-8")
            pubchem_url = (
                f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"
                if cid is not None else url
            )
            return dict(
                base,
                fichier=str(path),
                source=(
                    f"PubChem CID_{cid} ('{q}')"
                    if cid is not None else "PubChem '" + q + "'"
                ),
                url=pubchem_url,
                dimension=rt.upper(),
                cid=cid,
                date=now,
            )
    raise RuntimeError("introuvable (" + "; ".join(errors[-3:]) + ")" if errors else "introuvable")


def save_registry(profile_id, family, crystal, records):
    d = OUT_ROOT / profile_id
    d.mkdir(parents=True, exist_ok=True)
    f = d / "references.json"
    old = {}
    if f.exists():
        try:
            old = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            old = {}
    by_name = {r.get("nom"): r for r in old.get("references", [])}
    for r in records:
        if "erreur" not in r:
            by_name[r["nom"]] = r
    data = {"profil": profile_id, "famille": family, "ligand_cristal": crystal,
            "mise_a_jour": datetime.datetime.now().isoformat(timespec="seconds"),
            "references": list(by_name.values())}
    f.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return f
