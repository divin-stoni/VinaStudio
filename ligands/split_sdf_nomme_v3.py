#!/usr/bin/env python3
"""
Sépare un SDF multi-molécules en fichiers individuels,
nommés d'après le nom USUEL de la molécule (pas le nom IUPAC systématique).

Stratégie :
1. Récupère le CID depuis le titre (_Name) ou PUBCHEM_COMPOUND_CID.
2. Interroge PubChem /synonyms pour ce CID (liste de synonymes, souvent
   triée avec les noms usuels/commerciaux en premier).
3. Choisit le "meilleur" synonyme : on filtre les CAS numbers, les CID,
   les codes internes (ex. "NSC-xxxx"), et on préfère un nom court,
   alphabétique, plutôt qu'un nom IUPAC à rallonge.
4. Cache local (cid_nom_cache.json) pour ne pas re-interroger deux fois.
5. Fallback sur PUBCHEM_IUPAC_NAME si aucun synonyme exploitable trouvé,
   et sur le CID brut en dernier recours.
"""

from rdkit import Chem
import os
import re
import sys
import json
import time
import urllib.request

CACHE_FILE = "cid_nom_cache.json"


def charger_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def sauver_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def est_cas_number(s):
    return bool(re.fullmatch(r"\d{2,7}-\d{2}-\d", s))


def est_code_interne(s):
    # ex: NSC-12345, UNII-XXXXX, EINECS, DB00477, CHEMBL123, CHEBI:xxx
    return bool(re.match(r"^(NSC|UNII|EINECS|DB\d|CHEMBL|CHEBI|MFCD|SCHEMBL|AKOS|BRN|HSDB|CAS-)", s, re.IGNORECASE))


def est_cid_numerique(s):
    return bool(re.fullmatch(r"\d+", s.strip()))


def score_synonyme(s):
    """Plus le score est bas, meilleur est le synonyme (on trie ascendant)."""
    if est_cas_number(s) or est_code_interne(s) or est_cid_numerique(s):
        return 9999
    if not re.match(r"^[A-Za-z0-9\s\-,'()]+$", s):
        return 500  # contient des caractères bizarres -> probablement pas un nom usuel
    # pénalise les noms très longs (souvent IUPAC systématiques)
    penalite_longueur = len(s)
    # bonus si ça ressemble à un nom propre simple (une ou deux lettres majuscules type "Chlorpromazine")
    if re.match(r"^[A-Z][a-z]+(\s[A-Z]?[a-z]+)*$", s):
        penalite_longueur -= 20
    return penalite_longueur


def meilleur_nom_depuis_synonymes(cid, cache):
    cid = str(cid)
    if cid in cache:
        return cache[cid]

    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/synonyms/JSON"
    nom = ""
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        synonymes = data["InformationList"]["Information"][0].get("Synonym", [])
        if synonymes:
            candidats = sorted(synonymes[:25], key=score_synonyme)  # limite aux 25 premiers (déjà triés par pertinence par PubChem)
            if candidats and score_synonyme(candidats[0]) < 9999:
                nom = candidats[0]
    except Exception as e:
        print(f"   ⚠️  Échec requête synonymes PubChem pour CID {cid} : {e}")

    cache[cid] = nom
    sauver_cache(cache)
    time.sleep(0.3)
    return nom


def nom_fichier_propre(nom):
    nom = nom.strip()
    nom = re.sub(r"[^\w\-]", "_", nom)
    nom = re.sub(r"_+", "_", nom).strip("_")
    return nom if nom else "molecule_sans_nom"


def split_sdf(fichier_sdf, dossier_sortie, resoudre_pubchem=True):
    os.makedirs(dossier_sortie, exist_ok=True)
    suppl = Chem.SDMolSupplier(fichier_sdf, removeHs=False)
    cache = charger_cache() if resoudre_pubchem else {}

    compteur = {}
    n_ok, n_echec, n_pubchem = 0, 0, 0

    for i, mol in enumerate(suppl):
        if mol is None:
            print(f"⚠️  Molécule #{i+1} illisible, ignorée.")
            n_echec += 1
            continue

        titre = mol.GetProp("_Name") if mol.HasProp("_Name") else ""
        cid = titre if est_cid_numerique(titre) else ""
        if not cid and mol.HasProp("PUBCHEM_COMPOUND_CID"):
            cid = mol.GetProp("PUBCHEM_COMPOUND_CID").strip()

        nom = ""
        if cid and resoudre_pubchem:
            nom = meilleur_nom_depuis_synonymes(cid, cache)
            if nom:
                n_pubchem += 1

        # fallback : nom IUPAC local si aucun synonyme exploitable
        if not nom and mol.HasProp("PUBCHEM_IUPAC_NAME"):
            nom = mol.GetProp("PUBCHEM_IUPAC_NAME").strip()

        if not nom:
            nom = titre if titre else f"molecule_{i+1}"

        nom_propre = nom_fichier_propre(nom)
        if cid:
            nom_propre = f"{nom_propre}_CID{cid}"

        if nom_propre in compteur:
            compteur[nom_propre] += 1
            nom_final = f"{nom_propre}_{compteur[nom_propre]}"
        else:
            compteur[nom_propre] = 1
            nom_final = nom_propre

        chemin_sortie = os.path.join(dossier_sortie, f"{nom_final}.sdf")
        writer = Chem.SDWriter(chemin_sortie)
        writer.write(mol)
        writer.close()

        n_ok += 1
        print(f"✅ #{i+1:3d} → {nom_final}.sdf")

    print(f"\nTerminé : {n_ok} molécules écrites, {n_echec} échecs, "
          f"{n_pubchem} noms résolus via PubChem synonymes.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage : python split_sdf_nomme_v3.py <fichier.sdf> <dossier_sortie> [--no-pubchem]")
        sys.exit(1)
    resoudre = "--no-pubchem" not in sys.argv
    split_sdf(sys.argv[1], sys.argv[2], resoudre_pubchem=resoudre)
