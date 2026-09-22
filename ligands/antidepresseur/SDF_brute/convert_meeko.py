import os
import sys
import glob
from importlib.metadata import entry_points

# 1. Trouver automatiquement la commande Meeko cachée dans Windows
eps = [ep for ep in entry_points(group='console_scripts') if 'mk_ligand' in ep.name]
if not eps:
    print("Erreur : Meeko n'est pas détecté dans cet environnement Python.")
    sys.exit(1)

mod_name, func_name = eps[0].value.split(':')
mod = __import__(mod_name, fromlist=[func_name])
meeko_main = getattr(mod, func_name)

# 2. Créer le dossier de destination
os.makedirs('PDBQT', exist_ok=True)

# 3. Convertir automatiquement tous les fichiers .pdb présents
pdb_files = glob.glob('*.pdb')
print(f"--- Début de la conversion de {len(pdb_files)} fichiers .pdb ---")

for f in pdb_files:
    out_f = os.path.join('PDBQT', f.replace('.pdb', '.pdbqt'))
    print(f"Conversion : {f} -> {out_f}")
    # On transmet les arguments directement à Meeko
    sys.argv = ['mk_ligand_pdbqt', '-l', f, '-o', out_f]
    try:
        meeko_main()
    except SystemExit:
        pass

print("\n--- ✅ Tout est fini ! Tes fichiers t'attendent sagement dans le dossier PDBQT ---")
