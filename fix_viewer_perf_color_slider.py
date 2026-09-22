# -*- coding: utf-8 -*-
"""
fix_viewer_perf_color_slider.py

Corrige trois problemes signales sur la page docking de VinaStudio :

  1. Rotation 3D devenue lente : viewer_panel (qui contient le
     QWebEngineView) a l'objectName "ContentPanel", et
     apply_glass_elevation_to_children() lui applique donc un
     QGraphicsDropShadowEffect (blur=32). Cet effet force Qt a
     recomposer le widget hors-ecran a chaque repaint -- et le
     WebEngineView repeint en continu pendant une rotation WebGL,
     d'ou le ralentissement. On retire cet effet specifiquement sur
     viewer_panel, sans toucher aux autres panneaux "verre liquide".

  2. Couleur de la grid box : les aretes etaient en bleu fonce
     (0x1f6fa5) malgre un commentaire qui parlait d'"orange vif" --
     peu lisible sur fond blanc et sur une proteine "spectrum"
     (qui contient deja du bleu). Remplacee par du magenta vif
     (0xff00ff), qui ne se confond ni avec le fond blanc ni avec les
     teintes de l'arc-en-ciel "spectrum".

  3. Sliders de grid box beaucoup trop sensibles au glissement : la
     sensibilite reelle d'un QSlider au glissement souris est
     (max-min)/largeur_en_pixels -- independante du facteur "scale"
     utilise ici. Avec un centre allant de -1000 a 1000 sur ~140px de
     large, un mouvement de souris minime deplace la boite de
     plusieurs angstroms. On introduit SmoothSlider, un QSlider dont
     la sensibilite est fixee independamment de sa largeur reelle
     (parcours virtuel de 600px pour traverser tout le range), et on
     l'utilise a la place de QSlider pour les 3 jeux de sliders de
     grid box (MexB, MexR, generique).

Usage :
    python3 fix_viewer_perf_color_slider.py

Sauvegarde automatique horodatee avant toute modification. Verification
syntaxique (py_compile) apres patch. Si un bloc attendu ne correspond
pas exactement au fichier (version differente), le script s'arrete
sans rien modifier et affiche la ligne concernee.
"""

import datetime
import py_compile
import sys
from pathlib import Path

BASE = Path.home() / "MexAB_MexR_Analyzer_BETA" / "src" / "gui"
MAIN_WINDOW = BASE / "main_window.py"
VIEWER_TEMPLATE = BASE / "viewer_template.py"

STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def backup(path: Path) -> Path:
    dst = path.with_name(path.name + f".bak_{STAMP}")
    dst.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  sauvegarde -> {dst.name}")
    return dst


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        print(f"\n[ECHEC] bloc '{label}' trouve {count} fois (attendu 1).")
        print("Extrait attendu :\n---\n" + old[:300] + "\n---")
        sys.exit(1)
    return text.replace(old, new, 1)


def patch_viewer_template():
    print("\n== viewer_template.py ==")
    if not VIEWER_TEMPLATE.exists():
        print(f"[ECHEC] introuvable : {VIEWER_TEMPLATE}")
        sys.exit(1)
    backup(VIEWER_TEMPLATE)
    text = VIEWER_TEMPLATE.read_text(encoding="utf-8")

    # On cible uniquement la couleur des aretes de la grid box (le
    # highlight orange au survol d'un residu, lui, reste orange).
    old_edge_color = '          color: "0x1f6fa5",'
    new_edge_color = '          color: "0xff00ff",'
    text = replace_once(text, old_edge_color, new_edge_color, "couleur aretes grid box")

    old_comment = (
        "      // qui dessine aussi les diagonales de chaque face et rend la\n"
        "      // boîte illisible). Chaque arête est un cylindre épais, orange\n"
        "      // vif, toujours à 100% d'opacité : un cadre rectangulaire net,"
    )
    new_comment = (
        "      // qui dessine aussi les diagonales de chaque face et rend la\n"
        "      // boîte illisible). Chaque arête est un cylindre épais, magenta\n"
        "      // vif, toujours à 100% d'opacité : un cadre rectangulaire net,"
    )
    text = replace_once(text, old_comment, new_comment, "commentaire couleur aretes")
    print("  commentaire mis a jour (orange -> magenta)")

    VIEWER_TEMPLATE.write_text(text, encoding="utf-8")
    print("  couleur des aretes de la grid box : bleu fonce -> magenta vif")


def patch_main_window():
    print("\n== main_window.py ==")
    if not MAIN_WINDOW.exists():
        print(f"[ECHEC] introuvable : {MAIN_WINDOW}")
        sys.exit(1)
    backup(MAIN_WINDOW)
    text = MAIN_WINDOW.read_text(encoding="utf-8")

    # --- 1) garder une reference self.viewer_panel ---------------------
    old = (
        '        viewer_panel = QFrame()\n'
        '        viewer_panel.setObjectName("ContentPanel")\n'
    )
    new = (
        '        viewer_panel = QFrame()\n'
        '        viewer_panel.setObjectName("ContentPanel")\n'
        '        self.viewer_panel = viewer_panel\n'
    )
    text = replace_once(text, old, new, "reference self.viewer_panel")

    # --- 2) retirer l'effet de flou sur ce panneau precis ---------------
    old = (
        '        apply_glass_elevation_to_children(\n'
        '            self, {"ContentPanel", "ToolbarPanel"}\n'
        '        )\n'
    )
    new = (
        '        apply_glass_elevation_to_children(\n'
        '            self, {"ContentPanel", "ToolbarPanel"}\n'
        '        )\n'
        '        # Le panneau du visualiseur 3D heberge un QWebEngineView qui\n'
        '        # repeint en continu pendant une rotation WebGL. Lui laisser\n'
        '        # l\'effet "verre liquide" (QGraphicsDropShadowEffect) forcait\n'
        '        # Qt a recomposer tout le panneau hors-ecran a chaque frame,\n'
        '        # d\'ou la rotation devenue tres lente -- corrige le 16/09.\n'
        '        if hasattr(self, "viewer_panel"):\n'
        '            self.viewer_panel.setGraphicsEffect(None)\n'
    )
    text = replace_once(text, old, new, "retrait effet de flou sur viewer_panel")

    # --- 3) classe SmoothSlider (sensibilite de glissement fixe) --------
    anchor = (
        '# ============================================================================\n'
        '# EFFET "VERRE LIQUIDE"'
    )
    idx = text.find(anchor)
    if idx == -1:
        print("[ECHEC] point d'insertion de SmoothSlider introuvable.")
        sys.exit(1)
    smooth_slider_code = (
        '# ============================================================================\n'
        '# SmoothSlider -- sensibilite de glissement fixe, independante de la\n'
        '# largeur reelle du widget. Un QSlider standard mappe sa position de\n'
        '# souris directement sur toute sa plage (min..max) : avec une plage\n'
        '# large (ex. centre de grid box -1000..1000) et un widget etroit\n'
        '# (~140px), un tout petit mouvement de souris deplace la valeur de\n'
        '# plusieurs unites -- glissement percu comme "beaucoup trop rapide"\n'
        '# (signale le 16/09 sur les sliders de grid box). SmoothSlider simule\n'
        '# a la place un parcours virtuel de PIXELS_FOR_FULL_RANGE pixels pour\n'
        '# traverser toute la plage, quelle que soit la largeur reelle.\n'
        '# ============================================================================\n'
        '\n'
        'class SmoothSlider(QSlider):\n'
        '    PIXELS_FOR_FULL_RANGE = 600\n'
        '\n'
        '    def __init__(self, *args, **kwargs):\n'
        '        super().__init__(*args, **kwargs)\n'
        '        self._drag_start_x = None\n'
        '        self._drag_start_value = None\n'
        '\n'
        '    def _event_x(self, event):\n'
        '        pos = event.position() if hasattr(event, "position") else event.pos()\n'
        '        return pos.x()\n'
        '\n'
        '    def mousePressEvent(self, event):\n'
        '        self._drag_start_x = self._event_x(event)\n'
        '        self._drag_start_value = self.value()\n'
        '        event.accept()\n'
        '\n'
        '    def mouseMoveEvent(self, event):\n'
        '        if self._drag_start_x is None:\n'
        '            return\n'
        '        dx = self._event_x(event) - self._drag_start_x\n'
        '        span = self.maximum() - self.minimum()\n'
        '        delta = dx / self.PIXELS_FOR_FULL_RANGE * span\n'
        '        new_value = int(round(self._drag_start_value + delta))\n'
        '        new_value = max(self.minimum(), min(self.maximum(), new_value))\n'
        '        self.setValue(new_value)\n'
        '        event.accept()\n'
        '\n'
        '    def mouseReleaseEvent(self, event):\n'
        '        self._drag_start_x = None\n'
        '        self._drag_start_value = None\n'
        '        event.accept()\n'
        '\n'
        '\n'
    )
    text = text[:idx] + smooth_slider_code + text[idx:]
    print("  classe SmoothSlider inseree")

    # --- 4) utiliser SmoothSlider pour les 3 jeux de sliders grid box ---
    replacements = [
        (
            '            slider = QSlider(Qt.Horizontal)\n'
            '            slider.setMinimumWidth(110)\n'
            '            slider.setMaximumWidth(160)\n'
            '            slider.setMinimum(int(round(field.minimum() * scale)))\n'
            '            slider.setMaximum(int(round(field.maximum() * scale)))\n'
            '            slider.setValue(int(round(field.value() * scale)))\n'
            '\n'
            '            def _make_spinbox_to_slider(sl=slider, sc=scale):\n'
            '                def _sync(value):\n'
            '                    sl.blockSignals(True)\n'
            '                    sl.setValue(int(round(value * sc)))\n'
            '                    sl.blockSignals(False)\n'
            '                return _sync\n'
            '\n'
            '            def _make_slider_to_spinbox(spinbox=field, sc=scale):\n'
            '                def _sync(value):\n'
            '                    spinbox.blockSignals(True)\n'
            '                    spinbox.setValue(value / sc)\n'
            '                    spinbox.blockSignals(False)\n'
            '                    self._on_mexb_grid_changed()\n'
            '                return _sync\n',
            "slider MexB",
        ),
        (
            '            mexr_slider = QSlider(Qt.Horizontal)\n'
            '            mexr_slider.setMinimumWidth(110)\n'
            '            mexr_slider.setMaximumWidth(160)\n',
            "slider MexR",
        ),
        (
            '            slider = QSlider(Qt.Horizontal)\n'
            '            slider.setMinimumWidth(110)\n'
            '            slider.setMaximumWidth(160)\n'
            '            slider.setMinimum(int(round(field.minimum() * scale)))\n'
            '            slider.setMaximum(int(round(field.maximum() * scale)))\n'
            '            slider.setValue(int(round(field.value() * scale)))\n'
            '\n'
            '            def _make_spinbox_to_slider(sl=slider, sc=scale):\n'
            '                def _sync(value):\n'
            '                    sl.blockSignals(True)\n'
            '                    sl.setValue(int(round(value * sc)))\n'
            '                    sl.blockSignals(False)\n'
            '                return _sync\n'
            '\n'
            '            def _make_slider_to_spinbox(spinbox=field, sc=scale, tk=target_key):\n',
            "slider generique",
        ),
    ]
    for old_block, label in replacements:
        new_block = old_block.replace("QSlider(Qt.Horizontal)", "SmoothSlider(Qt.Horizontal)", 1)
        text = replace_once(text, old_block, new_block, label)

    MAIN_WINDOW.write_text(text, encoding="utf-8")
    print("  3 sliders de grid box migres vers SmoothSlider")


def check_syntax(path: Path):
    try:
        py_compile.compile(str(path), doraise=True)
        print(f"  OK syntaxe : {path.name}")
    except py_compile.PyCompileError as exc:
        print(f"[ECHEC] erreur de syntaxe apres patch dans {path.name} :\n{exc}")
        sys.exit(1)


def main():
    patch_viewer_template()
    patch_main_window()
    print("\n== verification syntaxique ==")
    check_syntax(MAIN_WINDOW)
    print("\nTermine. Relance VinaStudio pour tester.")


if __name__ == "__main__":
    main()
