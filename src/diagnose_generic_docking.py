#!/usr/bin/env python3
"""
diagnose_generic_docking.py
=============================

Diagnostic en lecture seule (ne modifie rien) pour comprendre pourquoi
le docking sur un récepteur importé (générique) n'écrit aucun
résultat, et pour préparer le couplage pompe+dérépresseur générique
(sur le modèle de MexB+MexR).

Ce script NE PATCHE RIEN. Il :

  1. Affiche le code source de create_target_config() et de la classe
     VinaEngine (src/docking/vina_engine.py) — pour voir comment les
     résultats de MexB/MexR sont enregistrés, et si un identifiant de
     récepteur générique est géré ou non.
  2. Affiche le code source de ReceptorManager / list_profile_ids /
     resolve_target_profile (src/docking/receptor_manager.py) et le
     schéma de ReceptorProfile (src/docking/receptor_profile.py).
  3. Liste tous les profils actuellement connus (built_in +
     user_defined), avec leur display_name et sa longueur — pour
     repérer les noms trop longs.
  4. REPRODUIT l'appel réel qui échoue : prend le premier profil
     user_defined trouvé, appelle create_target_config(pid, ...) puis
     VinaEngine(config).validate()/.check_vina() exactement comme le
     fait launch_docking() dans main_window.py, et affiche la
     traceback complète si ça casse.

Usage (depuis la racine du projet, ~/MexAB_MexR_Analyzer_BETA) :
    python3 diagnose_generic_docking.py

Ou depuis src/ :
    cd src && python3 diagnose_generic_docking.py
"""

import inspect
import sys
import traceback
from pathlib import Path


def setup_import_path():
    """Rend `from src.docking...` ET `from docking...` importables,
    peu importe d'où le script est lancé."""
    here = Path(__file__).resolve().parent
    candidates = [here, here.parent, here.parent.parent]
    for c in candidates:
        if (c / "src").is_dir():
            if str(c) not in sys.path:
                sys.path.insert(0, str(c))
        if (c / "docking").is_dir():
            if str(c) not in sys.path:
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
    import_errors = []

    vina_engine_mod = None
    receptor_manager_mod = None
    receptor_profile_mod = None

    try:
        from src.docking import vina_engine as vina_engine_mod
    except Exception as exc1:
        try:
            from docking import vina_engine as vina_engine_mod
        except Exception as exc2:
            import_errors.append(("src.docking.vina_engine", exc1, exc2))

    try:
        from src.docking import receptor_manager as receptor_manager_mod
    except Exception as exc1:
        try:
            from docking import receptor_manager as receptor_manager_mod
        except Exception as exc2:
            import_errors.append(("src.docking.receptor_manager", exc1, exc2))

    try:
        from src.docking import receptor_profile as receptor_profile_mod
    except Exception as exc1:
        try:
            from docking import receptor_profile as receptor_profile_mod
        except Exception as exc2:
            import_errors.append(("src.docking.receptor_profile", exc1, exc2))

    if import_errors:
        section("ÉCHEC D'IMPORT")
        for name, e1, e2 in import_errors:
            print(f"\n{name} :")
            print(f"  en tant que src.{name} -> {e1}")
            print(f"  en tant que {name} -> {e2}")
        print(
            "\nLance ce script depuis la racine du projet "
            "(~/MexAB_MexR_Analyzer_BETA) ou depuis src/."
        )
        sys.exit(1)

    # ------------------------------------------------------------
    # 1. SOURCE DE create_target_config / VinaEngine
    # ------------------------------------------------------------
    section("1. src/docking/vina_engine.py")

    if hasattr(vina_engine_mod, "create_target_config"):
        show_source(
            "create_target_config",
            vina_engine_mod.create_target_config,
        )
    else:
        print("create_target_config introuvable dans ce module.")

    if hasattr(vina_engine_mod, "VinaEngine"):
        show_source("VinaEngine (classe complète)", vina_engine_mod.VinaEngine)
    else:
        print("VinaEngine introuvable dans ce module.")

    # ------------------------------------------------------------
    # 2. SOURCE DE ReceptorManager / receptor_profile
    # ------------------------------------------------------------
    section("2. src/docking/receptor_manager.py")

    for name in ("ReceptorManager", "list_profile_ids", "resolve_target_profile"):
        if hasattr(receptor_manager_mod, name):
            show_source(name, getattr(receptor_manager_mod, name))
        else:
            print(f"\n{name} introuvable dans receptor_manager.py "
                  f"(peut-être dans receptor_profile.py).")

    section("2b. src/docking/receptor_profile.py")

    for name in dir(receptor_profile_mod):
        if name.startswith("_"):
            continue
        obj = getattr(receptor_profile_mod, name)
        if inspect.isclass(obj) or inspect.isfunction(obj):
            show_source(name, obj)

    # ------------------------------------------------------------
    # 3. LISTE DES PROFILS + LONGUEUR DES NOMS
    # ------------------------------------------------------------
    section("3. Profils connus (built_in + user_defined) et longueur des noms")

    list_profile_ids = getattr(receptor_manager_mod, "list_profile_ids", None)
    resolve_target_profile = getattr(
        receptor_manager_mod, "resolve_target_profile", None
    )

    generic_profile_ids = []

    if list_profile_ids is None or resolve_target_profile is None:
        print(
            "list_profile_ids / resolve_target_profile introuvables — "
            "impossible de lister les profils automatiquement."
        )
    else:
        try:
            pids = list(list_profile_ids())
        except Exception as exc:
            print(f"Erreur en appelant list_profile_ids() : {exc}")
            pids = []

        for pid in pids:
            try:
                profile = resolve_target_profile(pid)
            except Exception as exc:
                print(f"  [ERREUR] {pid} -> impossible à résoudre : {exc}")
                continue

            display_name = getattr(profile, "display_name", "?")
            profile_type = getattr(profile, "profile_type", "?")
            length = len(display_name)
            flag = "  ⚠ NOM LONG" if length > 15 else ""
            print(
                f"  {pid:<30} type={profile_type:<12} "
                f"display_name=\"{display_name}\" (len={length}){flag}"
            )

            if profile_type == "user_defined":
                generic_profile_ids.append(pid)

    # ------------------------------------------------------------
    # 4. REPRODUCTION DE L'APPEL RÉEL (launch_docking sur un
    #    récepteur générique)
    # ------------------------------------------------------------
    section("4. Reproduction de l'appel create_target_config() + VinaEngine "
            "sur un récepteur importé")

    if not generic_profile_ids:
        print(
            "Aucun profil user_defined trouvé pour l'instant — importe "
            "un récepteur dans l'app avant de relancer ce diagnostic "
            "si tu veux tester cette étape."
        )
    else:
        test_pid = generic_profile_ids[0]
        print(f"Test avec le profil : {test_pid}\n")

        create_target_config = vina_engine_mod.create_target_config
        VinaEngine = vina_engine_mod.VinaEngine

        # Racine des résultats, identique à celle utilisée par
        # main_window.py::launch_docking()
        project_root_candidates = [
            Path(__file__).resolve().parent,
            Path(__file__).resolve().parent.parent,
        ]
        results_root = None
        for c in project_root_candidates:
            if (c / "docking").is_dir():
                results_root = c / "docking" / "results" / "batch_vina_engine"
                break
        if results_root is None:
            results_root = Path("docking") / "results" / "batch_vina_engine"

        print(f"results_root utilisé pour le test : {results_root}\n")

        try:
            config = create_target_config(test_pid, results_root=results_root)
            print("[OK] create_target_config() n'a pas levé d'exception.")
            print(f"     Type du retour : {type(config)}")
            print(f"     Contenu : {config!r}")
        except Exception:
            print("[ÉCHEC] create_target_config() a levé une exception :\n")
            traceback.print_exc()
            print(
                "\n=> C'est très probablement la cause du \"aucun résultat "
                "exporté\" : create_target_config() ne sait construire une "
                "config que pour des cibles en dur (MexB/MexR), pas pour "
                "un identifiant de profil générique."
            )
            return

        try:
            engine = VinaEngine(config)
            print("\n[OK] VinaEngine(config) instancié sans exception.")
        except Exception:
            print("\n[ÉCHEC] VinaEngine(config) a levé une exception :\n")
            traceback.print_exc()
            return

        try:
            valid, errors = engine.validate()
            print(f"\nengine.validate() -> valid={valid}, errors={errors}")
        except Exception:
            print("\n[ÉCHEC] engine.validate() a levé une exception :\n")
            traceback.print_exc()
            return

        try:
            vina_ok, vina_message = engine.check_vina()
            print(f"engine.check_vina() -> ok={vina_ok}, message={vina_message}")
        except Exception:
            print("\n[ÉCHEC] engine.check_vina() a levé une exception :\n")
            traceback.print_exc()
            return

    section("FIN DU DIAGNOSTIC")
    print(
        "Colle l'intégralité de cette sortie dans la conversation — "
        "les sections 1, 2 et 2b donnent tout le code nécessaire pour "
        "écrire le patch (support des récepteurs génériques dans "
        "launch_docking, couplage pompe+dérépresseur, noms courts), "
        "et la section 4 confirme (ou infirme) l'hypothèse actuelle "
        "sur la cause du problème."
    )


if __name__ == "__main__":
    main()
