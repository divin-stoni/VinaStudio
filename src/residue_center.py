"""
residue_center.py

Saisie tolerante d'un residu de reference (22, GLU22, E-22, A:GLU22,
glutamate 22...) et calcul du centre de ses atomes lourds dans un
fichier PDB ou PDBQT. Sert a centrer la grid box sur ce residu.
"""

import re
import unicodedata
from pathlib import Path

_AA = [
    ("ALA", "A", ["ALANINE"]),
    ("ARG", "R", ["ARGININE"]),
    ("ASN", "N", ["ASPARAGINE"]),
    ("ASP", "D", ["ASPARTATE", "ASPARTIC", "ASPARTICACID", "ACIDEASPARTIQUE", "ASPARTIQUE"]),
    ("CYS", "C", ["CYSTEINE"]),
    ("GLN", "Q", ["GLUTAMINE"]),
    ("GLU", "E", ["GLUTAMATE", "GLUTAMIC", "GLUTAMICACID", "ACIDEGLUTAMIQUE", "GLUTAMIQUE"]),
    ("GLY", "G", ["GLYCINE"]),
    ("HIS", "H", ["HISTIDINE"]),
    ("ILE", "I", ["ISOLEUCINE"]),
    ("LEU", "L", ["LEUCINE"]),
    ("LYS", "K", ["LYSINE"]),
    ("MET", "M", ["METHIONINE"]),
    ("PHE", "F", ["PHENYLALANINE"]),
    ("PRO", "P", ["PROLINE"]),
    ("SER", "S", ["SERINE"]),
    ("THR", "T", ["THREONINE"]),
    ("TRP", "W", ["TRYPTOPHANE", "TRYPTOPHAN"]),
    ("TYR", "Y", ["TYROSINE"]),
    ("VAL", "V", ["VALINE"]),
]

THREE_TO_ONE = {t: o for t, o, _ in _AA}
ONE_TO_THREE = {o: t for t, o, _ in _AA}
NAME_TO_THREE = {}
for _t, _o, _names in _AA:
    for _n in _names:
        NAME_TO_THREE[_n] = _t

_SYNONYMS = {
    "HID": "HIS", "HIE": "HIS", "HIP": "HIS", "HSD": "HIS", "HSE": "HIS",
    "HSP": "HIS", "CYX": "CYS", "CYM": "CYS", "ASH": "ASP", "GLH": "GLU",
    "LYN": "LYS", "MSE": "MET",
}


def canon3(resn):
    r = str(resn).strip().upper()
    return _SYNONYMS.get(r, r)


def _strip_accents(text):
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def parse_residue_query(text):
    """Retourne (chaine ou None, nom 3 lettres ou None, numero)."""
    s = _strip_accents(str(text)).upper().strip()
    if not s:
        raise ValueError("saisie vide")

    chain = None
    m = re.search(r"\b(?:CHAINE|CHAIN)\s*[:=]?\s*([A-Z0-9])\b", s)
    if m:
        chain = m.group(1)
        s = (s[:m.start()] + " " + s[m.end():]).strip()
    else:
        m = re.match(r"^([A-Z0-9])\s*[:/]\s*(.+)$", s)
        if m:
            chain, s = m.group(1), m.group(2).strip()
        else:
            m = re.match(r"^(.+?)\s*[:/(]\s*([A-Z0-9])\)?$", s)
            if m:
                s, chain = m.group(1).strip(), m.group(2)

    m = re.match(r"^([A-Z ]*?)[\s\-_.]*([0-9]+)$", s)
    if not m:
        raise ValueError(
            f"format non reconnu : {text!r} (exemples : 22, GLU22, E-22, A:GLU22)"
        )
    letters = m.group(1).replace(" ", "")
    number = int(m.group(2))

    if not letters:
        resname = None
    elif len(letters) == 1:
        resname = ONE_TO_THREE.get(letters)
        if resname is None:
            raise ValueError(f"code a une lettre inconnu : {letters}")
    elif len(letters) == 3 and (letters in THREE_TO_ONE or letters in _SYNONYMS):
        resname = canon3(letters)
    elif letters in NAME_TO_THREE:
        resname = NAME_TO_THREE[letters]
    else:
        raise ValueError(f"nom d'acide amine non reconnu : {letters}")

    return chain, resname, number


def locate_residue(path, query):
    """Centre (atomes lourds) du residu designe par `query` dans le fichier."""
    chain, resname, resnum = parse_residue_query(query)

    path = Path(path) if path else None
    if path is None or not path.exists():
        raise ValueError("fichier du recepteur introuvable")

    residues = {}
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if not line.startswith("ATOM") or len(line) < 54:
                continue
            if line[16] not in (" ", "A", "1"):
                continue
            name = line[12:16].strip().lstrip("0123456789")
            if name.startswith("H"):
                continue
            try:
                resi = int(line[22:26])
                x = float(line[30:38])
                y = float(line[38:46])
                z = float(line[46:54])
            except ValueError:
                continue
            key = (line[21].strip(), resi)
            entry = residues.setdefault(key, {"resn": line[17:20].strip(), "xyz": []})
            entry["xyz"].append((x, y, z))

    if not residues:
        raise ValueError("aucun atome lisible dans le fichier du recepteur")

    candidates = [k for k in residues if k[1] == resnum]
    if chain:
        candidates = [k for k in candidates if k[0].upper() == chain.upper()]

    if not candidates:
        nums = [k[1] for k in residues]
        where = f" dans la chaine {chain}" if chain else ""
        raise ValueError(
            f"residu {resnum} introuvable{where} "
            f"(numerotation de ce fichier : {min(nums)} a {max(nums)})"
        )

    if resname:
        matching = [k for k in candidates if canon3(residues[k]["resn"]) == resname]
        if not matching:
            found = ", ".join(sorted({residues[k]["resn"] for k in candidates}))
            raise ValueError(
                f"le residu {resnum} est {found} dans ce fichier, pas {resname}. "
                "Verifie la numerotation (PDB ou article)."
            )
        candidates = matching

    candidates.sort()
    chains = [k[0] or "-" for k in candidates]
    key = candidates[0]
    pts = residues[key]["xyz"]
    n = len(pts)
    center = (
        sum(p[0] for p in pts) / n,
        sum(p[1] for p in pts) / n,
        sum(p[2] for p in pts) / n,
    )
    return {
        "chain": key[0] or "-",
        "resname": residues[key]["resn"],
        "resnum": resnum,
        "center": center,
        "chains": chains,
        "chain_given": bool(chain),
    }
