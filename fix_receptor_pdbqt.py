#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_receptor_pdbqt.py

CAUSE REELLE de l'echec systematique du docking sur les nouveaux recepteurs :

    PDBQT parsing error: Unknown or inappropriate tag found in rigid receptor.
     > HEADER    MEMBRANE PROTEIN   19-MAY-04   1T9X

Les fichiers .pdbqt des recepteurs importes ont conserve les enregistrements
PDB d'origine (HEADER, TITLE, COMPND, SEQRES, HELIX, CONECT, MASTER...).
AutoDock Vina 1.2.x refuse TOUT tag inconnu dans un recepteur rigide et sort
immediatement avec le code retour 1 -> tous les ligands en FAILED, CSV
exporte mais vide de scores.

Ce script :
  1. scanne tous les .pdbqt de docking/receptor/ ;
  2. sauvegarde les fichiers fautifs dans _archive_pdbqt_raw/<horodatage>/ ;
  3. les reecrit en ne gardant que ATOM / HETATM / TER / END / ROOT-BRANCH ;
  4. installe une desinfection PERMANENTE dans ReceptorManager.validate()
     pour que tout futur recepteur importe soit nettoye automatiquement ;
  5. affiche l'inventaire des profils (profile_id, display_name, role,
     longueur du nom) pour preparer le couplage pompe/derepresseur.

Lecture seule pour tout le reste. Rien n'est supprime, tout est sauvegarde.
"""

from __future__ import annotations

import datetime
import json
import shutil
import sys
from pathlib import Path

# ----------------------------------------------------------------------
# Tags acceptes par Vina dans un recepteur rigide
# ----------------------------------------------------------------------
ALLOWED_PREFIXES = (
    "ATOM",
    "HETATM",
    "TER",
    "END",
    "ROOT",
    "ENDROOT",
    "BRANCH",
    "ENDBRANCH",
    "TORSDOF",
    "MODEL",
    "ENDMDL",
)

STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def find_project_root() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in [here, *here.parents]:
        if (candidate / "docking" / "receptor").is_dir():
            return candidate
        if (candidate / "src" / "docking" / "receptor_profile.py").is_file():
            return candidate
    home_guess = Path.home() / "MexAB_MexR_Analyzer_BETA"
    if home_guess.is_dir():
        return home_guess
    raise SystemExit(
        "[ABANDON] Racine du projet introuvable. "
        "Lance le script depuis ~/MexAB_MexR_Analyzer_BETA ou depuis src/."
    )


def line_is_allowed(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return stripped.upper().startswith(ALLOWED_PREFIXES)


# ======================================================================
# ETAPE 1 — DESINFECTION DES PDBQT RECEPTEURS
# ======================================================================

def sanitize_all_receptors(project_root: Path) -> None:
    receptor_dir = project_root / "docking" / "receptor"

    print("=" * 72)
    print("ETAPE 1 — DESINFECTION DES PDBQT RECEPTEURS")
    print("=" * 72)

    if not receptor_dir.is_dir():
        print(f"[!] Dossier absent : {receptor_dir}")
        return

    files = sorted(receptor_dir.rglob("*.pdbqt"))

    if not files:
        print(f"[!] Aucun .pdbqt trouve sous {receptor_dir}")
        return

    backup_root = project_root / "_archive_pdbqt_raw" / STAMP
    n_fixed = 0

    for path in files:
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            print(f"  [ERREUR] lecture {path.name} : {exc}")
            continue

        lines = raw.splitlines()
        bad = [
            ln for ln in lines
            if ln.strip() and not line_is_allowed(ln)
        ]

        rel = path.relative_to(project_root)

        if not bad:
            print(f"  [OK]    {rel}  ({len(lines)} lignes, deja propre)")
            continue

        # Apercu des tags fautifs
        tags = []
        for ln in bad:
            tag = ln.split()[0] if ln.split() else "?"
            if tag not in tags:
                tags.append(tag)

        backup_path = backup_root / rel
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_path)

        kept = [ln for ln in lines if line_is_allowed(ln)]

        if not any(
            ln.strip().upper().startswith(("ATOM", "HETATM"))
            for ln in kept
        ):
            print(
                f"  [DANGER] {rel} : aucun atome apres nettoyage, "
                "fichier NON modifie."
            )
            continue

        path.write_text("\n".join(kept) + "\n", encoding="utf-8")
        n_fixed += 1

        print(f"  [CORRIGE] {rel}")
        print(f"            {len(bad)} ligne(s) hors-norme supprimee(s)")
        print(f"            tags retires : {', '.join(tags[:12])}")
        n_atoms = sum(
            1 for ln in kept
            if ln.strip().upper().startswith(("ATOM", "HETATM"))
        )
        print(f"            atomes conserves : {n_atoms}")

    print()
    print(f"  -> {n_fixed} fichier(s) corrige(s) sur {len(files)}.")
    if n_fixed:
        print(f"  -> Sauvegardes : {backup_root}")
    print()


# ======================================================================
# ETAPE 2 — DESINFECTION PERMANENTE DANS receptor_manager.py
# ======================================================================

ANCHOR = """        # --------------------------------------------------------------
        # Parsing
        # --------------------------------------------------------------

        atoms = self.parse_atoms()"""

INJECTED = '''        # --------------------------------------------------------------
        # Desinfection PDBQT (obligatoire pour AutoDock Vina)
        # --------------------------------------------------------------
        # Vina refuse tout tag non-PDBQT dans un recepteur rigide
        # (HEADER, TITLE, COMPND, SEQRES, HELIX, CONECT, MASTER...) et
        # sort avec le code retour 1 sans docker un seul ligand.
        # Tout recepteur importe est donc nettoye ici, une fois pour
        # toutes, avec sauvegarde du fichier d'origine.

        try:
            removed = sanitize_receptor_pdbqt(self.path)
            if removed:
                info.warnings.append(
                    f"{removed} ligne(s) non-PDBQT supprimee(s) "
                    "(incompatibles avec AutoDock Vina) ; "
                    "fichier d'origine sauvegarde en .raw_pdbqt"
                )
        except Exception as exc:
            info.warnings.append(
                f"Desinfection PDBQT impossible : {exc}"
            )

        # --------------------------------------------------------------
        # Parsing
        # --------------------------------------------------------------

        atoms = self.parse_atoms()'''

HELPER = '''

# ======================================================================
# DESINFECTION PDBQT — compatibilite AutoDock Vina
# ======================================================================

_VINA_ALLOWED_PREFIXES = (
    "ATOM",
    "HETATM",
    "TER",
    "END",
    "ROOT",
    "ENDROOT",
    "BRANCH",
    "ENDBRANCH",
    "TORSDOF",
    "MODEL",
    "ENDMDL",
)


def sanitize_receptor_pdbqt(path) -> int:
    """
    Supprime d'un fichier PDBQT de recepteur toute ligne dont le tag
    n'est pas reconnu par AutoDock Vina (HEADER, TITLE, COMPND, SEQRES,
    HELIX, SHEET, CONECT, MASTER, ANISOU...).

    Vina 1.2.x rejette le fichier entier des la premiere ligne inconnue :
        PDBQT parsing error: Unknown or inappropriate tag found
        in rigid receptor.
    ... et rend le code 1, ce qui fait echouer TOUS les ligands.

    Retourne le nombre de lignes supprimees. Ne fait rien si le fichier
    est deja propre. Sauvegarde l'original en <nom>.raw_pdbqt avant
    toute modification.
    """

    from pathlib import Path as _Path

    path = _Path(path)

    if not path.is_file():
        return 0

    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines()

    kept = []
    removed = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.upper().startswith(_VINA_ALLOWED_PREFIXES):
            kept.append(line)
        else:
            removed += 1

    if removed == 0:
        return 0

    has_atoms = any(
        ln.strip().upper().startswith(("ATOM", "HETATM"))
        for ln in kept
    )

    if not has_atoms:
        raise ValueError(
            "Nettoyage refuse : aucun atome ATOM/HETATM ne subsisterait."
        )

    backup = path.with_suffix(path.suffix + ".raw_pdbqt")
    if not backup.exists():
        backup.write_text(raw, encoding="utf-8")

    path.write_text("\\n".join(kept) + "\\n", encoding="utf-8")

    return removed
'''


def patch_receptor_manager(project_root: Path) -> None:
    print("=" * 72)
    print("ETAPE 2 — DESINFECTION PERMANENTE (receptor_manager.py)")
    print("=" * 72)

    candidates = [
        project_root / "src" / "docking" / "receptor_manager.py",
        project_root / "docking" / "receptor_manager.py",
    ]

    target = next((p for p in candidates if p.is_file()), None)

    if target is None:
        print("  [!] receptor_manager.py introuvable, etape ignoree.")
        print()
        return

    source = target.read_text(encoding="utf-8")

    if "def sanitize_receptor_pdbqt" in source:
        print(f"  [DEJA FAIT] {target} contient deja la desinfection.")
        print()
        return

    if source.count(ANCHOR) != 1:
        print(
            f"  [!] Point d'ancrage introuvable ou ambigu dans {target} "
            f"({source.count(ANCHOR)} occurrence(s))."
        )
        print("      La desinfection permanente n'a PAS ete installee.")
        print("      L'etape 1 reste valable : le docking doit deja marcher.")
        print()
        return

    backup = target.with_name(f"{target.name}.bak_{STAMP}")
    shutil.copy2(target, backup)

    patched = source.replace(ANCHOR, INJECTED, 1)

    marker = "# GESTIONNAIRE DU RÉCEPTEUR"
    if marker in patched:
        patched = patched.replace(marker, HELPER.strip() + "\n\n\n" + marker, 1)
    else:
        patched = patched + HELPER

    target.write_text(patched, encoding="utf-8")

    print(f"  [OK] {target} patche.")
    print(f"       Sauvegarde : {backup.name}")
    print("       -> tout recepteur importe est desormais nettoye")
    print("          automatiquement a la validation.")
    print()


# ======================================================================
# ETAPE 3 — INVENTAIRE DES PROFILS
# ======================================================================

def inventory_profiles(project_root: Path) -> None:
    print("=" * 72)
    print("ETAPE 3 — INVENTAIRE DES PROFILS DE RECEPTEURS")
    print("=" * 72)

    profiles_dir = project_root / "receptor_profiles"

    if not profiles_dir.is_dir():
        print(f"  [!] Dossier introuvable : {profiles_dir}")
        print()
        return

    files = sorted(profiles_dir.glob("*.json"))

    if not files:
        print(f"  [!] Aucun profil dans {profiles_dir}")
        print()
        return

    print(
        f"  {'profile_id':<34} {'display_name':<34} "
        f"{'len':>4} {'role':<12} {'valide':<7} partner"
    )
    print("  " + "-" * 104)

    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"  [ERREUR] {path.name} : {exc}")
            continue

        pid = str(data.get("profile_id", path.stem))
        dname = str(data.get("display_name", ""))
        role = str(data.get("role") or "-")
        valid = "oui" if data.get("validated") else "NON"
        partner = str(data.get("partner_id") or "-")
        flag = " <<< trop long" if len(dname) > 15 else ""

        print(
            f"  {pid:<34} {dname:<34} {len(dname):>4} "
            f"{role:<12} {valid:<7} {partner}{flag}"
        )

        pdbqt = data.get("pdbqt_path", "")
        if pdbqt:
            p = Path(pdbqt)
            if not p.is_absolute():
                p = project_root / p
            if not p.is_file():
                print(f"       [!] PDBQT introuvable : {p}")

    print()
    print(f"  {len(files)} profil(s) dans {profiles_dir}")
    print()


# ======================================================================

def main() -> None:
    project_root = find_project_root()

    print()
    print("#" * 72)
    print(f"# VINASTUDIO — CORRECTIF RECEPTEURS PDBQT   ({STAMP})")
    print(f"# Racine projet : {project_root}")
    print("#" * 72)
    print()

    sanitize_all_receptors(project_root)
    patch_receptor_manager(project_root)
    inventory_profiles(project_root)

    print("=" * 72)
    print("TERMINE.")
    print("Relance l'application et refais un docking sur un recepteur")
    print("importe (meme un seul ligand de test suffit).")
    print("=" * 72)
    print()


if __name__ == "__main__":
    sys.exit(main())
