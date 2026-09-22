#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch main_window.py :
  1) Retire "Crédits" de la barre d'onglets (creation + retranslate + noms).
  2) Remplace show_about_dialog() par une boite "A propos" avec un lien
     cliquable "Credits" (souligne), qui bascule vers la page credits_page
     (via switch_primary(4), qui gere deja l'ouverture paresseuse).

Sauvegarde horodatee automatique avant ecriture, verification syntaxique
(py_compile) apres patch ; restauration automatique si la compilation echoue.
"""

import py_compile
import shutil
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_PATH = Path.home() / "MexAB_MexR_Analyzer_BETA" / "src" / "gui" / "main_window.py"


REPLACEMENTS = [
    # 1) Boucle de creation des boutons d'onglets (barre du haut)
    (
        'for index, text in enumerate(["Docking", "Analyse", "Visualisation", "Phytomolécules", "Crédits"]):',
        'for index, text in enumerate(["Docking", "Analyse", "Visualisation", "Phytomolécules"]):',
    ),
    # 2) retranslate() : memes libelles, sans Credits
    (
        'tab_labels = [t("side_docking"), t("nav_analysis"), t("nav_visualization"), "Phytomolécules", "Crédits"]',
        'tab_labels = [t("side_docking"), t("nav_analysis"), t("nav_visualization"), "Phytomolécules"]',
    ),
    # 3) switch_primary() : liste des noms affiches dans la barre de statut
    (
        '        names = [\n'
        '            "Docking",\n'
        '            "Analyse",\n'
        '            "Visualisation",\n'
        '            "Phytomolécules",\n'
        '            "Crédits",\n'
        '        ]\n',
        '        names = [\n'
        '            "Docking",\n'
        '            "Analyse",\n'
        '            "Visualisation",\n'
        '            "Phytomolécules",\n'
        '        ]\n',
    ),
    # 4) show_about_dialog() : boite personnalisee avec lien "Credits"
    (
        '    def show_about_dialog(self):\n'
        '\n'
        '        QMessageBox.about(\n'
        '            self,\n'
        '            "À propos de VINA Studio",\n'
        '            "VINA Studio\\n"\n'
        '            "Molecular Docking & Interaction Analysis\\n\\n"\n'
        '            "Pipeline complet : préparation des ligands, docking "\n'
        '            "AutoDock Vina, analyse statistique (MexB/MexR) et "\n'
        '            "visualisation des interactions.",\n'
        '        )\n',
        '    def show_about_dialog(self):\n'
        '        from PySide6.QtWidgets import QDialog\n'
        '\n'
        '        dialog = QDialog(self)\n'
        '        dialog.setWindowTitle("À propos de VINA Studio")\n'
        '        dialog.setMinimumWidth(380)\n'
        '\n'
        '        layout = QVBoxLayout(dialog)\n'
        '        layout.setContentsMargins(24, 20, 24, 16)\n'
        '        layout.setSpacing(14)\n'
        '\n'
        '        text_label = QLabel(\n'
        '            "<b>VINA Studio</b><br>"\n'
        '            "Molecular Docking &amp; Interaction Analysis<br><br>"\n'
        '            "Pipeline complet : préparation des ligands, docking "\n'
        '            "AutoDock Vina, analyse statistique (MexB/MexR) et "\n'
        '            "visualisation des interactions.<br><br>"\n'
        '            \'<a href="credits" style="text-decoration: underline;">Crédits</a>\'\n'
        '        )\n'
        '        text_label.setTextFormat(Qt.RichText)\n'
        '        text_label.setOpenExternalLinks(False)\n'
        '        text_label.setWordWrap(True)\n'
        '        text_label.linkActivated.connect(\n'
        '            lambda _link: self._open_credits_from_about(dialog)\n'
        '        )\n'
        '        layout.addWidget(text_label)\n'
        '\n'
        '        close_button = LiquidGlassButton("Fermer")\n'
        '        close_button.setCursor(Qt.PointingHandCursor)\n'
        '        close_button.clicked.connect(dialog.accept)\n'
        '        layout.addWidget(close_button, 0, Qt.AlignRight)\n'
        '\n'
        '        dialog.exec()\n'
        '\n'
        '    def _open_credits_from_about(self, dialog):\n'
        '        # Le lien "Credits" de la boite "A propos" bascule vers la page\n'
        '        # credits_page (switch_primary gere deja le scan paresseux du\n'
        '        # dossier et le changement de page de travail).\n'
        '        dialog.accept()\n'
        '        self.switch_primary(4)\n',
    ),
]


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    if not path.is_file():
        print(f"Fichier introuvable : {path}")
        sys.exit(1)

    original = path.read_text(encoding="utf-8")
    text = original

    for old, new in REPLACEMENTS:
        count = text.count(old)
        if count == 0:
            print(f"ÉCHEC : bloc introuvable (le fichier a peut-être déjà changé) :\n---\n{old[:120]}...\n---")
            sys.exit(1)
        if count > 1:
            print(f"ÉCHEC : bloc trouvé {count} fois (devrait être unique) :\n---\n{old[:120]}...\n---")
            sys.exit(1)
        text = text.replace(old, new)

    if text == original:
        print("Rien à changer (le fichier semble déjà patché).")
        sys.exit(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(path.suffix + f".bak_{timestamp}")
    shutil.copy2(path, backup_path)
    print(f"Sauvegarde : {backup_path}")

    path.write_text(text, encoding="utf-8")

    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError as exc:
        print("ÉCHEC de compilation après patch, restauration de la sauvegarde :")
        print(exc)
        shutil.copy2(backup_path, path)
        sys.exit(1)

    print("Patch appliqué avec succès, syntaxe vérifiée.")


if __name__ == "__main__":
    main()
