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

# 1. Remplace la limite fixe de 150px par une hauteur minimale confortable,
#    sans plafond bloquant -- la table garde sa propre barre de defilement
#    verticale des qu'il y a plus de lignes que l'espace disponible.
old_height = '''        self.docking_log.setMaximumHeight(
            150
        )'''

new_height = '''        self.docking_log.setMinimumHeight(150)
        self.docking_log.setWordWrap(True)
        self.docking_log.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )'''

if old_height not in content:
    raise SystemExit("✗ Bloc 'setMaximumHeight(150)' introuvable, patch annulé.")
content = content.replace(old_height, new_height, 1)

# 2. Ajoute le stretch factor lors de l'ajout au layout, pour que le
#    journal utilise l'espace vertical disponible en priorite.
old_addwidget = '''        log_layout.addWidget(
            self.docking_log
        )'''

new_addwidget = '''        log_layout.addWidget(
            self.docking_log,
            1,
        )'''

if old_addwidget not in content:
    raise SystemExit("✗ Ligne d'ajout au layout introuvable, patch annulé.")
content = content.replace(old_addwidget, new_addwidget, 1)

# 3. Redimensionne chaque ligne a son contenu (messages longs sur
#    plusieurs lignes) a chaque nouvelle entree de log.
old_scroll = "        self.docking_log.scrollToBottom()"
new_scroll = '''        self.docking_log.resizeRowsToContents()
        self.docking_log.scrollToBottom()'''

if old_scroll not in content:
    raise SystemExit("✗ Ligne 'scrollToBottom()' introuvable, patch annulé.")
content = content.replace(old_scroll, new_scroll, 1)

if content == original:
    raise SystemExit("✗ Aucune modification appliquée.")

TARGET.write_text(content, encoding="utf-8")
print("✓ main_window.py patché : journal de docking extensible, messages longs sur plusieurs lignes")
