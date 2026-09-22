#!/usr/bin/env bash
# ============================================================================
# apply_liquid_glass.sh (v2 — "glace")
#
# Applique le style "glace" (verre translucide givré, coins arrondis,
# ombres portées) sur gui/main_window.py de VINA Studio.
#
# Contrairement à la v1, l'accent n'est plus un bleu plein : boutons,
# onglets actifs, cases cochées et cartes sélectionnées sont maintenant
# du verre bleu translucide (fond qui transparaît au travers), avec un
# liseré "biseau de glace" (clair en haut/gauche, plus froid en
# bas/droite) et un texte bleu glacé au lieu de blanc.
#
# Ce script :
#   1. Localise automatiquement gui/main_window.py dans le dossier courant
#      (ou un sous-dossier, ex. src/gui/main_window.py).
#   2. Fait une sauvegarde horodatée (même convention que vos .bak_* existants).
#   3. Applique le patch.
#   4. Vérifie que le fichier patché est syntaxiquement valide.
#
# Usage : placez ce script à la racine de votre projet VINA Studio puis :
#   bash apply_liquid_glass.sh
#
# Si vous aviez déjà appliqué la v1 (bleu plein), relancez ce script sur
# le fichier ORIGINAL (restaurez d'abord un .bak_* d'avant la v1) : ce
# patch part du fichier de base, pas de la v1.
# ============================================================================

set -euo pipefail

echo "== Recherche de main_window.py =="

TARGET=""
for candidate in "gui/main_window.py" "src/gui/main_window.py"; do
    if [ -f "$candidate" ]; then
        TARGET="$candidate"
        break
    fi
done

if [ -z "$TARGET" ]; then
    TARGET=$(find . -type f -name "main_window.py" -path "*/gui/*" ! -path "*/__pycache__/*" 2>/dev/null | head -n1 || true)
fi

if [ -z "$TARGET" ]; then
    echo "ERREUR : impossible de trouver gui/main_window.py."
    echo "Lancez ce script depuis la racine de votre projet VINA Studio,"
    echo "ou indiquez le chemin en argument : bash apply_liquid_glass.sh chemin/vers/main_window.py"
    if [ "${1:-}" != "" ]; then
        TARGET="$1"
    else
        exit 1
    fi
fi

echo "Fichier cible : $TARGET"

STAMP=$(date +%Y%m%d_%H%M%S)
BACKUP="${TARGET}.bak_${STAMP}"
cp "$TARGET" "$BACKUP"
echo "Sauvegarde créée : $BACKUP"

PATCH_FILE=$(mktemp)
trap 'rm -f "$PATCH_FILE"' EXIT

cat > "$PATCH_FILE" << 'PATCH_EOF'
--- main_window.py (original)
+++ main_window.py (glace)
@@ -168,19 +168,25 @@
         card.setStyleSheet(
             f"""
             QFrame#ChoiceCard {{
-                background: {COLORS["surface"]};
-                border: 1px solid {COLORS["border"]};
-                border-radius: 6px;
+                background: {COLORS["glass_sheen"]};
+                border-width: 1px;
+                border-style: solid;
+                border-top-color: {COLORS["bevel_light"]};
+                border-left-color: {COLORS["bevel_light"]};
+                border-right-color: {COLORS["bevel_dark"]};
+                border-bottom-color: {COLORS["bevel_dark"]};
+                border-radius: 16px;
             }}
             QFrame#ChoiceCard:hover {{
-                background: {COLORS["accent_light"]};
-                border: 1px solid {COLORS["accent"]};
+                background: {COLORS["accent_glass"]};
+                border-color: {COLORS["accent"]};
             }}
             """
         )
+        apply_glass_elevation(card, blur=22, y_offset=5, alpha=35)
 
         card_layout = QVBoxLayout(card)
-        card_layout.setContentsMargins(14, 11, 14, 11)
+        card_layout.setContentsMargins(16, 13, 16, 13)
         card_layout.setSpacing(3)
 
         title_label = QLabel(card_title)
@@ -306,15 +312,21 @@
         frame.setStyleSheet(
             f"""
             QFrame#SpeciesFrame {{
-                background: {COLORS["panel"]};
-                border: 1px solid {COLORS["border"]};
-                border-radius: 8px;
+                background: {COLORS["glass"]};
+                border-width: 1px;
+                border-style: solid;
+                border-top-color: {COLORS["bevel_light"]};
+                border-left-color: {COLORS["bevel_light"]};
+                border-right-color: {COLORS["bevel_dark"]};
+                border-bottom-color: {COLORS["bevel_dark"]};
+                border-radius: 18px;
             }}
             """
         )
+        apply_glass_elevation(frame, blur=28, y_offset=6, alpha=30)
 
         frame_layout = QVBoxLayout(frame)
-        frame_layout.setContentsMargins(14, 12, 14, 12)
+        frame_layout.setContentsMargins(16, 14, 16, 14)
         frame_layout.setSpacing(8)
 
         header = QLabel(species_label)
@@ -350,25 +362,32 @@
 
         border_color = COLORS["accent"] if is_current else COLORS["border"]
         bg_color = (
-            COLORS["accent_light"] if is_current else COLORS["surface"]
+            COLORS["accent_glass"] if is_current else COLORS["glass"]
         )
+        border_width = "1.5px" if is_current else "1px"
 
         card.setStyleSheet(
             f"""
             QFrame#ReceptorEntryCard {{
                 background: {bg_color};
-                border: 1px solid {border_color};
-                border-radius: 6px;
+                border-width: {border_width};
+                border-style: solid;
+                border-top-color: {COLORS["bevel_light"]};
+                border-left-color: {COLORS["bevel_light"]};
+                border-right-color: {border_color if is_current else COLORS["bevel_dark"]};
+                border-bottom-color: {border_color if is_current else COLORS["bevel_dark"]};
+                border-radius: 14px;
             }}
             QFrame#ReceptorEntryCard:hover {{
-                background: {COLORS["accent_light"]};
-                border: 1px solid {COLORS["accent"]};
+                background: {COLORS["accent_glass_hover"]};
+                border-color: {COLORS["accent"]};
             }}
             """
         )
+        apply_glass_elevation(card, blur=18, y_offset=4, alpha=28)
 
         layout = QHBoxLayout(card)
-        layout.setContentsMargins(12, 8, 12, 8)
+        layout.setContentsMargins(14, 10, 14, 10)
         layout.setSpacing(10)
 
         kind_tag = QLabel(kind_label)
@@ -385,9 +404,10 @@
         text_col.setSpacing(1)
 
         title_label = QLabel(("✓ " if is_current else "") + title)
+        title_color = COLORS["accent_ink"] if is_current else COLORS["text"]
         title_label.setStyleSheet(
             f"font-size: 13px; font-weight: 650; "
-            f"color: {COLORS['text']}; "
+            f"color: {title_color}; "
             "border: none; background: transparent;"
         )
         title_label.setWordWrap(True)
@@ -481,6 +501,7 @@
     QScrollArea,
     QListWidget,
     QListWidgetItem,
+    QGraphicsDropShadowEffect,
 )
 
 
@@ -489,31 +510,81 @@
 # ============================================================================
 
 COLORS = {
-    "window": "#eef1f4",
-    "surface": "#f7f8fa",
-    "surface_alt": "#e7ebef",
-    "panel": "#ffffff",
-    "border": "#cfd5dc",
-    "border_dark": "#b9c1ca",
-
-    "text": "#26323d",
-    "text_secondary": "#65717d",
-    "text_muted": "#89939d",
-
-    "accent": "#246b8f",
-    "accent_dark": "#1d5875",
-    "accent_light": "#dcecf4",
-
-    "success": "#3d7b61",
-    "success_light": "#e1efe8",
+    # Fond principal de la fenêtre : dégradé glacé (bleu-cyan très pâle),
+    # la "lumière froide" derrière laquelle les panneaux de glace flottent.
+    "window": "#e7f1f8",
+    "window_gradient": (
+        "qlineargradient(x1:0, y1:0, x2:1, y2:1, "
+        "stop:0 #dcedf8, stop:0.5 #e9f3fa, stop:1 #e2eef6)"
+    ),
+
+    # Surfaces "glace" : très translucides, utilisées uniquement sur des
+    # widgets enfants de la fenêtre principale (jamais sur une fenêtre
+    # top-level) pour un rendu givré sûr, sans artefacts de rendu.
+    # Alpha volontairement bas : on voit le dégradé au travers.
+    "glass": "rgba(255, 255, 255, 70)",
+    "glass_soft": "rgba(255, 255, 255, 40)",
+    "glass_strong": "rgba(255, 255, 255, 110)",
+    "glass_sheen": (
+        "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
+        "stop:0 rgba(255, 255, 255, 190), "
+        "stop:1 rgba(255, 255, 255, 70))"
+    ),
+    # Liseré "bord de glace" : plus clair en haut/gauche (la lumière
+    # accroche l'arête du bloc), plus froid/sombre en bas/droite (la
+    # face qui est dans l'ombre) — c'est ce qui vend l'épaisseur du
+    # verre plutôt qu'un simple rectangle à bord uniforme.
+    "bevel_light": "rgba(255, 255, 255, 235)",
+    "bevel_dark": "rgba(150, 195, 225, 130)",
+    "glass_edge": "rgba(255, 255, 255, 190)",
+
+    # Surfaces opaques : réservées aux fenêtres top-level (menus,
+    # listes déroulantes, dialogues) où une vraie transparence QSS
+    # provoquerait des artefacts de rendu.
+    "surface": "#eef6fb",
+    "surface_alt": "#e2eef7",
+    "panel": "#fbfdff",
+
+    "border": "rgba(130, 160, 190, 70)",
+    "border_dark": "rgba(110, 145, 178, 120)",
+
+    "text": "#12233a",
+    "text_secondary": "#4d6478",
+    "text_muted": "#7c92a3",
+
+    # Le bleu "plein" ne sert plus qu'à teinter (texte, contours,
+    # focus) — plus aucune surface cliquable n'est remplie de bleu
+    # opaque : tout est de la glace teintée, translucide.
+    "accent": "#1f8fe0",
+    "accent_dark": "#0a3d66",
+    "accent_ink": "#0a3d66",
+    "accent_light": "rgba(31, 143, 224, 45)",
+    "accent_glass": (
+        "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
+        "stop:0 rgba(170, 220, 255, 95), "
+        "stop:1 rgba(120, 195, 250, 120))"
+    ),
+    "accent_glass_hover": (
+        "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
+        "stop:0 rgba(190, 230, 255, 130), "
+        "stop:1 rgba(140, 205, 255, 160))"
+    ),
+    "accent_glass_pressed": (
+        "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
+        "stop:0 rgba(140, 205, 255, 150), "
+        "stop:1 rgba(90, 175, 245, 190))"
+    ),
+
+    "success": "#1f9e73",
+    "success_light": "rgba(31, 158, 115, 45)",
 
-    "warning": "#a97932",
-    "warning_light": "#f4ead9",
+    "warning": "#e08a12",
+    "warning_light": "rgba(224, 138, 18, 45)",
 
-    "danger": "#a94b4b",
-    "danger_light": "#f4dfdf",
+    "danger": "#ff453a",
+    "danger_light": "rgba(255, 69, 58, 40)",
 
-    "viewer": "#202830",
+    "viewer": "#12161f",
 }
 
 
@@ -523,7 +594,7 @@
 
 APP_STYLE = f"""
 QMainWindow {{
-    background: {COLORS["window"]};
+    background: {COLORS["window_gradient"]};
 }}
 
 QWidget {{
@@ -532,14 +603,24 @@
     color: {COLORS["text"]};
 }}
 
+QToolTip {{
+    background: {COLORS["panel"]};
+    color: {COLORS["text"]};
+    border: 1px solid {COLORS["border"]};
+    border-radius: 8px;
+    padding: 6px 10px;
+}}
+
 QMenuBar {{
     background: {COLORS["panel"]};
     border-bottom: 1px solid {COLORS["border"]};
-    padding: 2px 8px;
+    padding: 3px 8px;
 }}
 
 QMenuBar::item {{
-    padding: 7px 11px;
+    padding: 7px 12px;
+    margin: 2px;
+    border-radius: 8px;
     background: transparent;
 }}
 
@@ -551,11 +632,14 @@
 QMenu {{
     background: {COLORS["panel"]};
     border: 1px solid {COLORS["border"]};
-    padding: 5px;
+    border-radius: 14px;
+    padding: 8px;
 }}
 
 QMenu::item {{
-    padding: 7px 28px 7px 12px;
+    padding: 8px 28px 8px 14px;
+    border-radius: 9px;
+    margin: 1px 2px;
 }}
 
 QMenu::item:selected {{
@@ -563,24 +647,30 @@
     color: {COLORS["accent_dark"]};
 }}
 
+QMenu::separator {{
+    height: 1px;
+    background: {COLORS["border"]};
+    margin: 6px 8px;
+}}
+
 QToolBar {{
-    background: {COLORS["surface"]};
+    background: {COLORS["glass"]};
     border: none;
     border-bottom: 1px solid {COLORS["border"]};
-    spacing: 4px;
-    padding: 5px 8px;
+    spacing: 6px;
+    padding: 6px 10px;
 }}
 
 QToolButton {{
     border: 1px solid {COLORS["border"]};
-    background: {COLORS["panel"]};
-    padding: 6px 10px;
-    border-radius: 4px;
+    background: {COLORS["glass_strong"]};
+    padding: 7px 12px;
+    border-radius: 12px;
 }}
 
 QToolButton:hover {{
-    background: {COLORS["surface_alt"]};
-    border-color: {COLORS["border"]};
+    background: {COLORS["glass_edge"]};
+    border-color: {COLORS["accent"]};
 }}
 
 QToolButton:pressed {{
@@ -588,30 +678,34 @@
 }}
 
 QToolButton#TopTab {{
-    border: 1px solid {COLORS["border"]};
-    border-bottom: 2px solid transparent;
-    border-radius: 4px 4px 0 0;
-    margin-right: 3px;
-    padding: 8px 16px;
+    border: 1px solid transparent;
+    border-radius: 18px;
+    margin-right: 4px;
+    padding: 9px 20px;
     font-weight: 600;
     color: {COLORS["text_secondary"]};
-    background: {COLORS["surface"]};
+    background: transparent;
 }}
 
 QToolButton#TopTab:hover {{
-    background: {COLORS["surface_alt"]};
+    background: {COLORS["glass_soft"]};
     color: {COLORS["text"]};
 }}
 
 QToolButton#TopTab:checked {{
-    background: {COLORS["accent_light"]};
-    color: {COLORS["accent_dark"]};
-    border-color: {COLORS["accent"]};
-    border-bottom: 2px solid {COLORS["accent"]};
+    background: {COLORS["accent_glass"]};
+    color: {COLORS["accent_ink"]};
+    border-width: 1px;
+    border-style: solid;
+    border-top-color: {COLORS["bevel_light"]};
+    border-left-color: {COLORS["bevel_light"]};
+    border-right-color: {COLORS["bevel_dark"]};
+    border-bottom-color: {COLORS["bevel_dark"]};
+    font-weight: 650;
 }}
 
 QFrame#TopHeader {{
-    background: {COLORS["panel"]};
+    background: {COLORS["glass_strong"]};
     border-bottom: 1px solid {COLORS["border"]};
 }}
 
@@ -644,90 +738,105 @@
 }}
 
 QFrame#Navigation {{
-    background: {COLORS["surface"]};
+    background: {COLORS["glass_soft"]};
     border-right: 1px solid {COLORS["border"]};
 }}
 
 QFrame#NavigationHeader {{
-    background: {COLORS["surface"]};
+    background: transparent;
     border-bottom: 1px solid {COLORS["border"]};
 }}
 
 QToolButton#PrimaryNavigation {{
     text-align: left;
-    border: none;
-    border-left: 3px solid transparent;
-    border-radius: 0;
-    padding: 12px 14px;
+    border: 1px solid transparent;
+    border-radius: 12px;
+    margin: 2px 8px;
+    padding: 11px 13px;
     color: {COLORS["text_secondary"]};
     background: transparent;
 }}
 
 QToolButton#PrimaryNavigation:hover {{
-    background: {COLORS["surface_alt"]};
+    background: {COLORS["glass_strong"]};
     color: {COLORS["text"]};
 }}
 
 QToolButton#PrimaryNavigation:checked {{
-    background: {COLORS["accent_light"]};
-    color: {COLORS["accent_dark"]};
-    border-left: 3px solid {COLORS["accent"]};
+    background: {COLORS["accent_glass"]};
+    color: {COLORS["accent_ink"]};
+    border-width: 1px;
+    border-style: solid;
+    border-top-color: {COLORS["bevel_light"]};
+    border-left-color: {COLORS["bevel_light"]};
+    border-right-color: {COLORS["bevel_dark"]};
+    border-bottom-color: {COLORS["bevel_dark"]};
     font-weight: 650;
 }}
 
 QFrame#SecondaryNavigation {{
-    background: {COLORS["panel"]};
+    background: {COLORS["glass"]};
     border-right: 1px solid {COLORS["border"]};
 }}
 
 QToolButton#SecondaryTab {{
     text-align: left;
-    border: none;
-    border-left: 2px solid transparent;
-    border-radius: 0;
-    padding: 11px 13px;
+    border: 1px solid transparent;
+    border-radius: 10px;
+    margin: 1px 6px;
+    padding: 10px 12px;
     color: {COLORS["text_secondary"]};
     background: transparent;
 }}
 
 QToolButton#SecondaryTab:hover {{
-    background: {COLORS["surface"]};
+    background: {COLORS["glass_strong"]};
     color: {COLORS["text"]};
 }}
 
 QToolButton#SecondaryTab:checked {{
     color: {COLORS["accent_dark"]};
     background: {COLORS["accent_light"]};
-    border-left: 2px solid {COLORS["accent"]};
+    border: 1px solid rgba(10, 132, 255, 90);
     font-weight: 620;
 }}
 
 QFrame#Workspace {{
-    background: {COLORS["window"]};
+    background: transparent;
 }}
 
 QFrame#ContentPanel {{
-    background: {COLORS["panel"]};
-    border: 1px solid {COLORS["border"]};
-    border-radius: 4px;
+    background: {COLORS["glass_sheen"]};
+    border-width: 1px;
+    border-style: solid;
+    border-top-color: {COLORS["bevel_light"]};
+    border-left-color: {COLORS["bevel_light"]};
+    border-right-color: {COLORS["bevel_dark"]};
+    border-bottom-color: {COLORS["bevel_dark"]};
+    border-radius: 20px;
 }}
 
 QFrame#ToolbarPanel {{
-    background: {COLORS["surface"]};
-    border: 1px solid {COLORS["border"]};
-    border-radius: 4px;
+    background: {COLORS["glass"]};
+    border-width: 1px;
+    border-style: solid;
+    border-top-color: {COLORS["bevel_light"]};
+    border-left-color: {COLORS["bevel_light"]};
+    border-right-color: {COLORS["bevel_dark"]};
+    border-bottom-color: {COLORS["bevel_dark"]};
+    border-radius: 16px;
 }}
 
 QPushButton {{
-    background: {COLORS["panel"]};
+    background: {COLORS["glass_strong"]};
     border: 1px solid {COLORS["border_dark"]};
-    border-radius: 3px;
-    padding: 7px 14px;
+    border-radius: 14px;
+    padding: 9px 18px;
     min-height: 18px;
 }}
 
 QPushButton:hover {{
-    background: {COLORS["surface"]};
+    background: {COLORS["glass_edge"]};
     border-color: {COLORS["accent"]};
 }}
 
@@ -735,71 +844,107 @@
     background: {COLORS["accent_light"]};
 }}
 
+QPushButton:disabled {{
+    background: {COLORS["glass_soft"]};
+    color: {COLORS["text_muted"]};
+    border-color: {COLORS["border"]};
+}}
+
 QPushButton#PrimaryButton {{
-    background: {COLORS["accent"]};
-    color: white;
-    border: 1px solid {COLORS["accent_dark"]};
-    font-weight: 620;
+    background: {COLORS["accent_glass"]};
+    color: {COLORS["accent_ink"]};
+    border-width: 1px;
+    border-style: solid;
+    border-top-color: {COLORS["bevel_light"]};
+    border-left-color: {COLORS["bevel_light"]};
+    border-right-color: {COLORS["bevel_dark"]};
+    border-bottom-color: {COLORS["bevel_dark"]};
+    font-weight: 640;
+    padding: 9px 22px;
 }}
 
 QPushButton#PrimaryButton:hover {{
-    background: {COLORS["accent_dark"]};
+    background: {COLORS["accent_glass_hover"]};
+}}
+
+QPushButton#PrimaryButton:pressed {{
+    background: {COLORS["accent_glass_pressed"]};
 }}
 
 QPushButton#DangerButton {{
     color: {COLORS["danger"]};
 }}
 
+QPushButton#DangerButton:hover {{
+    border-color: {COLORS["danger"]};
+    background: {COLORS["danger_light"]};
+}}
+
 QLineEdit,
 QComboBox {{
-    background: {COLORS["panel"]};
+    background: {COLORS["glass_strong"]};
     border: 1px solid {COLORS["border_dark"]};
-    border-radius: 3px;
-    padding: 7px 8px;
+    border-radius: 12px;
+    padding: 8px 12px;
     min-height: 18px;
+    selection-background-color: {COLORS["accent_light"]};
+}}
+
+QLineEdit:hover,
+QComboBox:hover {{
+    background: {COLORS["glass_edge"]};
 }}
 
 QLineEdit:focus,
 QComboBox:focus {{
-    border: 1px solid {COLORS["accent"]};
+    border: 1.5px solid {COLORS["accent"]};
+    background: {COLORS["panel"]};
 }}
 
 QSpinBox,
 QDoubleSpinBox {{
-    background: {COLORS["panel"]};
+    background: {COLORS["glass_strong"]};
     color: {COLORS["text"]};
     border: 1px solid {COLORS["border_dark"]};
-    border-radius: 3px;
-    padding: 7px 8px;
+    border-radius: 12px;
+    padding: 8px 12px;
     min-height: 18px;
 }}
 
 QSpinBox:focus,
 QDoubleSpinBox:focus {{
-    border: 1px solid {COLORS["accent"]};
+    border: 1.5px solid {COLORS["accent"]};
+    background: {COLORS["panel"]};
 }}
 
 QSpinBox::up-button,
 QSpinBox::down-button,
 QDoubleSpinBox::up-button,
 QDoubleSpinBox::down-button {{
-    background: {COLORS["surface_alt"]};
-    border-left: 1px solid {COLORS["border_dark"]};
-    width: 16px;
+    background: transparent;
+    border-left: 1px solid {COLORS["border"]};
+    width: 18px;
+}}
+
+QSpinBox::up-button:hover,
+QSpinBox::down-button:hover,
+QDoubleSpinBox::up-button:hover,
+QDoubleSpinBox::down-button:hover {{
+    background: {COLORS["accent_light"]};
 }}
 
 QCheckBox {{
     color: {COLORS["text"]};
-    spacing: 8px;
+    spacing: 9px;
     padding: 3px 0px;
 }}
 
 QCheckBox::indicator {{
-    width: 16px;
-    height: 16px;
+    width: 17px;
+    height: 17px;
     border: 1px solid {COLORS["border_dark"]};
-    border-radius: 3px;
-    background: {COLORS["panel"]};
+    border-radius: 6px;
+    background: {COLORS["glass_strong"]};
 }}
 
 QCheckBox::indicator:hover {{
@@ -807,30 +952,32 @@
 }}
 
 QCheckBox::indicator:checked {{
-    background: {COLORS["accent"]};
-    border: 1px solid {COLORS["accent_dark"]};
+    background: {COLORS["accent_glass_pressed"]};
+    border: 1px solid {COLORS["accent"]};
 }}
 
 QCheckBox::indicator:disabled {{
-    background: {COLORS["surface_alt"]};
+    background: {COLORS["glass_soft"]};
     border: 1px solid {COLORS["border"]};
 }}
 
 QComboBox::drop-down {{
     border: none;
-    width: 22px;
+    width: 26px;
 }}
 
 QComboBox QAbstractItemView {{
     background: {COLORS["panel"]};
     color: {COLORS["text"]};
     border: 1px solid {COLORS["border_dark"]};
+    border-radius: 12px;
     outline: none;
-    padding: 2px;
+    padding: 4px;
 }}
 
 QComboBox QAbstractItemView::item {{
-    padding: 6px 8px;
+    padding: 7px 10px;
+    border-radius: 8px;
     color: {COLORS["text"]};
     background: {COLORS["panel"]};
 }}
@@ -844,14 +991,15 @@
 QTableWidget {{
     background: {COLORS["panel"]};
     border: 1px solid {COLORS["border"]};
+    border-radius: 14px;
     gridline-color: {COLORS["border"]};
     selection-background-color: {COLORS["accent_light"]};
     selection-color: {COLORS["text"]};
-    alternate-background-color: #f8fafb;
+    alternate-background-color: #f6f8fd;
 }}
 
 QTableWidget::item {{
-    padding: 6px;
+    padding: 7px;
 }}
 
 QHeaderView::section {{
@@ -860,31 +1008,40 @@
     border: none;
     border-right: 1px solid {COLORS["border"]};
     border-bottom: 1px solid {COLORS["border"]};
-    padding: 7px;
+    padding: 8px;
     font-weight: 620;
 }}
 
+QHeaderView::section:first {{
+    border-top-left-radius: 14px;
+}}
+
+QHeaderView::section:last {{
+    border-top-right-radius: 14px;
+}}
+
 QProgressBar {{
-    background: {COLORS["surface_alt"]};
+    background: {COLORS["glass_soft"]};
     border: 1px solid {COLORS["border"]};
-    border-radius: 3px;
-    height: 9px;
+    border-radius: 6px;
+    height: 12px;
     text-align: center;
 }}
 
 QProgressBar::chunk {{
-    background: {COLORS["accent"]};
-    border-radius: 2px;
+    background: {COLORS["accent_glass_pressed"]};
+    border-radius: 5px;
 }}
 
 QStatusBar {{
-    background: {COLORS["surface"]};
+    background: {COLORS["glass"]};
     border-top: 1px solid {COLORS["border"]};
     color: {COLORS["text_secondary"]};
 }}
 
 QSplitter::handle {{
     background: {COLORS["border"]};
+    border-radius: 2px;
 }}
 
 QSplitter::handle:hover {{
@@ -894,34 +1051,35 @@
 QFrame#Viewer {{
     background: {COLORS["viewer"]};
     border: 1px solid #151b20;
+    border-radius: 18px;
 }}
 
 QScrollArea {{
-    background: {COLORS["window"]};
+    background: transparent;
     border: none;
 }}
 
 QScrollArea > QWidget > QWidget {{
-    background: {COLORS["window"]};
+    background: transparent;
 }}
 
 QScrollArea#DockingScrollArea,
 QScrollArea#DockingScrollArea > QWidget {{
-    background: {COLORS["window"]};
+    background: transparent;
 }}
 
 QScrollBar:vertical {{
-    background: {COLORS["surface"]};
-    width: 13px;
-    margin: 0px;
+    background: transparent;
+    width: 11px;
+    margin: 2px;
     border: none;
 }}
 
 QScrollBar::handle:vertical {{
     background: {COLORS["border_dark"]};
-    min-height: 24px;
+    min-height: 28px;
     border-radius: 5px;
-    margin: 2px;
+    margin: 1px;
 }}
 
 QScrollBar::handle:vertical:hover {{
@@ -940,17 +1098,17 @@
 }}
 
 QScrollBar:horizontal {{
-    background: {COLORS["surface"]};
-    height: 13px;
-    margin: 0px;
+    background: transparent;
+    height: 11px;
+    margin: 2px;
     border: none;
 }}
 
 QScrollBar::handle:horizontal {{
     background: {COLORS["border_dark"]};
-    min-width: 24px;
+    min-width: 28px;
     border-radius: 5px;
-    margin: 2px;
+    margin: 1px;
 }}
 
 QScrollBar::handle:horizontal:hover {{
@@ -969,7 +1127,7 @@
 }}
 
 QDialog {{
-    background: {COLORS["panel"]};
+    background: {COLORS["window_gradient"]};
 }}
 
 QMessageBox {{
@@ -987,12 +1145,46 @@
 }}
 
 QMessageBox QPushButton {{
-    min-width: 72px;
+    min-width: 76px;
 }}
 """
 
 
 # ============================================================================
+# EFFET "VERRE LIQUIDE" — ombre portée douce simulant l'élévation d'une
+# carte de verre au-dessus du dégradé de fond. QSS seul ne sait pas
+# dessiner d'ombre portée : on utilise QGraphicsDropShadowEffect, qui ne
+# coûte rien en fiabilité (aucun rendu OpenGL requis) et fonctionne sur
+# n'importe quelle plateforme supportée par Qt.
+# ============================================================================
+
+def apply_glass_elevation(widget, blur=36, y_offset=10, alpha=55):
+    """
+    Applique une ombre portée douce à `widget` pour lui donner l'aspect
+    d'une carte de verre flottant au-dessus du fond. Sans effet sur la
+    couleur/texte du widget : uniquement l'ombre derrière lui.
+    """
+    effect = QGraphicsDropShadowEffect(widget)
+    effect.setBlurRadius(blur)
+    effect.setOffset(0, y_offset)
+    effect.setColor(QColor(20, 30, 60, alpha))
+    widget.setGraphicsEffect(effect)
+    return effect
+
+
+def apply_glass_elevation_to_children(root, object_names, blur=32, y_offset=8, alpha=50):
+    """
+    Parcourt les enfants de `root` et applique apply_glass_elevation() à
+    tout QFrame dont l'objectName figure dans `object_names`. Pratique
+    pour habiller d'un coup tous les panneaux existants (ContentPanel,
+    ToolbarPanel, ...) sans toucher à chacun de leurs points de création.
+    """
+    for frame in root.findChildren(QFrame):
+        if frame.objectName() in object_names:
+            apply_glass_elevation(frame, blur=blur, y_offset=y_offset, alpha=alpha)
+
+
+# ============================================================================
 # HELPERS
 # ============================================================================
 
@@ -7263,6 +7455,10 @@
 
         self.build_interface()
 
+        apply_glass_elevation_to_children(
+            self, {"ContentPanel", "ToolbarPanel"}
+        )
+
         self.retranslate_ui()
 
     def retranslate_ui(self, _code=None):
PATCH_EOF

echo "== Application du patch =="
if patch --fuzz=3 -b -z ".prepatch" "$TARGET" < "$PATCH_FILE"; then
    echo "Patch appliqué avec succès."
else
    echo "ERREUR : le patch ne s'applique pas proprement (fichier modifié entre-temps ?)."
    echo "Le fichier original est intact dans : $BACKUP"
    exit 1
fi

echo "== Vérification de la syntaxe Python =="
if python3 -m py_compile "$TARGET"; then
    echo "Syntaxe valide."
else
    echo "ERREUR de syntaxe après patch — restauration de la sauvegarde."
    cp "$BACKUP" "$TARGET"
    exit 1
fi

echo ""
echo "== Terminé =="
echo "Style 'glace' appliqué à     : $TARGET"
echo "Sauvegarde de l'ancienne version : $BACKUP"
echo ""
echo "Relancez simplement l'application pour voir le résultat."
