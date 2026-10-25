# -*- coding: utf-8 -*-
"""Bouton unique « Exporter tout » : copie tout ce que produit la session
dans un dossier daté, rangé par catégories numérotées."""
from __future__ import annotations

import json
import re
import shutil
import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QBoxLayout, QFileDialog, QMessageBox, QPushButton,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUTTON_NAME = "export_everything_button"
SKIP_NAMES = {".ds_store", "thumbs.db"}
SKIP_DIRS = {"__pycache__", ".thumbs", ".git"}

DESCRIPTIONS = {
    "00_configuration": "récepteurs, grid box, profils de configuration",
    "01_docking": "résultats CSV, poses PDBQT, journaux Vina",
    "02_analyse": "scores fusionnés, statistiques, graphiques",
    "03_visualisation": "diagrammes 2D, complexes PLIP, résidus d'interaction",
    "04_validation": "re-docking de contrôle et validation",
    "05_references": "molécules de référence",
    "06_phytomolecules": "résultats phytomolécules",
    "07_ligands": "ligands préparés",
    "99_autres": "fichiers non classés (rien n'est perdu)",
}


def _find_module(suffix, *import_names):
    for name, mod in list(sys.modules.items()):
        if mod is not None and (name == suffix or name.endswith("." + suffix)):
            return mod
    import importlib
    for name in import_names:
        try:
            return importlib.import_module(name)
        except Exception:
            continue
    return None


def _target_of(p):
    for key, label in (("mexb", "MexB"), ("mexr", "MexR")):
        if key in p:
            return label
    return ""


def classify(rel):
    """rel = chemin relatif préfixé par le nom de la source. Retourne le chemin de destination."""
    p = rel.as_posix().lower()
    name = rel.name.lower()
    ext = rel.suffix.lower()
    tgt = _target_of(p)

    def put(*folders):
        return Path(*[f for f in folders if f]) / rel.name

    if name.endswith("_out.pdbqt"):
        return put("01_docking", "poses_pdbqt", tgt)
    if ext == ".csv" and ("docking_results" in name or "ranked" in name or "combined" in name):
        return put("01_docking", "resultats_csv", tgt)
    if ext == ".log":
        return put("01_docking", "journaux_vina", tgt)
    if "redocking" in p or "validation" in p:
        return put("04_validation", tgt)
    if "reference" in p:
        return put("05_references", tgt)
    if "phyto" in p:
        return put("06_phytomolecules")
    if ext == ".csv" and ("interaction" in p or "residu" in p):
        return put("03_visualisation", "residus_csv", tgt)
    if ext in (".csv", ".json", ".xlsx", ".png", ".pdf", ".svg", ".txt") and any(
            k in p for k in ("scores_fusionnes", "scientific", "statist", "analyse", "analysis")):
        return put("02_analyse")
    if ext in (".png", ".svg") and any(k in p for k in ("diagram", "2d", "interaction")):
        return put("03_visualisation", "diagrammes_2d", tgt)
    if ext == ".xml" or name.endswith("_complex.pdb") or "plip" in p:
        return put("03_visualisation", "plip_xml_complex", tgt)
    if "receptor" in p and ext in (".pdb", ".pdbqt"):
        return put("00_configuration", "recepteurs")
    if ext == ".json" and any(k in p for k in ("config", "grid", "profile", "session")):
        return put("00_configuration")
    if ext in (".sdf", ".mol2", ".mol", ".pdbqt") or "ligand" in p:
        return put("07_ligands")
    return Path("99_autres") / rel


def _iter_files(root):
    for f in root.rglob("*"):
        try:
            if not f.is_file():
                continue
            rel_parts = f.relative_to(root).parts
        except OSError:
            continue
        if f.name.lower() in SKIP_NAMES or any(part in SKIP_DIRS for part in rel_parts[:-1]):
            continue
        yield f


def _since():
    sr = _find_module("session_runtime")
    ts = getattr(sr, "SESSION_START_TS", None)
    try:
        return float(ts) - 5 if ts else time.time() - 12 * 3600
    except Exception:
        return time.time() - 12 * 3600


def _sources(mw, notes):
    out = []
    sm = getattr(mw, "_session_manager", None)
    try:
        if sm is not None and getattr(sm, "active", False):
            out.append(("session", Path(sm.require_session()), False))
    except Exception as exc:
        notes.append("Session : %s" % exc)
    for label in ("docking/results", "scientific_analysis", "redocking_runs"):
        d = PROJECT_ROOT / label
        if d.is_dir():
            out.append((label, d, True))
    return out


def _build_plan(sources, since):
    plan = []
    for label, root, use_filter in sources:
        for f in _iter_files(root):
            try:
                if use_filter and f.stat().st_mtime < since:
                    continue
            except OSError:
                continue
            plan.append((f, classify(Path(label) / f.relative_to(root))))
    return plan


def _copy(src, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        if dest.stat().st_size == src.stat().st_size:
            return False
        k = 2
        while True:
            cand = dest.with_name("%s_%d%s" % (dest.stem, k, dest.suffix))
            if not cand.exists():
                dest = cand
                break
            k += 1
    shutil.copy2(src, dest)
    return True


def _write_readme(root, notes):
    lines = ["VINA Studio — export du " + time.strftime("%d/%m/%Y à %H:%M"), "",
             "Contenu (nombre de fichiers par dossier) :", ""]
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        n = sum(1 for f in d.rglob("*") if f.is_file())
        lines.append("  %-20s %5d fichier(s)  %s" % (d.name + "/", n, DESCRIPTIONS.get(d.name, "")))
    if notes:
        lines += ["", "Avertissements :"] + ["  - " + n for n in notes]
    (root / "00_LISEZ_MOI.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_everything(mw):
    parent = QFileDialog.getExistingDirectory(mw, "Choisir le dossier où créer l'export")
    if not parent:
        return
    root = Path(parent) / ("VinaStudio_export_" + time.strftime("%Y%m%d_%H%M%S"))
    notes = []
    total = 0
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        root.mkdir(parents=True, exist_ok=True)

        viz_ok = False
        vp = getattr(mw, "visualization_page", None)
        hits = getattr(vp, "hit_results", None) if vp is not None else None
        if hits:
            try:
                viz = _find_module("visualization_bridge", "src.gui.visualization_bridge",
                                   "gui.visualization_bridge")
                if viz is None:
                    raise RuntimeError("module visualization_bridge introuvable")
                viz.export_visualization_results(
                    {"results": hits, "errors": getattr(vp, "batch_errors", [])},
                    root / "03_visualisation")
                viz_ok = True
            except Exception as exc:
                notes.append("Visualisation : %s" % exc)

        ap = getattr(mw, "analysis_page", None)
        stats = getattr(ap, "statistics_result", None) if ap is not None else None
        if stats:
            try:
                dest = root / "02_analyse"
                dest.mkdir(parents=True, exist_ok=True)
                with (dest / "analyse_statistique.json").open("w", encoding="utf-8") as handle:
                    json.dump(stats, handle, default=str, ensure_ascii=False, indent=2)
            except Exception as exc:
                notes.append("Statistiques : %s" % exc)

        for src, dest_rel in _build_plan(_sources(mw, notes), _since()):
            if viz_ok and dest_rel.parts and dest_rel.parts[0] == "03_visualisation":
                continue
            try:
                _copy(src, root / dest_rel)
            except Exception as exc:
                notes.append("%s : %s" % (src.name, exc))

        total = sum(1 for f in root.rglob("*") if f.is_file())
        if total:
            _write_readme(root, notes)
            total += 1
        else:
            shutil.rmtree(root, ignore_errors=True)
    finally:
        QApplication.restoreOverrideCursor()

    if not total:
        QMessageBox.information(mw, "Rien à exporter",
                                "Aucun résultat de la session en cours à exporter pour le moment.")
        return
    box = QMessageBox(mw)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle("Export terminé")
    box.setText("%d fichier(s) exporté(s) dans :\n%s" % (total, root))
    open_btn = box.addButton("Ouvrir le dossier", QMessageBox.ButtonRole.AcceptRole)
    box.addButton("Fermer", QMessageBox.ButtonRole.RejectRole)
    box.exec()
    if box.clickedButton() is open_btn:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(root)))


def _label():
    tr = _find_module("translations")
    try:
        if tr is not None and hasattr(tr, "t"):
            return tr.t("viz_btn_export_all")
    except Exception:
        pass
    return "Exporter tout"


def _locate(layout, widget):
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item is None:
            continue
        if item.widget() is widget:
            return layout, i
        sub = item.layout()
        if sub is not None:
            found = _locate(sub, widget)
            if found:
                return found
    return None


_OLD = re.compile(r"(tout exporter|exporter tout|export all|alles exportieren|全部导出|すべてエクスポート)", re.I)
_ANCHOR = re.compile(r"(charger une analyse|load analysis|analyse laden)", re.I)


def _install_button(mw):
    if mw.findChild(QPushButton, BUTTON_NAME) is not None:
        return
    btn = QPushButton(_label())
    btn.setObjectName(BUTTON_NAME)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setToolTip("Exporte tout dans un dossier daté, rangé par catégories")
    btn.clicked.connect(lambda _=False: export_everything(mw))
    mw._export_everything_button = btn

    for b in mw.findChildren(QPushButton):
        if b is not btn and _OLD.search(b.text() or ""):
            b.hide()
    for page, attr in (("docking_page", "_export_session_button"),
                       ("visualization_page", "export_all_button")):
        old = getattr(getattr(mw, page, None), attr, None)
        if old is not None and old is not btn:
            old.hide()

    anchor = None
    for b in mw.findChildren(QPushButton):
        if b is not btn and _ANCHOR.search(b.text() or ""):
            anchor = b
            break
    placed = False
    if anchor is not None:
        btn.setSizePolicy(anchor.sizePolicy())
        if anchor.styleSheet():
            btn.setStyleSheet(anchor.styleSheet())
        if anchor.minimumHeight():
            btn.setMinimumHeight(anchor.minimumHeight())
        w = anchor.parentWidget()
        while w is not None and not placed:
            lay = w.layout()
            found = _locate(lay, anchor) if lay is not None else None
            if found and isinstance(found[0], QBoxLayout):
                found[0].insertWidget(found[1], btn)
                placed = True
            w = w.parentWidget()
    if not placed:
        try:
            mw.statusBar().addPermanentWidget(btn)
            placed = True
        except Exception:
            pass
    print("[EXPORT] bouton unique installé :", "barre du haut" if (placed and anchor is not None) else "barre de statut")


def install(main_window_class):
    original = main_window_class.__init__

    def __init__(self, *args, **kwargs):
        original(self, *args, **kwargs)
        QTimer.singleShot(0, lambda: _install_button(self))

    main_window_class.__init__ = __init__
