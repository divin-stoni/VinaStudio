#!/usr/bin/env python3
"""
Sépare un SDF multi-molécules en fichiers individuels,
nommés d'après le nom réel de la molécule (champ _Name ou une propriété SDF).
"""

from rdkit import Chem
import os
import re
import sys

def nom_fichier_propre(nom):
    nom = nom.strip()
    nom = re.sub(r'[^\w\-]', '_', nom)
    nom = re.sub(r'_+', '_', nom).strip('_')
    return nom if nom else "molecule_sans_nom"

def split_sdf(fichier_sdf, dossier_sortie):
    os.makedirs(dossier_sortie, exist_ok=True)
    suppl = Chem.SDMolSupplier(fichier_sdf, removeHs=False)
    compteur = {}
    n_ok, n_echec = 0, 0

    for i, mol in enumerate(suppl):
        if mol is None:
            print(f"⚠️  Molécule #{i+1} illisible, ignorée.")
            n_echec += 1
            continue

        nom = mol.GetProp("_Name") if mol.HasProp("_Name") else ""
        if not nom:
            for prop in ("NAME", "Name", "COMPOUND_NAME", "ID"):
                if mol.HasProp(prop):
                    nom = mol.GetProp(prop)
                    break
        if not nom:
            nom = f"molecule_{i+1}"

        nom_propre = nom_fichier_propre(nom)
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

    print(f"\nTerminé : {n_ok} molécules écrites, {n_echec} échecs.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage : python split_sdf_nomme.py <fichier.sdf> <dossier_sortie>")
        sys.exit(1)
    split_sdf(sys.argv[1], sys.argv[2])
