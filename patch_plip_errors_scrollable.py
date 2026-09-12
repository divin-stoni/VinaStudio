# -*- coding: utf-8 -*-
from pathlib import Path
import shutil
import datetime

TARGET = Path("src/gui/main_window.py")
backup = TARGET.with_suffix(TARGET.suffix + f".bak_{datetime.datetime.now():%Y%m%d_%H%M%S}")
shutil.copy2(TARGET, backup)
print(f"✓ Sauvegarde créée : {backup}")

content = TARGET.read_text(encoding="utf-8")
original = content

old = '''        self.plip_errors_label = self._t_label(
            "viz_plip_no_errors_yet",
            "Aucune erreur pour le moment.",
            "SectionDescription",
        )

        panel_layout.addWidget(self.plip_errors_label)'''

new = '''        self.plip_errors_label = self._t_label(
            "viz_plip_no_errors_yet",
            "Aucune erreur pour le moment.",
            "SectionDescription",
        )
        self.plip_errors_label.setWordWrap(True)
        self.plip_errors_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.plip_errors_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # Zone defilante independante : le texte peut grandir avec le
        # nombre d'erreurs accumulees, sans jamais faire deborder le
        # panneau ni pousser le reste de l'interface hors de la fenetre.
        plip_errors_scroll = QScrollArea()
        plip_errors_scroll.setWidgetResizable(True)
        plip_errors_scroll.setFrameShape(QFrame.NoFrame)
        plip_errors_scroll.setMinimumHeight(90)
        plip_errors_scroll.setMaximumHeight(320)
        plip_errors_scroll.setWidget(self.plip_errors_label)

        panel_layout.addWidget(plip_errors_scroll)'''

if old not in content:
    raise SystemExit("✗ Bloc 'plip_errors_label' introuvable, patch annulé.")
content = content.replace(old, new, 1)

if content == original:
    raise SystemExit("✗ Aucune modification appliquée.")

TARGET.write_text(content, encoding="utf-8")
print("✓ main_window.py patché : panneau d'erreurs PLIP extensible avec défilement")
