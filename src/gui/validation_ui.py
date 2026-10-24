# -*- coding: utf-8 -*-
"""
validation_ui.py

Ligne « Vérifier ma configuration » ajoutee sous chaque panneau de grid box.
Lance le re-docking du ligand co-cristallise dans un thread, affiche le
resultat en clair, enregistre la validation.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src import guide_assistant, redocking

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REF_DIR = guide_assistant.VALIDATION_DIR / "refs"
WORK_DIR = PROJECT_ROOT / "redocking_runs"


# ------------------------------------------------------------------ outils
def pkey(path) -> str:
    try:
        return str(Path(path).resolve())
    except Exception:
        return str(path)


def fraction_in_box(xyz, center, size) -> float:
    xyz = np.asarray(xyz, dtype=float)
    if len(xyz) == 0:
        return 0.0
    half = np.asarray(size, dtype=float) / 2.0
    inside = (np.abs(xyz - np.asarray(center, dtype=float)) <= half).all(axis=1)
    return float(inside.mean())


def _resolve(profile_id):
    from src.docking import receptor_profile as rp
    fn = getattr(rp, "resolve_target_profile", None) or getattr(rp, "load_profile")
    return fn(profile_id)


def _ref_file(profile_id) -> Path:
    return REF_DIR / f"{profile_id}_ref.json"


def load_ref(profile_id):
    try:
        data = json.loads(_ref_file(profile_id).read_text(encoding="utf-8"))
        if Path(data["pdb"]).exists() and data.get("ligand"):
            return data["pdb"], data["ligand"]
    except Exception:
        pass
    return None


def save_ref(profile_id, pdb, ligand) -> str:
    """Copie le PDB d'origine dans un dossier durable et memorise le ligand."""
    REF_DIR.mkdir(parents=True, exist_ok=True)
    pdb = Path(pdb)
    dest = pdb
    if REF_DIR.resolve() not in pdb.resolve().parents:
        dest = REF_DIR / f"{profile_id}_source.pdb"
        shutil.copy2(pdb, dest)
    _ref_file(profile_id).write_text(
        json.dumps({"pdb": str(dest), "ligand": ligand}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    return str(dest)


# ----------------------------------------------------------------- thread
class _Worker(QThread):
    done = Signal(object)

    def __init__(self, args, parent=None):
        super().__init__(parent)
        self._args = args

    def run(self):
        try:
            res = redocking.redock(*self._args)
        except Exception as exc:
            res = redocking.RedockingResult(False, f"{type(exc).__name__}: {exc}")
        # figure de validation : ajout facultatif, ne bloque jamais le resultat
        try:
            if getattr(res, "ok", False):
                from src import redocking_figure
                work, key = Path(self._args[6]), str(self._args[5])
                tag = key.replace(":", "_")
                out = work / f"{tag}_validation.png"
                redocking_figure.make_figure(
                    work, tag, out, f"{work.name} ({key})",
                    getattr(redocking, "RMSD_THRESHOLD", 2.0))
                res.figure_path = str(out)
        except Exception as exc:
            print(f"[validation] figure non generee : {exc}", file=sys.stderr)
        # donnees completes par pose (pour l'analyse), ajout facultatif
        try:
            if getattr(res, "ok", False):
                from src import redocking_records
                work, key = Path(self._args[6]), str(self._args[5])
                tag = key.replace(":", "_")
                res.pose_table = redocking_records.pose_table(work, tag)
                try:
                    from src import redocking_core
                    res.core_info = redocking_core.analyse(work, tag)
                    for _row, _c in zip(res.pose_table, res.core_info['poses']):
                        _row['rmsd_noyau'] = _c['rmsd_core']
                        _row['rmsd_queues'] = _c['rmsd_tail']
                except Exception as _exc:
                    print(f"[validation] analyse noyau/queues impossible : {_exc}", file=sys.stderr)
                redocking_records.write_csv(res.pose_table, work / f"{tag}_poses.csv")
                res.run_params = dict(self._args[3] or {})
        except Exception as exc:
            print(f"[validation] table des poses non generee : {exc}", file=sys.stderr)
        self.done.emit(res)


# ------------------------------------------------------------------ ligne
class ValidationRow(QWidget):

    def __init__(self, host, profile_id, parent=None):
        super().__init__(parent)
        self._host = host
        self._pid = profile_id
        self._worker = None
        self._ctx = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 0)
        lay.setSpacing(4)
        top = QHBoxLayout()
        self.button = QPushButton("Vérifier ma configuration")
        self.button.setToolTip(
            "Re-docke le ligand du cristal avec ta grid box et tes paramètres, puis compare "
            "avec sa vraie position. Sous 2 Å : configuration valide.")
        self.badge = QLabel()
        top.addWidget(self.button)
        top.addWidget(self.badge, 1)
        lay.addLayout(top)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setMaximumHeight(8)
        self.progress.hide()
        lay.addWidget(self.progress)
        self.result = QLabel()
        self.result.setWordWrap(True)
        self.result.setTextFormat(Qt.RichText)
        self.result.hide()
        lay.addWidget(self.result)

        self.thumb = QPushButton()
        self.thumb.setFlat(True)
        self.thumb.setCursor(Qt.PointingHandCursor)
        self.thumb.setToolTip("Cliquer pour agrandir, enregistrer ou copier la figure")
        self.thumb.hide()
        self._fig_path = None
        self.thumb.clicked.connect(lambda _=False: self._open_figure())
        lay.addWidget(self.thumb)

        self.button.clicked.connect(lambda _=False: self._start())
        self.refresh_badge()
        self._show_figure_if_any()

    # --------------------------------------------------------------- badge
    def refresh_badge(self):
        v = guide_assistant.load_validation(self._pid)
        if v:
            text = guide_assistant.validation_badge(v)
        else:
            text = "⚠ non validé"
            try:
                if getattr(_resolve(self._pid), "validated", False):
                    text = "✔ validé (réglage d'origine)"
            except Exception:
                pass
        color = ("#15803d" if text.startswith("✔")
                 else "#b91c1c" if text.startswith("✖") else "#b45309")
        tip = ""
        try:
            if v and v.get("niveau"):
                from src import validation_levels as _vl
                text, color, tip = _vl.badge(v)
            elif v:
                text, color = "◌ à réévaluer (ancienne mesure)", "#6b7785"
                tip = ("Résultat enregistré avant l'analyse noyau/queues. "
                       "Relance « Vérifier ma configuration ».")
        except Exception:
            pass
        self.badge.setText(text)
        self.badge.setToolTip(tip)
        self.badge.setStyleSheet(f"color: {color}; font-weight: 600;")

    # ---------------------------------------------------------- reference
    def _find_reference(self, profile):
        refs = getattr(self._host, "_import_refs", None) or {}
        ref = refs.get(pkey(profile.pdbqt_path))
        if ref and Path(ref["pdb"]).exists():
            return ref["pdb"], ref["ligand"]
        saved = load_ref(self._pid)
        if saved:
            return saved
        return self._ask_reference(profile)

    def _ask_reference(self, profile):
        pdb = None
        code = (getattr(profile, "source_pdb", None) or "").strip().upper()
        if re.fullmatch(r"[0-9][A-Z0-9]{3}", code):
            REF_DIR.mkdir(parents=True, exist_ok=True)
            dest = REF_DIR / f"{code}.pdb"
            if not dest.exists():
                QApplication.setOverrideCursor(Qt.WaitCursor)
                try:
                    redocking._download_pdb(code, REF_DIR)
                except Exception as exc:
                    QMessageBox.warning(
                        self, "Téléchargement impossible",
                        f"Impossible de télécharger {code} ({type(exc).__name__}). "
                        "Choisis le fichier PDB d'origine à la main.")
                finally:
                    QApplication.restoreOverrideCursor()
            if dest.exists():
                pdb = dest
        if pdb is None:
            QMessageBox.information(
                self, "PDB d'origine",
                "Pour vérifier la configuration, le logiciel a besoin du fichier PDB d'origine "
                "du récepteur, celui qui contient le ligand co-cristallisé.")
            path, _ = QFileDialog.getOpenFileName(
                self, "Fichier PDB d'origine (avec le ligand)", "", "Fichiers PDB (*.pdb)")
            if not path:
                return None
            pdb = Path(path)

        from src import pdb_inspect
        try:
            rep = pdb_inspect.inspect_pdb(pdb)
        except Exception as exc:
            QMessageBox.warning(self, "Lecture impossible", f"{type(exc).__name__}: {exc}")
            return None
        if not rep.ligands:
            QMessageBox.warning(
                self, "Aucun ligand",
                "Ce PDB ne contient aucun ligand co-cristallisé : le re-docking est impossible. "
                "Choisis une structure du même récepteur obtenue avec un ligand.")
            return None
        best = guide_assistant.best_ligand_key(rep)
        ligs = sorted(rep.ligands, key=lambda l: (l.key != best, -l.best_contacts))
        labels = []
        for lig in ligs:
            txt = lig.label
            if lig.name:
                txt += " : " + guide_assistant.short_name(lig.name, 30)
            if guide_assistant.is_lipid_like(lig):
                txt += "  [lipide probable]"
            else:
                bl, bp = guide_assistant.ligand_bfactors(pdb, lig)
                if bl and bp and bl / bp > guide_assistant.B_RATIO_BAD:
                    txt += "  [position peu fiable]"
            if lig.key == best:
                txt += "  ← conseillé"
            labels.append(txt)
        choice, ok = QInputDialog.getItem(
            self, "Ligand de référence",
            "Choisis le ligand dont la position dans le cristal est connue. Il sera retiré puis "
            "re-docké ; le conseillé est le mieux défini et le plus enfoui :",
            labels, 0, False)
        if not ok:
            return None
        return str(pdb), ligs[labels.index(choice)].key

    # ------------------------------------------------------------- lancement
    def _start(self):
        if self._worker is not None:
            return
        try:
            profile = _resolve(self._pid)
        except Exception as exc:
            QMessageBox.warning(self, "Profil introuvable", f"{type(exc).__name__}: {exc}")
            return
        pdbqt = Path(profile.pdbqt_path)
        if not pdbqt.exists():
            QMessageBox.warning(self, "Récepteur introuvable", f"Fichier absent : {pdbqt}")
            return
        ref = self._find_reference(profile)
        if ref is None:
            return
        pdb, key = ref

        from src import pdb_inspect
        try:
            lig = pdb_inspect.inspect_pdb(pdb).ligand_by_key(key)
        except Exception:
            lig = None
        if lig is None:
            QMessageBox.warning(self, "Ligand introuvable",
                                f"Le ligand {key} n'est pas dans {Path(pdb).name}.")
            return
        center = [float(v) for v in profile.grid_box.center]
        size = [float(v) for v in profile.grid_box.size]
        frac = fraction_in_box(lig.xyz, center, size)
        if frac < 0.5:
            ans = QMessageBox.question(
                self, "Ligand hors de la grid box",
                f"Seulement {frac*100:.0f} % des atomes du ligand {key} sont dans la grid box de ce "
                "profil : le test échouera presque sûrement.\n\nContinuer quand même ?")
            if ans != QMessageBox.Yes:
                return
        ans = QMessageBox.question(
            self, "Vérifier ma configuration",
            f"Le logiciel va retirer le ligand {key} du cristal, le re-docker dans ce récepteur avec "
            "ta grid box et tes paramètres, puis mesurer l'écart (RMSD) avec sa vraie position.\n\n"
            "Sous 2 Å, la configuration est considérée valide.\n"
            "Cela prend plusieurs minutes ; tu peux continuer à utiliser le logiciel.\n\nLancer ?")
        if ans != QMessageBox.Yes:
            return
        try:
            pdb = save_ref(self._pid, pdb, key)
        except Exception as exc:
            print(f"[validation] reference non memorisee : {exc}", file=sys.stderr)

        self._ctx = {"profile": profile, "key": key, "center": center, "size": size}
        params = dict(getattr(profile, "docking_params", None) or {})
        args = (pdbqt, center, size, params, pdb, key, WORK_DIR / self._pid)
        self.button.setEnabled(False)
        self.progress.show()
        self.result.setStyleSheet("")
        self.result.setText("Re-docking en cours… (plusieurs minutes)")
        self.result.show()
        self._worker = _Worker(args, self)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    # -------------------------------------------------------------- resultat
    def _on_done(self, res):
        self._worker = None
        self.progress.hide()
        self.button.setEnabled(True)
        ctx = self._ctx or {}
        profile = ctx.get("profile")
        key = ctx.get("key", "?")

        if not res.ok:
            self.result.setStyleSheet("color: #b91c1c;")
            self.result.setText(html.escape(res.summary()))
            self.result.show()
            return

        v = guide_assistant.validation_from_result(res, key)
        v["profile_id"] = self._pid
        v["box"] = {"center": ctx.get("center"), "size": ctx.get("size")}
        try:
            import datetime as _dt
            v["role"] = "redocking"
            v["date"] = _dt.datetime.now().isoformat(timespec="seconds")
            v["poses"] = getattr(res, "pose_table", [])
            v["params"] = getattr(res, "run_params", {})
            v["reference_pdb"] = str(getattr(res, "reference_pdb", ""))
            _ci = getattr(res, "core_info", None)
            if _ci:
                from src import validation_levels as _vl
                v["noyau"] = _ci["resume"]
                v["niveau"] = _vl.level_from_validation(v, _ci)
        except Exception as exc:
            print(f"[validation] donnees completes non ajoutees : {exc}", file=sys.stderr)
        try:
            guide_assistant.save_validation(self._pid, v)
        except Exception as exc:
            print(f"[validation] enregistrement impossible : {exc}", file=sys.stderr)

        note = ""
        if profile is not None and getattr(profile, "profile_type", "") == "user_defined":
            try:
                from src.docking.receptor_profile import save_user_profile
                profile.validated = bool(res.passed)
                save_user_profile(profile)
            except Exception as exc:
                note = f"Profil non mis à jour ({type(exc).__name__})."
        else:
            note = ("Profil intégré : le résultat est enregistré dans receptor_profiles/validation/, "
                    "le fichier du profil n'est pas modifié.")

        self.refresh_badge()
        self._update_combo(bool(res.passed))
        advice = guide_assistant.to_html(guide_assistant.advise_validation(v))
        tech = html.escape(res.summary()).replace("\n", "<br>")
        parts = [advice, f"<span style='color:#6b7785'>{tech}</span>"]
        if v.get("niveau"):
            try:
                from src import validation_levels as _vl
                parts.insert(0, _vl.sentence(v))
            except Exception:
                pass
        if note:
            parts.append(f"<i>{html.escape(note)}</i>")
        self.result.setStyleSheet("")
        self.result.setText("<br>".join(parts))
        self.result.show()
        self._show_figure(getattr(res, "figure_path", None))

    # ---------------------------------------------------------------- figure
    def _show_figure(self, path):
        from PySide6.QtGui import QIcon, QPixmap
        from PySide6.QtCore import QSize
        if not path or not Path(path).exists():
            self.thumb.hide()
            return
        pix = QPixmap(str(path))
        if pix.isNull():
            self.thumb.hide()
            return
        w = 320
        h = max(1, int(w * pix.height() / pix.width()))
        self._fig_path = str(path)
        self.thumb.setIcon(QIcon(pix))
        self.thumb.setIconSize(QSize(w, h))
        self.thumb.setFixedSize(w + 10, h + 10)
        self.thumb.show()

    def _show_figure_if_any(self):
        try:
            d = WORK_DIR / self._pid
            files = sorted(d.glob("*_validation.png"), key=lambda f: f.stat().st_mtime)
            if files:
                self._show_figure(files[-1])
        except Exception:
            pass

    def _open_figure(self):
        from PySide6.QtGui import QPixmap, QDesktopServices
        from PySide6.QtCore import QUrl
        from PySide6.QtWidgets import QDialog, QScrollArea
        path = self._fig_path
        if not path or not Path(path).exists():
            return
        pix = QPixmap(path)
        dlg = QDialog(self)
        dlg.setWindowTitle("Figure de validation par re-docking")
        dlg.resize(1100, 780)
        lay = QVBoxLayout(dlg)
        img = QLabel()
        img.setAlignment(Qt.AlignCenter)
        img.setPixmap(pix.scaledToWidth(1060, Qt.SmoothTransformation))
        scroll = QScrollArea()
        scroll.setWidget(img)
        scroll.setWidgetResizable(True)
        lay.addWidget(scroll, 1)
        row = QHBoxLayout()
        b_save = QPushButton("Enregistrer en PNG")
        b_copy = QPushButton("Copier")
        b_dir = QPushButton("Ouvrir le dossier")
        b_close = QPushButton("Fermer")
        for b in (b_save, b_copy, b_dir):
            row.addWidget(b)
        row.addStretch(1)
        row.addWidget(b_close)
        lay.addLayout(row)

        def _save():
            dest, _ = QFileDialog.getSaveFileName(
                dlg, "Enregistrer la figure", Path(path).name, "Image PNG (*.png)")
            if dest:
                shutil.copy2(path, dest)

        def _copy():
            QApplication.clipboard().setPixmap(pix)

        def _dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).parent)))

        b_save.clicked.connect(lambda _=False: _save())
        b_copy.clicked.connect(lambda _=False: _copy())
        b_dir.clicked.connect(lambda _=False: _dir())
        b_close.clicked.connect(dlg.accept)
        dlg.exec()

    def _update_combo(self, passed):
        combo = getattr(self._host, "target_combo", None)
        if combo is None:
            return
        try:
            idx = combo.findData(self._pid)
            if idx < 0:
                return
            t = combo.itemText(idx)
            if passed and t.startswith("⚠ "):
                combo.setItemText(idx, "✔ " + t[2:])
            elif not passed and t.startswith("✔ "):
                combo.setItemText(idx, "⚠ " + t[2:])
        except Exception:
            pass


def attach_validation_row(host, panel, profile_id):
    if not profile_id:
        raise ValueError("identifiant de profil absent")
    lay = panel.layout()
    if lay is None:
        raise RuntimeError("le panneau n'a pas de layout")
    row = ValidationRow(host, profile_id, panel)
    lay.addWidget(row)
    panel._validation_row = row
    return row
