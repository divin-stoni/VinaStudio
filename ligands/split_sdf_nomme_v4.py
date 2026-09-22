#!/usr/bin/env python3
"""
Sépare un SDF multi-molécules en fichiers individuels,
nommés d'après le "Title" PubChem officiel de chaque CID
(le nom affiché en haut de la fiche PubChem — généralement le nom
générique/scientifique standard, ex. "Chlorpromazine", pas un nom
commercial régional obscur).

Endpoint utilisé : /compound/cid/{cid}/description/JSON -> champ "Title"
(beaucoup plus fiable que de trier /synonyms à l'aveugle).

Cache local (cid_nom_cache_v4.json) pour ne pas re-interroger deux fois.
"""

from rdkit import Chem
import os
import re
import sys
import json
import time
import urllib.request

CACHE_FILE = "cid_nom_cache_v4.json"


def charger_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def sauver_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def est_cid_numerique(s):
    return bool(re.fullmatch(r"\d+", s.strip()))


def titre_pubchem(cid, cache):
    cid = str(cid)
    if cid in cache:
        return cache[cid]

    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/description/JSON"
    nom = ""
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        infos = data["InformationList"]["Information"]
        # la première entrée avec un "Title" est en général la bonne (CID lui-même)
        for entry in infos:
            if "Title" in entry and entry.get("CID") is not None:
                nom = entry["Title"]
                break
        if not nom and infos:
            nom = infos[0].get("Title", "")
    except Exception as e:
        print(f"   ⚠️  Échec requête PubChem (description) pour CID {cid} : {e}")

    cache[cid] = nom
    sauver_cache(cache)
    time.sleep(0.25)
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

        titre_bloc = mol.GetProp("_Name") if mol.HasProp("_Name") else ""
        cid = titre_bloc if est_cid_numerique(titre_bloc) else ""
        if not cid and mol.HasProp("PUBCHEM_COMPOUND_CID"):
            cid = mol.GetProp("PUBCHEM_COMPOUND_CID").strip()

        nom = ""
        if cid and resoudre_pubchem:
            nom = titre_pubchem(cid, cache)
            if nom:
                n_pubchem += 1

        # fallback : nom IUPAC local si le titre PubChem a échoué
        if not nom and mol.HasProp("PUBCHEM_IUPAC_NAME"):
            nom = mol.GetProp("PUBCHEM_IUPAC_NAME").strip()

        if not nom:
            nom = titre_bloc if titre_bloc else f"molecule_{i+1}"

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
          f"{n_pubchem} noms résolus via PubChem (Title officiel).")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage : python split_sdf_nomme_v4.py <fichier.sdf> <dossier_sortie> [--no-pubchem]")
        sys.exit(1)
    resoudre = "--no-pubchem" not in sys.argv
    split_sdf(sys.argv[1], sys.argv[2], resoudre_pubchem=resoudre)
