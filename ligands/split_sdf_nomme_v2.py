#!/usr/bin/env python3
"""
Sépare un SDF multi-molécules en fichiers individuels,
nommés d'après le nom réel de la molécule.

Ordre de priorité pour trouver le nom :
1. Propriétés SDF locales : PUBCHEM_IUPAC_NAME, NAME, Name, COMPOUND_NAME, ID
2. Si le titre (_Name) est un CID PubChem numérique et qu'aucun nom local
   n'est trouvé -> requête à l'API PubChem PUG REST pour récupérer le nom
   (avec cache local pour ne pas re-demander deux fois le même CID).

Nécessite une connexion internet pour l'étape 2 (curl/urllib).
"""

from rdkit import Chem
import os
import re
import sys
import json
import time
import urllib.request
import urllib.error

CACHE_FILE = "cid_nom_cache.json"


def charger_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def sauver_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def nom_depuis_pubchem(cid, cache):
    """Interroge PubChem PUG REST pour obtenir un nom lisible à partir d'un CID."""
    cid = str(cid)
    if cid in cache:
        return cache[cid]

    url = (
        f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/"
        f"property/IUPACName/JSON"
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        nom = data["PropertyTable"]["Properties"][0].get("IUPACName", "")
    except Exception as e:
        print(f"   ⚠️  Échec requête PubChem pour CID {cid} : {e}")
        nom = ""

    cache[cid] = nom
    sauver_cache(cache)
    time.sleep(0.3)  # politesse envers l'API PubChem (limite de requêtes)
    return nom


def nom_fichier_propre(nom):
    nom = nom.strip()
    nom = re.sub(r"[^\w\-]", "_", nom)
    nom = re.sub(r"_+", "_", nom).strip("_")
    return nom if nom else "molecule_sans_nom"


def est_cid_numerique(s):
    return bool(re.fullmatch(r"\d+", s.strip()))


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
        nom = ""

        # 1. propriétés locales explicites
        for prop in ("PUBCHEM_IUPAC_NAME", "NAME", "Name", "COMPOUND_NAME", "ID"):
            if mol.HasProp(prop):
                val = mol.GetProp(prop).strip()
                if val and not est_cid_numerique(val):
                    nom = val
                    break

        # 2. si le titre est un CID numérique et qu'on n'a toujours rien -> PubChem
        if not nom and titre and est_cid_numerique(titre) and resoudre_pubchem:
            nom = nom_depuis_pubchem(titre, cache)
            if nom:
                n_pubchem += 1

        # 3. dernier recours
        if not nom:
            nom = titre if titre else f"molecule_{i+1}"

        nom_propre = nom_fichier_propre(nom)
        # garde le CID entre parenthèses si on l'a résolu, pour traçabilité
        if titre and est_cid_numerique(titre) and nom_propre != titre:
            nom_propre = f"{nom_propre}_CID{titre}"

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
          f"{n_pubchem} noms résolus via PubChem.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage : python split_sdf_nomme_v2.py <fichier.sdf> <dossier_sortie> [--no-pubchem]")
        sys.exit(1)
    resoudre = "--no-pubchem" not in sys.argv
    split_sdf(sys.argv[1], sys.argv[2], resoudre_pubchem=resoudre)
