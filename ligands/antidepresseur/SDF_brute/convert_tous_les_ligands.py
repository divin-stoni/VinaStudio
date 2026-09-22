import os
import sys
import glob
from importlib.metadata import entry_points

# 1. On charge la commande Meeko directement depuis la mémoire de Python
try:
    scripts = entry_points(group='console_scripts')
    ep = next((x for x in scripts if x.name == 'mk_ligand_pdbqt'), None)
    if ep is None:
        raise ImportError
    meeko_main = ep.load()
except Exception:
    print("❌ Erreur : Meeko n'est pas détecté par Python.")
    sys.exit(1)

# 2. On crée le dossier de destination pour ton PFE
os.makedirs('PDBQT', exist_ok=True)

# 3. On récupère la liste de tes fichiers .pdb (Agomélatine, etc.)
fichiers_pdb = glob.glob('*.pdb')
if not fichiers_pdb:
    print("⚠️ Aucun fichier .pdb trouvé dans ce dossier.")
    sys.exit(0)

print(f"🚀 Début de la conversion de {len(fichiers_pdb)} ligands...\n")

# 4. Boucle magique de conversion sans bug de chemin
for f in fichiers_pdb:
    fichier_sortie = os.path.join('PDBQT', f.replace('.pdb', '.pdbqt'))
    print(f"-> Traitement de : {f}")
    
    # On transmet les arguments directement à Meeko
    sys.argv = ['mk_ligand_pdbqt', '-l', f, '-o', fichier_sortie]
    
    try:
        meeko_main()
    except SystemExit as e:
        # On empêche le script de s'arrêter au premier fichier converti
        if e.code != 0:
            print(f"   ⚠️ Attention : problème potentiel sur {f}")
    except Exception as e:
        print(f"   ❌ Erreur critique sur {f} : {e}")

print("\n--- ✅ Félicitations ! Tous tes fichiers sont convertis dans le dossier PDBQT ---")
