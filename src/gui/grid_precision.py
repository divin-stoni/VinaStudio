# -*- coding: utf-8 -*-
"""
grid_precision.py

Controles precis pour la grid box :
- PreciseSpinBox : Maj + fleches = pas fin (/10), molette seulement si focus,
  valeur tapee validee a Entree ou a la perte de focus.
- FineSlider : fenetre glissante autour de la valeur courante au lieu de
  toute la plage (centres +-15 A, tailles +-10 A).
- build_override_row_with_fit : ajoute le bloc "Ajustement precis" sous la
  rangee Enregistrer / Centrer sur residu existante.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from src import grid_fit


class PreciseSpinBox(QDoubleSpinBox):

    FINE_FACTOR = 0.1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setKeyboardTracking(False)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
            return
        super().wheelEvent(event)

    def stepBy(self, steps):
        if QGuiApplication.keyboardModifiers() & Qt.ShiftModifier:
            self.setValue(self.value() + steps * self.singleStep() * self.FINE_FACTOR)
            return
        super().stepBy(steps)


class FineSlider(QSlider):
    """
    Les appelants fixent une plage absolue (centres : +-1000 A, echelle 1000 ;
    tailles : 1 a 200 A, echelle 100) puis appellent setValue. La plage reelle
    est une fenetre autour de la valeur, recentree a chaque setValue Python et
    au relachement du curseur.
    """

    CENTER_HALF_A = 15.0
    SIZE_HALF_A = 10.0

    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self._abs_lo = None
        self._abs_hi = None
        self.setFocusPolicy(Qt.StrongFocus)
        self.sliderReleased.connect(self._recenter)

    def setMinimum(self, v):
        self._abs_lo = int(v)
        super().setMinimum(int(v))

    def setMaximum(self, v):
        self._abs_hi = int(v)
        super().setMaximum(int(v))

    def setRange(self, lo, hi):
        self._abs_lo = int(lo)
        self._abs_hi = int(hi)
        super().setRange(int(lo), int(hi))

    def _geometry(self):
        lo, hi = self._abs_lo, self._abs_hi
        if lo is None or hi is None or hi <= 0:
            return None
        if lo < 0:
            scale = hi / 1000.0
            half = self.CENTER_HALF_A * scale
        else:
            scale = hi / 200.0
            half = self.SIZE_HALF_A * scale
        return scale, int(round(half))

    def _recenter(self):
        self.setValue(self.value())

    def setValue(self, v):
        v = int(v)
        geo = self._geometry()
        if geo is None or self.isSliderDown():
            super().setValue(v)
            return
        scale, half = geo
        v = max(self._abs_lo, min(self._abs_hi, v))
        lo = max(self._abs_lo, v - half)
        hi = min(self._abs_hi, v + half)
        was_blocked = self.signalsBlocked()
        old = self.value()
        self.blockSignals(True)
        super().setRange(lo, hi)
        super().setValue(v)
        self.setSingleStep(max(1, int(round(0.1 * scale))))
        self.setPageStep(max(1, int(round(1.0 * scale))))
        self.blockSignals(was_blocked)
        if not was_blocked and self.value() != old:
            self.valueChanged.emit(self.value())

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
            return
        super().wheelEvent(event)


class _VisibilityMirror(QObject):
    """Le bloc d'ajustement suit la visibilite des champs de la grid box."""

    def __init__(self, source, target):
        super().__init__(target)
        self._source = source
        self._target = target
        source.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self._source:
            t = event.type()
            if t == QEvent.Type.Show:
                self._target.setVisible(True)
            elif t == QEvent.Type.Hide:
                self._target.setVisible(False)
        return False


def _fmt_int(v):
    return f"{v:,.0f}".replace(",", " ")


class _FitPanel(QFrame):

    KEYS = ("center_x", "center_y", "center_z", "size_x", "size_y", "size_z")
    VOLUME_WARN = 27000.0
    C_NORMAL = "#44505c"
    C_WARN = "#b45309"
    C_ERR = "#b91c1c"

    def __init__(self, page, get_profile, is_current, fields, sliders):
        super().__init__()
        self._page = page
        self._get_profile = get_profile
        self._is_current = is_current
        self._fields = fields
        self._sliders = sliders
        self._source = fields["center_x"]
        self._undo = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 0)
        lay.setSpacing(6)

        title = QLabel("Ajustement précis de la grid box")
        title.setStyleSheet("font-weight: 600;")
        hint = QLabel(
            "Calcule le centre et la taille de la boîte à partir d'un ligand ou de "
            "résidus. Rien n'est enregistré tant que tu n'as pas cliqué sur "
            "Enregistrer. Maj + flèches dans un champ : pas fin (÷10)."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #6b7785; font-size: 11px;")

        self.margin = PreciseSpinBox()
        self.margin.setRange(0.0, 30.0)
        self.margin.setDecimals(1)
        self.margin.setSingleStep(0.5)
        self.margin.setValue(5.0)
        self.margin.setSuffix(" Å")
        self.margin.setMaximumWidth(100)
        self.margin.setToolTip(
            "Distance ajoutée de chaque côté de la cible. 4 à 6 Å est la plage usuelle avec Vina."
        )

        self.btn_ligand = QPushButton("Autour du ligand du récepteur")
        self.btn_ligand.setToolTip(
            "Utilise le ligand co-cristallisé (HETATM) présent dans le fichier du récepteur."
        )
        self.btn_file = QPushButton("Autour d'un fichier ligand…")
        self.btn_file.setToolTip(
            "SDF, MOL, PDB ou PDBQT. Les coordonnées doivent être dans le même repère "
            "que le récepteur (ligand co-cristallisé ou pose de docking)."
        )
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Résidus : GLY22, F178, A:VAL139")
        self.btn_res = QPushButton("Entourer ces résidus")
        self.btn_undo = QPushButton("Annuler le dernier ajustement")
        self.btn_undo.setEnabled(False)

        self.msg = QLabel("")
        self.msg.setWordWrap(True)
        self.msg.setStyleSheet(f"color: {self.C_NORMAL}; font-size: 12px;")
        self.stats = QLabel("")
        self.stats.setWordWrap(True)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.addWidget(QLabel("Marge de chaque côté"), 0, 0)
        grid.addWidget(self.margin, 0, 1)
        grid.addWidget(self.btn_ligand, 1, 0)
        grid.addWidget(self.btn_file, 1, 1)
        grid.addWidget(self.edit, 2, 0, 1, 2)
        grid.addWidget(self.btn_res, 3, 0)
        grid.addWidget(self.btn_undo, 3, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        lay.addWidget(title)
        title.setToolTip(hint.text())
        lay.addLayout(grid)
        lay.addWidget(self.msg)
        lay.addWidget(self.stats)

        self.btn_ligand.clicked.connect(lambda _=False: self._fit_ligand())
        self.btn_file.clicked.connect(lambda _=False: self._fit_file())
        self.btn_res.clicked.connect(lambda _=False: self._fit_residues())
        self.edit.returnPressed.connect(self._fit_residues)
        self.btn_undo.clicked.connect(lambda _=False: self._undo_last())

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(80)
        self._timer.timeout.connect(self._refresh)
        for f in fields.values():
            f.valueChanged.connect(self._schedule_refresh)
        for s in sliders.values():
            s.valueChanged.connect(self._schedule_refresh)

        self._mirror = _VisibilityMirror(self._source, self)

    # ------------------------------------------------------------ utilitaires
    def showEvent(self, event):
        super().showEvent(event)
        try:
            if not self._source.isVisibleTo(self._source.window()):
                QTimer.singleShot(0, self.hide)
                return
        except Exception:
            pass
        self._schedule_refresh()

    def _schedule_refresh(self, *_):
        self._timer.start()

    def _say(self, text, error=False):
        color = self.C_ERR if error else self.C_NORMAL
        self.msg.setStyleSheet(f"color: {color}; font-size: 12px;")
        self.msg.setText(text)
        status = getattr(self._page, "execution_status", None)
        if status is not None:
            try:
                status.setText(text)
            except Exception:
                pass

    def _values(self):
        return tuple(float(self._fields[k].value()) for k in self.KEYS)

    def _paths(self, prefer_pdb):
        profile = self._get_profile()
        if profile is None:
            return []
        names = (("pdb_path_for_viewer", "pdbqt_path") if prefer_pdb
                 else ("pdbqt_path", "pdb_path_for_viewer"))
        out = []
        for n in names:
            try:
                v = getattr(profile, n, None)
            except Exception:
                v = None
            if v and Path(str(v)).exists() and str(v) not in out:
                out.append(str(v))
        return out

    def _ready(self):
        profile = self._get_profile()
        if profile is None:
            self._say("Aucun récepteur chargé.", error=True)
            return None
        if not self._fields["center_x"].isEnabled():
            self._say(
                "Grid box verrouillée dans ce mode : choisis le récepteur seul pour l'ajuster.",
                error=True,
            )
            return None
        return profile

    def _set_values(self, vals):
        for k, v in zip(self.KEYS, vals):
            self._fields[k].setValue(float(v))
        profile = self._get_profile()
        if profile is not None:
            self._page._sync_grid_profile(profile, self._fields)
            if self._is_current():
                self._page._update_viewer_box(profile.grid_box)
        self._schedule_refresh()

    # ----------------------------------------------------------- statistiques
    def _refresh(self):
        if not self.isVisible():
            return
        try:
            vals = self._values()
        except Exception:
            return
        c, s = vals[:3], vals[3:]
        vol = float(np.prod(s))
        text = f"Boîte {s[0]:.1f} × {s[1]:.1f} × {s[2]:.1f} Å, volume {_fmt_int(vol)} Å³"
        color = self.C_NORMAL
        paths = self._paths(prefer_pdb=False)
        if paths:
            try:
                st = grid_fit.load_structure(paths[0])
                stats = grid_fit.box_stats(st, c, s)
                text += (f" · {stats['n_in']} résidus dans la boîte, "
                         f"dont {stats['n_cut']} coupés en bordure")
                if stats["n_in"] == 0:
                    text += " · la boîte ne contient aucun résidu du récepteur"
                    color = self.C_ERR
            except Exception:
                pass
        if vol > self.VOLUME_WARN:
            text += (" · au-delà de 27 000 Å³ la recherche Vina perd en fiabilité : "
                     "réduis la boîte ou augmente l'exhaustivité")
            if color != self.C_ERR:
                color = self.C_WARN
        self.stats.setStyleSheet(f"color: {color}; font-size: 12px;")
        self.stats.setText(text)

    # --------------------------------------------------------------- actions
    def _finish(self, xyz, label, notes):
        margin = float(self.margin.value())
        center, size, clamped = grid_fit.box_from_coords(xyz, margin)
        vals = (tuple(round(float(v), 3) for v in center)
                + tuple(round(float(v), 2) for v in size))
        self._undo.append(self._values())
        del self._undo[:-20]
        self.btn_undo.setEnabled(True)
        self._set_values(vals)
        msg = (f"Grid box ajustée autour de {label} (marge {margin:.1f} Å) : "
               f"centre {vals[0]:.2f}, {vals[1]:.2f}, {vals[2]:.2f} ; "
               f"taille {vals[3]:.1f} × {vals[4]:.1f} × {vals[5]:.1f} Å.")
        if clamped:
            notes.append("Taille limitée entre 1 et 200 Å.")
        if notes:
            msg += " " + " ".join(notes)
        self._say(msg, error=bool(clamped))

    def _fit_ligand(self):
        if self._ready() is None:
            return
        for path in self._paths(prefer_pdb=True):
            try:
                st = grid_fit.load_structure(path)
            except Exception:
                continue
            i = grid_fit.find_ligand(st)
            if i is not None:
                label = (f"le ligand {st.name[i]}{st.num[i]} "
                         f"(chaîne {st.chain[i] or '?'})")
                self._finish(grid_fit.coords_of(st, [i]), label, [])
                return
        self._say(
            "Aucun ligand co-cristallisé trouvé dans le fichier du récepteur. "
            "Utilise « Autour d'un fichier ligand… » (SDF, PDB ou PDBQT).",
            error=True,
        )

    def _fit_file(self):
        if self._ready() is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Choisir le ligand de référence", "",
            "Ligand (*.sdf *.mol *.pdb *.pdbqt);;Tous les fichiers (*)",
        )
        if not path:
            return
        try:
            xyz = grid_fit.read_ligand_file(path)
        except Exception as exc:
            self._say(f"Lecture impossible : {exc}", error=True)
            return
        notes = []
        paths = self._paths(prefer_pdb=False)
        if paths:
            try:
                st = grid_fit.load_structure(paths[0])
                center = (xyz.min(axis=0) + xyz.max(axis=0)) / 2.0
                if not grid_fit.receptor_bbox_contains(st, center):
                    notes.append(
                        "Attention : ce ligand semble hors du récepteur, vérifie que les "
                        "coordonnées sont dans le même repère (Annuler restaure la boîte)."
                    )
            except Exception:
                pass
        self._finish(xyz, f"le ligand « {Path(path).name} »", notes)

    def _fit_residues(self):
        if self._ready() is None:
            return
        paths = self._paths(prefer_pdb=False)
        if not paths:
            self._say("Fichier du récepteur introuvable.", error=True)
            return
        try:
            st = grid_fit.load_structure(paths[0])
            specs = grid_fit.parse_residue_query(self.edit.text())
            sel, notes = grid_fit.select_residues(st, specs)
            xyz = grid_fit.coords_of(st, sel)
        except Exception as exc:
            self._say(f"Ajustement impossible : {exc}", error=True)
            return
        label = "les résidus " + ", ".join(s["raw"] for s in specs)
        self._finish(xyz, label, notes)

    def _undo_last(self):
        if not self._undo or self._ready() is None:
            return
        vals = self._undo.pop()
        self._set_values(vals)
        self.btn_undo.setEnabled(bool(self._undo))
        self._say("Grid box restaurée à l'état précédent.")


def build_override_row_with_fit(page, base, *args, **kwargs):
    """Enveloppe _build_grid_override_row : meme retour, plus le bloc d'ajustement."""
    result = base(*args, **kwargs)
    try:
        row, *rest = result
        panel = _FitPanel(
            page,
            kwargs["get_profile"],
            kwargs["is_current"],
            kwargs["fields"],
            kwargs["sliders"],
        )
        combined = QVBoxLayout()
        combined.setContentsMargins(0, 0, 0, 0)
        combined.setSpacing(8)
        combined.addLayout(row)
        combined.addWidget(panel)
        return (combined, *rest)
    except Exception as exc:
        import sys
        print(f"[grid_precision] bloc d'ajustement non ajouté : {exc}", file=sys.stderr)
        return result
