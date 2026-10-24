# -*- coding: utf-8 -*-
"""Dialogue « Inhibiteurs de reference »."""
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QPushButton, QVBoxLayout)
from src import reference_inhibitors as ri

_PID = {"MexB": "mexb_paeruginosa", "MexR": "mexr_paeruginosa"}


class _Worker(QThread):
    done = Signal(object)

    def __init__(self, jobs, dest, parent=None):
        super().__init__(parent)
        self._jobs, self._dest = jobs, dest

    def run(self):
        out = []
        for job in self._jobs:
            try:
                out.append(ri.fetch_compound(job, self._dest))
            except Exception as exc:
                out.append({"nom": job["nom"], "erreur": str(exc)})
        self.done.emit(out)


def _crystal(pid):
    try:
        from src.gui.validation_ui import load_ref
        r = load_ref(pid)
    except Exception:
        return None
    if not r:
        return None
    pdb, key = (r.get("pdb"), r.get("ligand")) if isinstance(r, dict) else (r[0], r[1])
    fb = None
    try:
        from src.gui.validation_ui import _resolve
        fb = getattr(_resolve(pid), "source_pdb", None)
    except Exception:
        pass
    return {"pdb": ri.pdb_code_from(pdb, fb), "ligand": str(key).split(":")[0], "cle": str(key)}


def open_dialog(host):
    combo = host.target_combo
    data = combo.currentData()
    if not isinstance(data, str) or "+" in combo.currentText():
        QMessageBox.information(host, "Inhibiteurs de référence",
                                "Choisis d'abord une cible unique (pas un couple).")
        return
    pid = _PID.get(data, data)
    fam = ri.family_of(f"{data} {combo.currentText()}")
    if fam is None:
        QMessageBox.information(
            host, "Inhibiteurs de référence",
            "La liste vérifiée couvre MexB, AcrB, AdeB et CmeB. Pour cette cible, ajoute les "
            "composés à la main avec le champ « Ajouter un composé ».")
    cat = ri.load_catalog()
    cr = _crystal(pid)
    role, entry, verified = ("inconnu", None, False)
    if cr:
        role, entry, verified = ri.classify_crystal(cat, cr["pdb"], cr["ligand"])
    crystal_compound = entry if role == "inhibiteur" else None
    picks, missing = ri.propose(cat, fam, crystal_compound) if fam else ([], 3)

    dlg = QDialog(host)
    dlg.setWindowTitle("Inhibiteurs de référence")
    dlg.resize(760, 560)
    lay = QVBoxLayout(dlg)

    if cr:
        txt = (f"Ligand du cristal : {cr['ligand']} ({cr['pdb'] or 'PDB inconnu'}) → rôle : "
               f"<b>{role}</b>" + ("" if verified or role == "inconnu" else " (à confirmer)"))
    else:
        txt = ("Aucun ligand de référence enregistré pour cette cible. Lance d'abord "
               "« Vérifier ma configuration ».")
    head = QLabel(f"Cible : <b>{fam or data}</b><br>{txt}")
    head.setTextFormat(Qt.RichText)
    head.setWordWrap(True)
    lay.addWidget(head)

    lay.addWidget(QLabel("Inhibiteurs documentés pour cette pompe (liste vérifiée) :"))
    boxes = []
    for c in picks:
        cb = QCheckBox(f"{c['nom']}   [{', '.join(c['refs'])}]")
        cb.setChecked(True)
        lay.addWidget(cb)
        boxes.append((cb, c))
    if missing:
        lay.addWidget(QLabel(
            f"Seulement {3 - missing - (1 if crystal_compound else 0) + (1 if crystal_compound else 0)} "
            f"inhibiteur(s) documenté(s) dans la liste. Ajoute-en à la main si besoin "
            "(marqué « non vérifié »)."))

    row = QHBoxLayout()
    add = QLineEdit()
    add.setPlaceholderText("Ajouter un composé (nom PubChem)")
    row.addWidget(add, 1)
    lay.addLayout(row)

    log = QPlainTextEdit()
    log.setReadOnly(True)
    lay.addWidget(log, 1)
    btns = QHBoxLayout()
    go = QPushButton("Télécharger et enregistrer")
    close = QPushButton("Fermer")
    btns.addWidget(go)
    btns.addStretch(1)
    btns.addWidget(close)
    lay.addLayout(btns)
    close.clicked.connect(dlg.accept)
    state = {}

    def _start():
        jobs = []
        for cb, c in boxes:
            if cb.isChecked():
                jobs.append({"nom": c["nom"], "role": "inhibiteur de référence",
                             "pdb": c.get("pdb", []), "queries": ri.QUERIES.get(c["nom"], [c["nom"]]),
                             "refs": c["refs"], "verifie": c.get("verifie", False),
                             "pompes": c.get("pompes")})
        if add.text().strip():
            n = add.text().strip()
            jobs.append({"nom": n, "role": "inhibiteur (ajout utilisateur, non vérifié)",
                         "pdb": [], "queries": [n], "refs": [], "verifie": False,
                         "pompes": [fam] if fam else None})
        if not jobs:
            log.setPlainText("Rien à télécharger.")
            return
        go.setEnabled(False)
        log.setPlainText("Téléchargement en cours…")
        w = _Worker(jobs, ri.OUT_ROOT / pid, dlg)
        state["w"] = w
        w.done.connect(_done)
        w.start()

    def _done(records):
        go.setEnabled(True)
        crystal = None
        if cr:
            crystal = {"pdb": cr["pdb"], "ligand": cr["cle"], "role": (
                "inhibiteur de référence" if role == "inhibiteur"
                else "substrat de référence" if role.startswith("substrat")
                else "ligand de référence (rôle inconnu)"), "verifie": verified}
        f = ri.save_registry(pid, fam, crystal, records)
        lines = []
        for r in records:
            if "erreur" in r:
                lines.append(f"✖ {r['nom']} : {r['erreur']}")
            else:
                lines.append(f"✔ {r['nom']} : {r['source']}, {r['dimension']}"
                             + (f", CID {r['cid']}" if r.get("cid") else "") + f" ({r['date']})")
        lines.append(f"\nRegistre : {f}\nSDF dans : {Path(f).parent}")
        log.setPlainText("\n".join(lines))

    go.clicked.connect(lambda _=False: _start())
    dlg.exec()
