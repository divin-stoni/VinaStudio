import os, sys, glob

os.makedirs('PDBQT', exist_ok=True)

try:
    from meeko import MoleculePreparation
    from rdkit import Chem
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "rdkit", "meeko"])
    from meeko import MoleculePreparation
    from rdkit import Chem

fichiers_pdb = glob.glob('*.pdb')
print(f"🚀 Conversion de {len(fichiers_pdb)} ligands via API interne...\n")

succes, echecs = 0, []

for f in fichiers_pdb:
    print(f" -> {f} ...")
    fichier_sortie = os.path.join('PDBQT', f.replace('.pdb', '.pdbqt'))

    try:
        # Lecture via Python (gère les accents) puis passage à RDKit comme string
        with open(f, 'r', encoding='utf-8', errors='replace') as fh:
            pdb_block = fh.read()

        mol = Chem.MolFromPDBBlock(pdb_block, removeHs=False)
        if mol is None:
            print(f"    ❌ RDKit n'a pas pu lire {f}")
            echecs.append(f)
            continue

        preparator = MoleculePreparation()
        mol_list = preparator.prepare(mol)

        pdbqt_string = ""
        for setup in mol_list:
            pdbqt_string += setup.write_pdbqt_string()

        with open(fichier_sortie, 'w', encoding='utf-8') as out:
            out.write(pdbqt_string)

        succes += 1

    except Exception as e:
        print(f"    ❌ Erreur sur {f} : {e}")
        echecs.append(f)

print(f"\n✅ {succes} ligands convertis avec succès")
if echecs:
    print(f"⚠️  {len(echecs)} échecs :")
    for e in echecs:
        print(f"   - {e}")
print("📁 Tes fichiers .pdbqt sont dans le dossier PDBQT")
