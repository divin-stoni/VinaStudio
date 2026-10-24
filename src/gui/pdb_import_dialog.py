# -*- coding: utf-8 -*-
"""
pdb_import_dialog.py

Interface de l'import assiste :
- choose_receptor_source : code PDB (RCSB) ou fichier local.
- PdbImportDialog : fiche de la structure, choix des chaines, ligand de
  reference pour la grid box, options de nettoyage.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src import guide_assistant

_FILE_FILTER = ("Récepteurs (*.pdbqt *.pdb);;Fichiers PDBQT (*.pdbqt);;"
                "Fichiers PDB (*.pdb)")


# ------------------------------------------------------------------ source
class _SourceDialog(QDialog):

    def __init__(self, parent, title_suffix, download_dir):
        super().__init__(parent)
        self.path = None
        self._dir = Path(download_dir)
        self.setWindowTitle(f"Importer un récepteur{title_suffix}")
        self.setMinimumWidth(460)

        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.addWidget(QLabel("Télécharger depuis le RCSB (code à 4 caractères) :"))
        row = QHBoxLayout()
        self.code = QLineEdit()
        self.code.setPlaceholderText("ex. 4MT1")
        self.code.setMaxLength(4)
        self.btn_dl = QPushButton("Télécharger")
        row.addWidget(self.code, 1)
        row.addWidget(self.btn_dl)
        lay.addLayout(row)
        lay.addWidget(QLabel("ou"))
        self.btn_file = QPushButton("Choisir un fichier PDB ou PDBQT…")
        lay.addWidget(self.btn_file)
        self.msg = QLabel("")
        self.msg.setWordWrap(True)
        self.msg.setStyleSheet("color: #b91c1c; font-size: 12px;")
        lay.addWidget(self.msg)
        cancel = QPushButton("Annuler")
        cancel.clicked.connect(self.reject)
        lay.addWidget(cancel, 0, Qt.AlignRight)

        self.btn_dl.clicked.connect(lambda _=False: self._download())
        self.code.returnPressed.connect(self._download)
        self.btn_file.clicked.connect(lambda _=False: self._browse())

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choisir le fichier du récepteur (PDB ou PDBQT)", "", _FILE_FILTER)
        if path:
            self.path = Path(path)
            self.accept()

    def _download(self):
        code = self.code.text().strip().upper()
        if not re.fullmatch(r"[0-9][A-Z0-9]{3}", code):
            self.msg.setText("Code invalide : 4 caractères, le premier est un chiffre (ex. 4MT1).")
            return
        self.msg.setText("")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            import requests
            resp = requests.get(
                f"https://files.rcsb.org/download/{code}.pdb",
                timeout=30, headers={"User-Agent": "VinaStudio"})
        except Exception as exc:
            resp = None
            self.msg.setText(f"Téléchargement impossible : {type(exc).__name__}. Vérifie la connexion.")
        finally:
            QApplication.restoreOverrideCursor()
        if resp is None:
            return
        if resp.status_code == 404:
            self.msg.setText(
                "Aucun fichier PDB pour ce code (code inexistant, ou très grande structure "
                "disponible seulement en mmCIF).")
            return
        if resp.status_code != 200:
            self.msg.setText(f"Le RCSB a répondu avec l'erreur HTTP {resp.status_code}.")
            return
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            dest = self._dir / f"{code}.pdb"
            dest.write_bytes(resp.content)
        except OSError as exc:
            self.msg.setText(f"Écriture impossible : {exc}")
            return
        self.path = dest
        self.accept()


def choose_receptor_source(parent, title_suffix, download_dir):
    """Retourne le chemin du fichier choisi ou telecharge, ou None si annule."""
    dlg = _SourceDialog(parent, title_suffix, download_dir)
    if dlg.exec() != QDialog.Accepted:
        return None
    return dlg.path


# ------------------------------------------------------------------- fiche
def _bold(text):
    lab = QLabel(text)
    lab.setStyleSheet("font-weight: 600;")
    return lab


def _card_html(r) -> str:
    esc = html.escape
    rows = [f"<b>{esc(r.title or Path(r.path).name)}</b>"]
    meth = esc(r.method or "méthode non indiquée")
    if r.resolution is not None:
        if r.resolution <= 2.5:
            color, word = "#15803d", "bonne"
        elif r.resolution <= 3.5:
            color, word = "#b45309", "moyenne"
        else:
            color, word = "#b91c1c", "faible"
        meth += (f' · résolution <span style="color:{color}"><b>'
                 f'{r.resolution:.2f} Å ({word})</b></span>')
    rows.append(meth)
    if r.organism:
        rows.append(f"Organisme : {esc(r.organism)}")
    rows.append(f"{len(r.chains)} chaîne(s) protéique(s), "
                f"{sum(c.n_res for c in r.chains.values())} résidus")
    other = []
    if r.n_water:
        other.append(f"{r.n_water} molécule(s) d'eau")
    if r.ions:
        other.append("ions : " + ", ".join(f"{k} ×{v}" for k, v in r.ions.items()))
    if r.additives:
        other.append("additifs : " + ", ".join(f"{k} ×{v}" for k, v in r.additives.items()))
    if r.ligands:
        other.append("ligands : " + ", ".join(
            f"{l.resname}" + (f" ({guide_assistant.short_name(l.name)})" if l.name else "") + f" chaîne {l.chain}"
            for l in r.ligands))
    if r.modified:
        other.append("résidus modifiés : " + ", ".join(f"{k} ×{v}" for k, v in r.modified.items()))
    rows.append("Contenu non protéique : " + (esc(" · ".join(other)) if other else "aucun"))
    for w in r.warnings:
        rows.append(f'<span style="color:#b45309">⚠ {esc(w)}</span>')
    return "<br>".join(rows)


def _remark(report, c) -> str:
    parts = []
    same = [o.chain for o in report.chains.values()
            if o.group == c.group and o.chain != c.chain]
    if same:
        parts.append("identique à " + ", ".join(same))
    for key, n in c.contacts.items():
        lig = report.ligand_by_key(key)
        if lig is not None:
            parts.append(f"lie {lig.resname} ({n} atomes à moins de 4,5 Å)")
    return " ; ".join(parts)


class PdbImportDialog(QDialog):

    def __init__(self, report, parent=None):
        super().__init__(parent)
        self._report = report
        self.setWindowTitle("Importer un récepteur : fiche de la structure")
        self.setMinimumWidth(800)

        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        self.card = QLabel(_card_html(report))
        self.card.setTextFormat(Qt.RichText)
        self.card.setWordWrap(True)
        lay.addWidget(self.card)

        lay.addWidget(_bold("Chaînes à conserver pour le docking"))
        chains = list(report.chains.values())
        self._chain_names = [c.chain for c in chains]
        self.table = QTableWidget(len(chains), 6)
        self.table.setHorizontalHeaderLabels(
            ["Garder", "Chaîne", "Molécule", "Résidus", "Manquants", "Remarque"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        for r, c in enumerate(chains):
            keep = QTableWidgetItem()
            keep.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            keep.setCheckState(
                Qt.Checked if c.chain in report.suggested_chains else Qt.Unchecked)
            self.table.setItem(r, 0, keep)
            texts = (c.chain, c.molecule or "?", str(c.n_res), str(c.missing),
                     _remark(report, c))
            for col, text in enumerate(texts, start=1):
                it = QTableWidgetItem(text)
                it.setFlags(Qt.ItemIsEnabled)
                self.table.setItem(r, col, it)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)
        self.table.setMinimumHeight(min(260, 40 + 30 * max(1, len(chains))))
        lay.addWidget(self.table)

        quick = QHBoxLayout()
        for text, fn in (
            ("Suggestion", lambda: self._set_checked(set(report.suggested_chains))),
            ("Une chaîne par groupe", lambda: self._set_checked(set(report.one_per_group()))),
            ("Toutes", lambda: self._set_checked(set(self._chain_names))),
            ("Aucune", lambda: self._set_checked(set())),
        ):
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, f=fn: f())
            quick.addWidget(b)
        quick.addStretch(1)
        lay.addLayout(quick)

        lay.addWidget(_bold("Grid box"))
        row = QHBoxLayout()
        row.addWidget(QLabel("Placer la grid box autour du ligand :"))
        self.lig_combo = QComboBox()
        self.lig_combo.addItem("Aucun (centroïde de la protéine, à ajuster ensuite)", "")
        default_idx = 0
        for i, lig in enumerate(report.ligands, start=1):
            txt = (f"{lig.label}" + (f" : {guide_assistant.short_name(lig.name)}" if lig.name else "")
                   + f", {lig.n_atoms} atomes")
            self.lig_combo.addItem(txt, lig.key)
            if lig.key == report.suggested_ligand:
                default_idx = i
        self.lig_combo.setCurrentIndex(default_idx)
        row.addWidget(self.lig_combo, 1)
        row.addWidget(QLabel("Marge"))
        self.margin = QDoubleSpinBox()
        self.margin.setRange(0.0, 30.0)
        self.margin.setDecimals(1)
        self.margin.setSingleStep(0.5)
        self.margin.setValue(8.0)
        self.margin.setSuffix(" Å")
        self.margin.setToolTip("Distance ajoutée de chaque côté du ligand. Les ligands à cribler "
                               "sont souvent plus gros que celui du cristal : garde de la marge.")
        row.addWidget(self.margin)
        lay.addLayout(row)

        lay.addWidget(_bold("Nettoyage"))
        self.chk_alt = None
        if report.altloc_residues:
            self.chk_alt = QCheckBox("Garder une seule conformation alternative par résidu")
            self.chk_alt.setChecked(True)
            lay.addWidget(self.chk_alt)
        self.chk_mse = None
        if "MSE" in report.modified:
            self.chk_mse = QCheckBox("Convertir la sélénométhionine (MSE) en méthionine")
            self.chk_mse.setChecked(True)
            lay.addWidget(self.chk_mse)
        self.chk_h = QCheckBox("Ajouter les hydrogènes à la conversion (pH 7,4)")
        self.chk_h.setChecked(not report.has_h)
        self.chk_h.setToolTip("Coché par défaut : sans hydrogènes polaires, Vina ne voit pas les "
                              "liaisons hydrogène. Décoché si le fichier en contient déjà.")
        lay.addWidget(self.chk_h)
        info = QLabel("Retirés du fichier : eaux, ions, additifs et ligands (le ligand choisi "
                      "sert uniquement à placer la grid box). Un rapport détaillé est écrit "
                      "à côté du fichier nettoyé.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #6b7785; font-size: 11px;")
        lay.addWidget(info)

        lay.addWidget(_bold("Conseils de l'assistant"))
        self.advice_label = QLabel()
        self.advice_label.setTextFormat(Qt.RichText)
        self.advice_label.setWordWrap(True)
        lay.addWidget(self.advice_label)
        self.btn_reco = QPushButton("Appliquer les réglages recommandés")
        self.btn_reco.setToolTip("Chaîne liante, ligand de référence le plus fiable, marge de 8 Å, "
                                 "hydrogènes ajoutés, nettoyage conseillé.")
        self.btn_reco.clicked.connect(lambda _=False: self._apply_recommended())
        lay.addWidget(self.btn_reco, 0, Qt.AlignLeft)
        self.table.itemChanged.connect(lambda *_: self._refresh_advice())
        self.lig_combo.currentIndexChanged.connect(lambda *_: self._refresh_advice())
        self.margin.valueChanged.connect(lambda *_: self._refresh_advice())
        self.chk_h.toggled.connect(lambda *_: self._refresh_advice())
        self._apply_recommended(initial=True)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Importer")
        buttons.button(QDialogButtonBox.Cancel).setText("Annuler")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _apply_recommended(self, initial=False):
        rep = self._report
        try:
            key = guide_assistant.best_ligand_key(rep)
        except Exception:
            key = rep.suggested_ligand
        lig = rep.ligand_by_key(key) if key else None
        chains = {lig.best_chain} if (lig and lig.best_chain) else set(rep.suggested_chains)
        self.table.blockSignals(True)
        self._set_checked(chains)
        self.table.blockSignals(False)
        idx = self.lig_combo.findData(key or "")
        if idx >= 0:
            self.lig_combo.setCurrentIndex(idx)
        if not initial:
            self.margin.setValue(8.0)
            self.chk_h.setChecked(not self._report.has_h)
            if self.chk_alt is not None:
                self.chk_alt.setChecked(True)
            if self.chk_mse is not None:
                self.chk_mse.setChecked(True)
        self._refresh_advice()

    def _refresh_advice(self):
        try:
            adv = guide_assistant.advise_all(self._report, self.choices())
            level, phrase = guide_assistant.overall(adv)
            self.advice_label.setText(guide_assistant.to_html(adv, phrase, level))
        except Exception as exc:
            self.advice_label.setText(f"<i>Assistant indisponible ({html.escape(str(exc))}).</i>")

    def _set_checked(self, names):
        for r, name in enumerate(self._chain_names):
            self.table.item(r, 0).setCheckState(Qt.Checked if name in names else Qt.Unchecked)

    def choices(self) -> dict:
        chains = [self._chain_names[r] for r in range(self.table.rowCount())
                  if self.table.item(r, 0).checkState() == Qt.Checked]
        return {
            "chains": chains,
            "ligand": self.lig_combo.currentData() or "",
            "margin": float(self.margin.value()),
            "convert_mse": bool(self.chk_mse and self.chk_mse.isChecked()),
            "single_altloc": bool(self.chk_alt and self.chk_alt.isChecked()),
            "protonate": bool(self.chk_h.isChecked()),
        }

    def accept(self):
        ch = self.choices()
        if not ch["chains"]:
            QMessageBox.warning(self, "Aucune chaîne sélectionnée",
                                "Sélectionne au moins une chaîne pour continuer.")
            return
        lig = self._report.ligand_by_key(ch["ligand"]) if ch["ligand"] else None
        if lig is not None and lig.best_chain and lig.best_chain not in ch["chains"]:
            ans = QMessageBox.question(
                self, "Ligand et chaînes",
                f"Le ligand {lig.resname} est lié à la chaîne {lig.best_chain}, que tu n'as pas "
                "conservée. La grid box serait placée hors de la protéine importée.\n\nContinuer ?")
            if ans != QMessageBox.Yes:
                return
        super().accept()
