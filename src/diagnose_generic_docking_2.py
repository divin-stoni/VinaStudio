#!/usr/bin/env python3
"""
diagnose_generic_docking_2.py
================================

Suite du diagnostic précédent. Lecture seule, ne modifie rien.

  1. Code source de DockingWorker (src/docking/vina_worker.py) —
     comment le calcul tourne réellement et comment le CSV final est
     construit/exporté.
  2. Code source de create_scientific_scores (src/scientific_fusion.py)
     — pour voir exactement comment "MexB"/"MexR" sont recherchés
     (littéral en dur, ou generique).
  3. Contenu brut de TOUS les fichiers receptor_profiles/*.json —
     noms affichés réels, profile_id réels, et chemins pdbqt_path
     enregistrés.
  4. Pour chaque profil : vérifie si son pdbqt_path existe VRAIMENT
     sur le disque en ce moment (détecte un profil dont le fichier a
     disparu — cause silencieuse d'échec de validate()).
  5. Vérifie l'existence et le contenu de docking/ligands/prepared/
     (dossier fixe utilisé par VinaConfig.ligands_dir, indépendant de
     la cible) — une deuxième cause possible de "Configuration
     invalide".

Usage (depuis la racine du projet ou depuis src/) :
    python3 diagnose_generic_docking_2.py
"""

import inspect
import json
import sys
from pathlib import Path


def setup_import_path():
    here = Path(__file__).resolve().parent
    for c in (here, here.parent, here.parent.parent):
        if (c / "src").is_dir() and str(c) not in sys.path:
            sys.path.insert(0, str(c))
        if (c / "docking").is_dir() and str(c) not in sys.path:
            sys.path.insert(0, str(c))


def section(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def show_source(label, obj):
    print(f"\n--- {label} " + "-" * max(1, 60 - len(label)))
    try:
        print(inspect.getsource(obj))
    except Exception as exc:
        print(f"[Impossible d'afficher la source : {exc}]")


def main():
    setup_import_path()

    # ------------------------------------------------------------
    # IMPORTS
    # ------------------------------------------------------------
    vina_worker_mod = None
    scientific_fusion_mod = None
    receptor_profile_mod = None

    import_errors = []

    for modname, target_name in (
        ("docking.vina_worker", "vina_worker_mod"),
        ("scientific_fusion", "scientific_fusion_mod"),
        ("docking.receptor_profile", "receptor_profile_mod"),
    ):
        mod = None
        try:
            mod = __import__(f"src.{modname}", fromlist=["_"])
        except Exception as exc1:
            try:
                mod = __import__(modname, fromlist=["_"])
            except Exception as exc2:
                import_errors.append((modname, exc1, exc2))
        if target_name == "vina_worker_mod":
            vina_worker_mod = mod
        elif target_name == "scientific_fusion_mod":
            scientific_fusion_mod = mod
        elif target_name == "receptor_profile_mod":
            receptor_profile_mod = mod

    if import_errors:
        section("ÉCHEC D'IMPORT (pour information — la suite continue "
                "quand même pour ce qui est importable)")
        for name, e1, e2 in import_errors:
            print(f"\n{name} :")
            print(f"  en tant que src.{name} -> {e1}")
            print(f"  en tant que {name} -> {e2}")

    # ------------------------------------------------------------
    # 1. DockingWorker
    # ------------------------------------------------------------
    section("1. src/docking/vina_worker.py — DockingWorker")

    if vina_worker_mod is not None and hasattr(vina_worker_mod, "DockingWorker"):
        show_source("DockingWorker (classe complète)", vina_worker_mod.DockingWorker)
    else:
        print("DockingWorker non disponible (voir échecs d'import ci-dessus).")

    # ------------------------------------------------------------
    # 2. create_scientific_scores
    # ------------------------------------------------------------
    section("2. src/scientific_fusion.py — create_scientific_scores")

    if scientific_fusion_mod is not None:
        for name in dir(scientific_fusion_mod):
            if name.startswith("_"):
                continue
            obj = getattr(scientific_fusion_mod, name)
            if inspect.isfunction(obj) and obj.__module__ == scientific_fusion_mod.__name__:
                show_source(name, obj)
    else:
        print("scientific_fusion non disponible (voir échecs d'import ci-dessus).")

    # ------------------------------------------------------------
    # 3 & 4. Profils réels + vérification des chemins
    # ------------------------------------------------------------
    section("3 & 4. Contenu réel de receptor_profiles/*.json + "
            "vérification d'existence des pdbqt_path")

    profiles_dir = None
    if receptor_profile_mod is not None and hasattr(receptor_profile_mod, "PROFILES_DIR"):
        profiles_dir = Path(receptor_profile_mod.PROFILES_DIR)
    else:
        # repli : chercher un dossier receptor_profiles/ à côté du script
        for c in (Path(__file__).resolve().parent,
                   Path(__file__).resolve().parent.parent):
            candidate = c / "receptor_profiles"
            if candidate.is_dir():
                profiles_dir = candidate
                break

    if profiles_dir is None or not profiles_dir.exists():
        print(f"Dossier de profils introuvable (essayé : {profiles_dir}).")
    else:
        print(f"Dossier de profils : {profiles_dir}\n")
        json_files = sorted(profiles_dir.glob("*.json"))
        if not json_files:
            print("Aucun fichier .json trouvé dedans.")
        for jf in json_files:
            print(f"--- {jf.name} " + "-" * max(1, 50 - len(jf.name)))
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
            except Exception as exc:
                print(f"  [ERREUR lecture/parse JSON : {exc}]")
                continue

            print(json.dumps(data, indent=2, ensure_ascii=False))

            pdbqt_path = data.get("pdbqt_path")
            if pdbqt_path:
                p = Path(pdbqt_path)
                exists = p.exists()
                flag = "" if exists else "  ⚠ FICHIER MANQUANT SUR LE DISQUE"
                print(f"\n  Vérification disque : {p} -> existe={exists}{flag}")
            print()

    # ------------------------------------------------------------
    # 5. Dossier ligands fixe
    # ------------------------------------------------------------
    section("5. docking/ligands/prepared/ (dossier fixe utilisé par "
            "VinaConfig.ligands_dir, indépendant de la cible)")

    ligands_dir = None
    for c in (Path(__file__).resolve().parent,
              Path(__file__).resolve().parent.parent):
        candidate = c / "docking" / "ligands" / "prepared"
        if candidate.parent.parent.is_dir():
            ligands_dir = candidate
            break

    if ligands_dir is None:
        print("Impossible de localiser docking/ (lance ce script depuis "
              "la racine du projet ou depuis src/).")
    else:
        print(f"Chemin attendu : {ligands_dir}")
        print(f"Existe : {ligands_dir.exists()}")
        if ligands_dir.exists():
            pdbqt_files = sorted(ligands_dir.glob("*.pdbqt"))
            print(f"Nombre de fichiers .pdbqt dedans : {len(pdbqt_files)}")
            for f in pdbqt_files[:10]:
                print(f"  - {f.name}")
            if len(pdbqt_files) > 10:
                print(f"  ... et {len(pdbqt_files) - 10} de plus")
        else:
            print(
                "⚠ CE DOSSIER N'EXISTE PAS -> VinaEngine.validate() "
                "échouera systématiquement avec \"Dossier ligands "
                "introuvable\", quelle que soit la cible (MexB, MexR "
                "ou générique). Si tu vois \"Configuration invalide\" "
                "en cliquant sur Lancer le docking, c'est probablement "
                "ça, et ça n'a rien à voir avec le récepteur importé."
            )

    section("FIN DU DIAGNOSTIC 2")
    print("Colle l'intégralité de cette sortie dans la conversation.")


if __name__ == "__main__":
    main()
