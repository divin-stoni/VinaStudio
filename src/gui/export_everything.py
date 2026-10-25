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
    if name == "config.txt" or ext == ".conf":
        return put("00_configuration", tgt)
    if ext == ".txt" and ("2d" in p or "diagram" in p):
        return put("03_visualisation", "diagrammes_2d", tgt)
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
    for f in sorted(PROJECT_ROOT.glob("docking_results_combined*.csv")):
        out.append(("racine", f, True))
    return out


def _build_plan(sources, since):
    plan = []
    for label, root, use_filter in sources:
        files = [root] if root.is_file() else _iter_files(root)
        for f in files:
            try:
                if use_filter and f.stat().st_mtime < since:
                    continue
            except OSError:
                continue
            rel = Path(f.name) if root.is_file() else f.relative_to(root)
            plan.append((f, classify(Path(label) / rel)))
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

        have = set()
        if viz_ok:
            for f in (root / "03_visualisation").rglob("*"):
                if f.is_file():
                    have.add((f.name, f.stat().st_size))
        for src, dest_rel in _build_plan(_sources(mw, notes), _since()):
            if viz_ok and dest_rel.parts and dest_rel.parts[0] == "03_visualisation":
                try:
                    if (src.name, src.stat().st_size) in have:
                        continue
                except OSError:
                    pass
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


# ==== PLACEMENT DU BOUTON ====
import unicodedata

from PySide6.QtCore import QPoint, QRect, QSettings
from PySide6.QtWidgets import QAbstractButton, QToolButton

_LABELS = {
    "fr": "Exporter les résultats",
    "en": "Export results",
    "de": "Ergebnisse exportieren",
    "zh": "导出结果",
    "ja": "結果をエクスポート",
}
_OLD = re.compile(r"(tout exporter|exporter tout|export all|alles exportieren|全部导出|すべてエクスポート)", re.I)


def label():
    try:
        code = str(QSettings("VINA Studio", "VINA Studio").value("language/code", "fr") or "fr")[:2].lower()
    except Exception:
        code = "fr"
    return _LABELS.get(code, _LABELS["fr"])


def _norm(s):
    return unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().lower().strip()


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


def _visible_buttons(mw):
    out = []
    for b in mw.findChildren(QAbstractButton):
        try:
            if b.isVisibleTo(mw):
                out.append(b)
        except Exception:
            continue
    return out


def _y_of(w, mw):
    try:
        return w.mapTo(mw, QPoint(0, 0)).y()
    except Exception:
        return 10 ** 6


def _find_anchor(mw):
    """Retourne (bouton de repère, True si on place APRÈS lui)."""
    btns = [b for b in _visible_buttons(mw) if b is not getattr(mw, "_export_everything_button", None)]
    for needle, after in (("phytomol", True), ("arriere-plan", False), ("parametres", False)):
        matches = [b for b in btns if needle in _norm(b.text())]
        if matches:
            return min(matches, key=lambda b: _y_of(b, mw)), after
    return None, True


def _make_button(anchor):
    txt = label()
    btn = None
    cls = type(anchor)
    if cls.__module__ != "PySide6.QtWidgets":
        for args in ((txt,), ()):
            try:
                btn = cls(*args)
                break
            except Exception:
                btn = None
    if btn is None:
        btn = QToolButton() if isinstance(anchor, QToolButton) else QPushButton()
    btn.setText(txt)
    try:
        btn.setSizePolicy(anchor.sizePolicy())
        if anchor.styleSheet():
            btn.setStyleSheet(anchor.styleSheet())
        for name in anchor.dynamicPropertyNames():
            key = bytes(name).decode()
            if key.startswith("_q_") or re.search(r"active|current|check|select", key, re.I):
                continue
            btn.setProperty(key, anchor.property(key))
        if anchor.objectName():
            btn.setObjectName(anchor.objectName())
        btn.setFont(anchor.font())
        btn.setMinimumHeight(anchor.minimumHeight())
        btn.setMaximumHeight(anchor.maximumHeight())
        btn.setCheckable(False)
        if isinstance(btn, QToolButton):
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            if isinstance(anchor, QToolButton):
                btn.setAutoRaise(anchor.autoRaise())
    except Exception:
        pass
    return btn


def _chain(anchor):
    parts = []
    w = anchor.parentWidget()
    while w is not None:
        lay = w.layout()
        parts.append("%s %dx%d disposition=%s" % (type(w).__name__, w.width(), w.height(),
                                                  type(lay).__name__ if lay is not None else "aucune"))
        w = w.parentWidget()
    return " < ".join(parts)


def _place(mw, btn, anchor, after):
    """Retourne le mode de placement utilisé, ou '' si impossible."""
    w = anchor.parentWidget()
    while w is not None:
        lay = w.layout()
        found = _locate(lay, anchor) if lay is not None else None
        if found and isinstance(found[0], QBoxLayout):
            found[0].insertWidget(found[1] + (1 if after else 0), btn)
            return "dans la disposition"
        w = w.parentWidget()

    need_w = max(anchor.width(), btn.sizeHint().width(), btn.fontMetrics().horizontalAdvance(btn.text()) + 44)
    need_h = anchor.height()
    others = [b for b in _visible_buttons(mw) if b is not btn]
    w = anchor.parentWidget()
    while w is not None:
        pos = anchor.mapTo(w, QPoint(0, 0))
        x = pos.x() + anchor.width() + 8 if after else pos.x() - need_w - 8
        rect = QRect(x, pos.y(), need_w, need_h)
        if rect.left() >= 0 and rect.right() <= w.width():
            clash = False
            for o in others:
                if not w.isAncestorOf(o):
                    continue
                try:
                    op = o.mapTo(w, QPoint(0, 0))
                except Exception:
                    continue
                if rect.adjusted(-3, -3, 3, 3).intersects(QRect(op.x(), op.y(), o.width(), o.height())):
                    clash = True
                    break
            if not clash:
                btn.setParent(w)
                btn.setGeometry(rect)
                btn.show()
                btn.raise_()
                return "position libre"
        w = w.parentWidget()
    return ""


def _install_button(mw):
    try:
        if getattr(mw, "_export_everything_button", None) is not None:
            return
        anchor, after = _find_anchor(mw)
        if anchor is None:
            print("[EXPORT] aucun bouton de repère trouvé : bouton non installé, anciens boutons conservés")
            return
        btn = _make_button(anchor)
        btn.setToolTip("Exporte tout dans un dossier daté, rangé par catégories")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda _=False: export_everything(mw))
        mode = _place(mw, btn, anchor, after)
        if not mode:
            btn.deleteLater()
            print("[EXPORT] placement impossible à côté de « %s » : anciens boutons conservés" % anchor.text())
            print("[EXPORT] structure : " + _chain(anchor))
            return
        mw._export_everything_button = btn
        for b in mw.findChildren(QAbstractButton):
            if b is not btn and _OLD.search(b.text() or ""):
                b.hide()
        for page, attr in (("docking_page", "_export_session_button"),
                           ("visualization_page", "export_all_button")):
            old = getattr(getattr(mw, page, None), attr, None)
            if old is not None and old is not btn:
                old.hide()
        print("[EXPORT] bouton « %s » (%s) placé %s « %s » : %s" % (
            btn.text(), type(btn).__name__, "après" if after else "avant", anchor.text(), mode))
    except Exception as exc:
        print("[EXPORT] installation du bouton impossible :", exc)


def install(main_window_class):
    original = main_window_class.__init__

    def __init__(self, *args, **kwargs):
        original(self, *args, **kwargs)
        _STATE["mw"] = self
        QTimer.singleShot(0, lambda: _install_button(self))

    main_window_class.__init__ = __init__


# ==== SUIVI DU PIPELINE ====
import functools
import os

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QCheckBox, QMenu

REMIND_S = int(os.environ.get("VINASTUDIO_REMIND_S", "150") or "150")   # 2 min 30 sans nouvelle étape
_NEEDED = ("docking", "analysis", "interactions")
_NAMES = {"docking": "le docking", "analysis": "l'analyse", "interactions": "le calcul des interactions"}
_STATE = {"mw": None, "stages": {}, "prompted": False, "timer": None, "exported_at": 0.0}


def _qs():
    return QSettings("VINA Studio", "VINA Studio")


def _flag(key, default):
    v = _qs().value(key, None)
    if v is None:
        return default
    return str(v).lower() in ("true", "1", "yes")


def _set(key, value):
    s = _qs()
    s.setValue(key, value)
    s.sync()


def _status(mw, text, ms=8000):
    try:
        mw.statusBar().showMessage(text, ms)
    except Exception:
        pass


def _mark_exported():
    _STATE["exported_at"] = time.time()


def _restart_timer(ms=None):
    st = _STATE
    t = st.get("timer")
    if t is None:
        t = QTimer(st["mw"])
        t.setSingleShot(True)
        t.timeout.connect(_reminder_due)
        st["timer"] = t
    t.start(ms if ms is not None else REMIND_S * 1000)


def _cancel_timer():
    t = _STATE.get("timer")
    if t is not None:
        t.stop()


def _after_stage_change():
    st = _STATE
    mw = st["mw"]
    if mw is None:
        return
    if all(k in st["stages"] for k in _NEEDED):
        _cancel_timer()
        if not st["prompted"]:
            st["prompted"] = True
            QTimer.singleShot(1500, lambda: _prompt_complete(mw))
        return
    _restart_timer()


def _stage(name):
    st = _STATE
    if name == "docking":          # un nouveau docking repart de zéro
        st["stages"] = {}
        st["prompted"] = False
    st["stages"][name] = time.time()
    _after_stage_change()


def _reminder_due():
    st = _STATE
    mw = st["mw"]
    stages = st["stages"]
    if mw is None or not stages or all(k in stages for k in _NEEDED):
        return
    if st["exported_at"] and st["exported_at"] >= max(stages.values()):
        return                      # déjà exporté depuis la dernière étape
    if not _flag("export/remind_enabled", True):
        return
    vp = getattr(mw, "visualization_page", None)
    if QApplication.activeModalWidget() is not None or getattr(vp, "batch_running", False):
        _restart_timer(30000)       # un calcul tourne ou une fenêtre est ouverte : on repousse
        return
    _remind(mw)


def _prompt_complete(mw, tries=0):
    if not _flag("export/prompt_enabled", True):
        return
    if QApplication.activeModalWidget() is not None:
        if tries < 40:
            QTimer.singleShot(3000, lambda: _prompt_complete(mw, tries + 1))
        return
    box = QMessageBox(mw)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle("Pipeline terminé : pensez à exporter")
    box.setText("Le docking, l'analyse et le calcul des interactions sont terminés.\n\n"
                "Les résultats de cette session sont effacés à la fermeture du logiciel.\n"
                "Voulez-vous les exporter maintenant ? (vous choisissez le dossier)")
    go = box.addButton("Exporter…", QMessageBox.ButtonRole.AcceptRole)
    box.addButton("Plus tard", QMessageBox.ButtonRole.RejectRole)
    box.exec()
    if box.clickedButton() is go:
        export_everything(mw)


def _remind(mw):
    stages = _STATE["stages"]
    faits = [_NAMES[k] for k in _NEEDED if k in stages]
    manque = [_NAMES[k] for k in _NEEDED if k not in stages]
    box = QMessageBox(mw)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle("Pensez à exporter")
    box.setText("Terminé : %s.\nPas encore fait : %s.\n\n"
                "Pensez à exporter vos résultats : ils sont effacés à la fermeture du logiciel."
                % (", ".join(faits), ", ".join(manque)))
    cb = QCheckBox("Ne plus afficher ce message")
    box.setCheckBox(cb)
    go = box.addButton("Exporter…", QMessageBox.ButtonRole.AcceptRole)
    box.addButton("Plus tard", QMessageBox.ButtonRole.RejectRole)
    box.exec()
    if cb.isChecked():
        _set("export/remind_enabled", "false")
        _status(mw, "Rappel désactivé (réactivable par clic droit sur le bouton d'export).")
    if box.clickedButton() is go:
        export_everything(mw)


def _menu(mw, btn, pos):
    m = QMenu(btn)
    a_end = QAction("Proposer l'export à la fin du pipeline complet", m)
    a_end.setCheckable(True)
    a_end.setChecked(_flag("export/prompt_enabled", True))
    a_rem = QAction("Rappel « Pensez à exporter » (étapes manquantes)", m)
    a_rem.setCheckable(True)
    a_rem.setChecked(_flag("export/remind_enabled", True))
    m.addAction(a_end)
    m.addAction(a_rem)
    chosen = m.exec(btn.mapToGlobal(pos))
    if chosen is a_end:
        _set("export/prompt_enabled", "true" if a_end.isChecked() else "false")
        _status(mw, "Proposition d'export en fin de pipeline " + ("activée" if a_end.isChecked() else "désactivée"))
    elif chosen is a_rem:
        _set("export/remind_enabled", "true" if a_rem.isChecked() else "false")
        _status(mw, "Rappel d'export " + ("activé" if a_rem.isChecked() else "désactivé"))


def _setup_pipeline(mw, btn):
    _STATE["mw"] = mw
    btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    btn.customContextMenuRequested.connect(lambda pos: _menu(mw, btn, pos))
    btn.setToolTip("Exporte tout dans un dossier daté, rangé par catégories (clic droit : options des rappels)")


def _wrap(cls, name, attr, stage):
    """Ajoute une écoute APRÈS la méthode d'origine, sans rien changer à son contenu."""
    orig = getattr(cls, name, None)
    if orig is None:
        print("[EXPORT] méthode introuvable, suivi non branché :", cls.__name__, name)
        return False
    if getattr(orig, "_export_wrapped", False):
        return True

    @functools.wraps(orig)
    def wrapper(self, *args, **kwargs):
        before = getattr(self, attr, None) if attr else None
        result = orig(self, *args, **kwargs)
        try:
            now = getattr(self, attr, None) if attr else True
            if now and (attr is None or now is not before):
                _stage(stage)
        except Exception as exc:
            print("[EXPORT] suivi du pipeline (%s) : %s" % (name, exc))
        return result

    wrapper._export_wrapped = True
    setattr(cls, name, wrapper)
    return True


def install_pipeline(docking_cls, analysis_cls, viz_cls):
    ok = [
        _wrap(docking_cls, "on_docking_finished", None, "docking"),
        _wrap(analysis_cls, "run_docking_analysis", "statistics_result", "analysis"),
        _wrap(analysis_cls, "_run_statistics_analysis_core", "statistics_result", "analysis"),
        _wrap(viz_cls, "_on_batch_finished", "hit_results", "interactions"),
    ]
    print("[EXPORT] suivi du pipeline branché : %d/4 signaux" % sum(1 for x in ok if x))
