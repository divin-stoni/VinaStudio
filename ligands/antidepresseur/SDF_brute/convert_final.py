import os, sys, glob, subprocess

os.makedirs('PDBQT', exist_ok=True)

# Trouve mk_ligand_pdbqt via pip show (méthode 100% fiable)
result = subprocess.run(
    [sys.executable, '-m', 'pip', 'show', '-f', 'meeko'],
    capture_output=True, text=True
)

script_rel = None
for line in result.stdout.splitlines():
    if 'mk_ligand_pdbqt' in line and ('.exe' in line or '.py' in line):
        script_rel = line.strip()
        break

if not script_rel:
    print("❌ mk_ligand_pdbqt introuvable. Lance : pip show -f meeko")
    sys.exit(1)

# Reconstituer le chemin absolu
for line in result.stdout.splitlines():
    if line.startswith('Location:'):
        base = line.split(':', 1)[1].strip()
        break

# Les scripts sont un niveau AU-DESSUS de site-packages
scripts_dir = os.path.normpath(os.path.join(base, '..', '..', 'Scripts'))
script_path = os.path.join(scripts_dir, os.path.basename(script_rel))

print(f"✅ Script trouvé : {script_path}")

fichiers_pdb = glob.glob('*.pdb')
print(f"🚀 Conversion de {len(fichiers_pdb)} ligands...\n")

for pdb in fichiers_pdb:
    pdbqt = os.path.join('PDBQT', pdb.replace('.pdb', '.pdbqt'))
    print(f" -> {pdb} ...")
    cmd = [sys.executable, script_path, '-l', pdb, '-o', pdbqt]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"    ⚠️ {r.stderr.strip()[:120]}")

print("\n✅ Terminé ! Vérifie le dossier PDBQT")
