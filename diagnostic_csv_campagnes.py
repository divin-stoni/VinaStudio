import os
import datetime
from pathlib import Path
import pandas as pd

ROOT = Path.cwd()
EXCLUS = {"dist", "venv", ".venv", "__pycache__", ".git", "node_modules"}
MOTIFS = ("docking_results", "analysis_ready", "scores_fusionnes", "dataset_fusionne")

fichiers = []
for dossier, sous_dossiers, noms in os.walk(ROOT):
    sous_dossiers[:] = [d for d in sous_dossiers if d not in EXCLUS]
    for nom in noms:
        if nom.endswith(".csv") and nom.startswith(MOTIFS) and ".bak" not in nom:
            fichiers.append(Path(dossier) / nom)
fichiers.sort()

lignes = []
def out(txt=""):
    lignes.append(txt)

out("DIAGNOSTIC CSV DE CAMPAGNES - " + datetime.datetime.now().isoformat(timespec="seconds"))
out("Racine : " + str(ROOT))
out("Fichiers trouves : " + str(len(fichiers)))
out("")

for p in fichiers:
    rel = p.relative_to(ROOT)
    out("=" * 78)
    out("FICHIER : " + str(rel))
    try:
        mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="minutes")
        out("Modifie le : " + mtime)
        df = pd.read_csv(p)
        out("Forme : %d lignes x %d colonnes" % df.shape)
        out("Colonnes : " + ", ".join(map(str, df.columns)))

        col_mol = next((c for c in ("molecule", "nom", "name") if c in df.columns), None)
        if col_mol:
            out("Molecules distinctes (%s) : %d" % (col_mol, df[col_mol].nunique()))
        else:
            out("Molecules distinctes : colonne non trouvee")

        if "groupe" in df.columns:
            comptes = df["groupe"].value_counts(dropna=False)
            out("Familles (groupe) : %d distinctes" % len(comptes))
            for nom_g, n in comptes.head(12).items():
                out("    %s : %d" % (nom_g, n))
        else:
            out("Familles : pas de colonne 'groupe'")

        cols_aff = [c for c in df.columns if str(c).startswith(("best_affinity", "dg_", "DeltaG"))]
        out("Colonnes d'affinite : " + (", ".join(cols_aff) if cols_aff else "aucune"))

        for c in [c for c in df.columns if str(c).startswith("status")]:
            out("Statuts %s : %s" % (c, dict(df[c].value_counts(dropna=False))))

        if "best_affinity" in df.columns:
            out("Cible seule : deduite du dossier -> " + p.parent.name)

        out("Apercu (2 premieres lignes) :")
        out(df.head(2).to_string(max_colwidth=30))
    except Exception as e:
        out("ERREUR de lecture : %r" % (e,))
    out("")

sortie = ROOT / "diagnostic_csv_campagnes.txt"
sortie.write_text("\n".join(lignes), encoding="utf-8")
print("Termine. %d fichier(s) analyse(s)." % len(fichiers))
print("Rapport ecrit dans : " + str(sortie))
