#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch multi-recepteurs (visualisation) :

  Bug : BatchWorker.run() (visualization_bridge.py) indexe hit_results
  uniquement par nom de molecule ("results[hit.molecule] = ...").
  Si le meme ligand est docke sur MexB ET MexR (ou tout autre couple
  pompe/derepresseur), la seconde cible traitee ECRASE la premiere dans
  le dictionnaire -> un seul recepteur visible en 2D/3D, generalement
  le derniere de known_target_labels() (le derepresseur).

  Fix :
    1. hit_results est desormais indexe par "<molecule> — <target>"
       (fonction hit_result_key), donc les deux cibles coexistent.
    2. export_visualization_results() exporte TOUTES les cibles
       presentes dans les resultats (avant : une seule, celle du
       premier hit), avec un sous-dossier par cible des qu'il y en a
       plus d'une.
    3. Le reste (combos de molecules, viewer 2D/3D, tableau des
       residus) fonctionne deja generiquement par cle de dictionnaire :
       aucun autre changement necessaire.

Sauvegarde horodatee automatique avant ecriture sur CHAQUE fichier,
verification syntaxique (py_compile) apres patch, restauration
automatique si la compilation echoue.
"""

import py_compile
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path.home() / "MexAB_MexR_Analyzer_BETA" / "src"
BRIDGE_PATH = ROOT / "gui" / "visualization_bridge.py"
MAIN_WINDOW_PATH = ROOT / "gui" / "main_window.py"


BRIDGE_REPLACEMENTS = [
    (
        '@dataclass\n'
        'class Hit:\n'
        '    molecule: str\n'
        '    score: float\n'
        '    ligand_pdbqt: Path\n'
        '    receptor: Path\n'
        '    target: str\n',
        '@dataclass\n'
        'class Hit:\n'
        '    molecule: str\n'
        '    score: float\n'
        '    ligand_pdbqt: Path\n'
        '    receptor: Path\n'
        '    target: str\n'
        '\n'
        '\n'
        'def hit_result_key(target: str, molecule: str) -> str:\n'
        '    """Clé unique pour hit_results : deux cibles différentes (MexB, MexR,\n'
        '    ou tout autre couple pompe/dérépresseur) peuvent doquer un ligand du\n'
        '    même nom — sans le suffixe cible, la seconde cible traitée écrasait\n'
        '    purement et simplement les résultats de la première dans le\n'
        '    dictionnaire (c\'était toujours la dernière de known_target_labels()\n'
        '    qui survivait, en général le dérépresseur)."""\n'
        '    return f"{molecule} — {target}"\n',
    ),
    (
        '        for index, hit in enumerate(self.hits, start=1):\n'
        '            self.progress.emit(hit.molecule, index, total)\n',
        '        for index, hit in enumerate(self.hits, start=1):\n'
        '            self.progress.emit(f"{hit.molecule} ({hit.target})", index, total)\n',
    ),
    (
        '                results[hit.molecule] = {\n'
        '                    "interactions": interactions,\n'
        '                    "diagram": str(output_png),\n'
        '                    "complex": str(_plip_complex_pdb(hit.target, hit.molecule)),\n'
        '                    "target": hit.target,\n'
        '                }\n',
        '                key = hit_result_key(hit.target, hit.molecule)\n'
        '                results[key] = {\n'
        '                    "interactions": interactions,\n'
        '                    "diagram": str(output_png),\n'
        '                    "complex": str(_plip_complex_pdb(hit.target, hit.molecule)),\n'
        '                    "target": hit.target,\n'
        '                    "molecule": hit.molecule,\n'
        '                }\n',
    ),
    (
        'def export_visualization_results(target: str, batch_payload: dict, destination_dir: Path) -> Path:\n'
        '    destination_dir = Path(destination_dir)\n'
        '    destination_dir.mkdir(parents=True, exist_ok=True)\n'
        '\n'
        '    diagrams_src = _diagrams_dir(target)\n'
        '    if diagrams_src.exists():\n'
        '        shutil.copytree(diagrams_src, destination_dir / "diagrammes_2d", dirs_exist_ok=True)\n'
        '\n'
        '    plip_src = _plip_workdir(target)\n'
        '    if plip_src.exists():\n'
        '        shutil.copytree(plip_src, destination_dir / "plip_xml_complex", dirs_exist_ok=True)\n'
        '\n'
        '    summary_csv = destination_dir / "residus_interactions.csv"\n'
        '    with summary_csv.open("w", encoding="utf-8", newline="") as handle:\n'
        '        writer = csv.DictWriter(\n'
        '            handle,\n'
        '            fieldnames=["molecule", "residue", "residue_id", "chain", "distance", "interaction_types"],\n'
        '        )\n'
        '        writer.writeheader()\n'
        '        for molecule, data in batch_payload.get("results", {}).items():\n'
        '            for row in data["interactions"]["summary"]:\n'
        '                writer.writerow({"molecule": molecule, **row})\n'
        '\n'
        '    return destination_dir\n',
        'def export_visualization_results(batch_payload: dict, destination_dir: Path) -> Path:\n'
        '    """Exporte TOUTES les cibles présentes dans batch_payload (MexB, MexR,\n'
        '    ou tout autre couple), pas une seule : avant, l\'appelant ne passait\n'
        '    qu\'une cible et le dossier d\'une autre cible dockée dans la même\n'
        '    campagne n\'était jamais copié."""\n'
        '    destination_dir = Path(destination_dir)\n'
        '    destination_dir.mkdir(parents=True, exist_ok=True)\n'
        '\n'
        '    results = batch_payload.get("results", {})\n'
        '\n'
        '    targets = sorted({\n'
        '        data.get("target", DEFAULT_TARGET) for data in results.values()\n'
        '    }) or [DEFAULT_TARGET]\n'
        '\n'
        '    # Une seule cible : structure plate, inchangée pour les campagnes\n'
        '    # mono-récepteur existantes. Plusieurs cibles : un sous-dossier par\n'
        '    # cible pour ne jamais mélanger leurs diagrammes/complexes.\n'
        '    single_target = len(targets) == 1\n'
        '\n'
        '    for target in targets:\n'
        '        target_dest = destination_dir if single_target else destination_dir / target\n'
        '\n'
        '        diagrams_src = _diagrams_dir(target)\n'
        '        if diagrams_src.exists():\n'
        '            shutil.copytree(diagrams_src, target_dest / "diagrammes_2d", dirs_exist_ok=True)\n'
        '\n'
        '        plip_src = _plip_workdir(target)\n'
        '        if plip_src.exists():\n'
        '            shutil.copytree(plip_src, target_dest / "plip_xml_complex", dirs_exist_ok=True)\n'
        '\n'
        '    summary_csv = destination_dir / "residus_interactions.csv"\n'
        '    with summary_csv.open("w", encoding="utf-8", newline="") as handle:\n'
        '        writer = csv.DictWriter(\n'
        '            handle,\n'
        '            fieldnames=["target", "molecule", "residue", "residue_id", "chain", "distance", "interaction_types"],\n'
        '        )\n'
        '        writer.writeheader()\n'
        '        for key, data in results.items():\n'
        '            molecule = data.get("molecule", key)\n'
        '            target = data.get("target", DEFAULT_TARGET)\n'
        '            for row in data["interactions"]["summary"]:\n'
        '                writer.writerow({"target": target, "molecule": molecule, **row})\n'
        '\n'
        '    return destination_dir\n',
    ),
]

MAIN_WINDOW_REPLACEMENTS = [
    (
        '        rows = []\n'
        '        for molecule, data in self.hit_results.items():\n'
        '            for res in data["interactions"]["summary"]:\n'
        '                rows.append(\n'
        '                    (\n'
        '                        res["residue"],\n'
        '                        res["chain"],\n'
        '                        str(res["residue_id"]),\n'
        '                        res["interaction_types"],\n'
        '                        molecule,\n'
        '                    )\n'
        '                )\n',
        '        rows = []\n'
        '        for key, data in self.hit_results.items():\n'
        '            for res in data["interactions"]["summary"]:\n'
        '                rows.append(\n'
        '                    (\n'
        '                        res["residue"],\n'
        '                        res["chain"],\n'
        '                        str(res["residue_id"]),\n'
        '                        res["interaction_types"],\n'
        '                        key,\n'
        '                    )\n'
        '                )\n',
    ),
    (
        '        try:\n'
        '            target = self.current_hits[0].target if self.current_hits else viz_bridge.DEFAULT_TARGET\n'
        '\n'
        '            export_dir = viz_bridge.export_visualization_results(\n'
        '                target,\n'
        '                {"results": self.hit_results, "errors": self.batch_errors},\n'
        '                Path(destination) / "export_visualisation",\n'
        '            )\n',
        '        try:\n'
        '            export_dir = viz_bridge.export_visualization_results(\n'
        '                {"results": self.hit_results, "errors": self.batch_errors},\n'
        '                Path(destination) / "export_visualisation",\n'
        '            )\n',
    ),
]


def apply_replacements(path: Path, replacements):
    if not path.is_file():
        print(f"Fichier introuvable : {path}")
        return False

    original = path.read_text(encoding="utf-8")
    text = original

    for old, new in replacements:
        count = text.count(old)
        if count == 0:
            print(f"ÉCHEC sur {path.name} : bloc introuvable :\n---\n{old[:150]}...\n---")
            return False
        if count > 1:
            print(f"ÉCHEC sur {path.name} : bloc trouvé {count} fois (devrait être unique) :\n---\n{old[:150]}...\n---")
            return False
        text = text.replace(old, new)

    if text == original:
        print(f"{path.name} : rien à changer (déjà patché ?).")
        return True

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(path.suffix + f".bak_{timestamp}")
    shutil.copy2(path, backup_path)
    print(f"Sauvegarde : {backup_path}")

    path.write_text(text, encoding="utf-8")

    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError as exc:
        print(f"ÉCHEC de compilation sur {path.name}, restauration de la sauvegarde :")
        print(exc)
        shutil.copy2(backup_path, path)
        return False

    print(f"{path.name} : patch appliqué avec succès, syntaxe vérifiée.")
    return True


def main():
    ok_bridge = apply_replacements(BRIDGE_PATH, BRIDGE_REPLACEMENTS)
    ok_main = apply_replacements(MAIN_WINDOW_PATH, MAIN_WINDOW_REPLACEMENTS)

    if not (ok_bridge and ok_main):
        sys.exit(1)


if __name__ == "__main__":
    main()
