# -*- coding: utf-8 -*-
"""Dialogue « Molécules de référence » : inhibiteurs, substrats, dérépresseurs
et ligands du cristal d'une cible (téléchargement PubChem ou import d'un fichier)."""
import datetime
import html
import json
import shutil
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout)
from src import reference_inhibitors as ri

_PID = {"MexB": "mexb_paeruginosa", "MexR": "mexr_paeruginosa"}

# (libellé affiché, rôle enregistré pour une molécule ajoutée par l'utilisateur)
ROLES = [
    ("Inhibiteur de référence", "inhibiteur (ajout utilisateur, non vérifié)"),
    ("Substrat de référence", "substrat de référence (ajout utilisateur)"),
    ("Dérépresseur de référence (seuil de risque)",
     "dérépresseur de référence (ajout utilisateur)"),
]


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


def _targets(host):
    """Cibles uniques du menu de docking : (texte, donnee, id de profil)."""
    combo = host.target_combo
    out, seen = [], set()
    for i in range(combo.count()):
        d = combo.itemData(i)
        t = combo.itemText(i)
        if not isinstance(d, str) or "+" in t:
            continue
        pid = _PID.get(d, d)
        if pid in seen:
            continue
        seen.add(pid)
        out.append((t.strip(), d, pid))
    return out


def _registered(pid):
    f = ri.OUT_ROOT / pid / "references.json"
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return [], None
    return d.get("references", []), d.get("ligand_cristal")


def _clear(layout):
    while layout.count():
        it = layout.takeAt(0)
        w = it.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()


def _import_local(path, name, role, fam, pid):
    """Copie un fichier de molécule dans le dossier des références et fabrique son enregistrement."""
    src = Path(path)
    dest_dir = ri.OUT_ROOT / pid
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / (ri._slug(name) + src.suffix.lower())
    shutil.copy2(str(src), str(dest))
    dim = "3D"
    if src.suffix.lower() in (".sdf", ".mol"):
        dim = "2D"
        try:
            from rdkit import Chem
            m = next((x for x in Chem.SDMolSupplier(str(dest), removeHs=False)
                      if x is not None), None)
            if m is not None and m.GetNumConformers():
                dim = "3D" if m.GetConformer().Is3D() else "2D"
        except Exception:
            dim = "2D"
    return {"nom": name, "role": role, "refs": [], "verifie": False,
            "pompes": [fam] if fam else None, "source_info": None,
            "fichier": str(dest), "source": "fichier local : " + src.name,
            "url": None, "dimension": dim, "cid": None,
            "date": datetime.datetime.now().isoformat(timespec="seconds")}


def build_dialog(host):
    targets = _targets(host)
    if not targets:
        return None
    cat = ri.load_catalog()
    st = {"boxes": [], "file": None, "worker": None, "local": [], "job": None}

    dlg = QDialog(host)
    dlg.setWindowTitle("Molécules de référence")
    dlg.resize(820, 700)
    lay = QVBoxLayout(dlg)

    intro = QLabel(
        "Choisis la cible, puis ajoute ses molécules de référence : inhibiteurs, substrats "
        "ou dérépresseurs (la molécule qui libère le répresseur, par exemple la pyocyanine "
        "pour MexR). Le rôle choisi décide de son usage dans l'analyse.")
    intro.setWordWrap(True)
    lay.addWidget(intro)

    tcombo = QComboBox()
    for t, d, p in targets:
        tcombo.addItem(t, (d, p))
    cur = host.target_combo.currentData()
    for i in range(tcombo.count()):
        if tcombo.itemData(i)[0] == cur:
            tcombo.setCurrentIndex(i)
            break
    lay.addWidget(tcombo)

    info = QLabel()
    info.setTextFormat(Qt.RichText)
    info.setWordWrap(True)
    lay.addWidget(info)

    box_area = QVBoxLayout()
    lay.addLayout(box_area)

    lay.addWidget(QLabel("Ajouter une molécule :"))
    row = QHBoxLayout()
    name_edit = QLineEdit()
    name_edit.setPlaceholderText("Nom PubChem (ex. pyocyanin), ou nom à donner à ton fichier")
    role_combo = QComboBox()
    for label, _r in ROLES:
        role_combo.addItem(label)
    row.addWidget(name_edit, 2)
    row.addWidget(role_combo, 2)
    lay.addLayout(row)

    frow = QHBoxLayout()
    file_btn = QPushButton("Importer un fichier (SDF, MOL, MOL2, PDB)…")
    file_lbl = QLabel("Aucun fichier choisi")
    frow.addWidget(file_btn)
    frow.addWidget(file_lbl, 1)
    lay.addLayout(frow)

    log = QPlainTextEdit()
    log.setReadOnly(True)
    lay.addWidget(log, 1)
    btns = QHBoxLayout()
    go = QPushButton("Enregistrer")
    close = QPushButton("Fermer")
    btns.addWidget(go)
    btns.addStretch(1)
    btns.addWidget(close)
    lay.addLayout(btns)
    close.clicked.connect(dlg.accept)

    def _rebuild():
        data = tcombo.currentData()
        if not data:
            return
        d, pid = data
        fam = ri.family_of(f"{d} {tcombo.currentText()}")
        cr = _crystal(pid)
        role, entry, verified = ("inconnu", None, False)
        if cr:
            role, entry, verified = ri.classify_crystal(cat, cr["pdb"], cr["ligand"])
        crystal_compound = entry if role == "inhibiteur" else None
        picks, _missing = ri.propose(cat, fam, crystal_compound) if fam else ([], 0)
        st.update(pid=pid, fam=fam, cr=cr, role=role, verified=verified)

        lines = ["Cible : <b>%s</b>" % html.escape(str(fam or tcombo.currentText()))]
        if cr:
            lines.append("Ligand du cristal : %s (%s) → rôle : <b>%s</b>%s" % (
                html.escape(str(cr["ligand"])), html.escape(str(cr["pdb"] or "PDB inconnu")),
                html.escape(str(role)),
                "" if verified or role == "inconnu" else " (à confirmer)"))
        else:
            lines.append("Aucun ligand du cristal enregistré (lance « Vérifier ma "
                         "configuration » pour en définir un).")
        regs, _c = _registered(pid)
        if regs:
            lines.append("Molécules enregistrées pour cette cible :")
            for r in regs:
                lines.append("&nbsp;&nbsp;• <b>%s</b> : %s" % (
                    html.escape(str(r.get("nom"))), html.escape(str(r.get("role")))))
        else:
            lines.append("Aucune molécule de référence enregistrée pour cette cible.")
        info.setText("<br>".join(lines))

        _clear(box_area)
        st["boxes"] = []
        if picks:
            box_area.addWidget(QLabel("Inhibiteurs documentés (liste vérifiée) :"))
            for c in picks:
                cb = QCheckBox(f"{c['nom']}   [{', '.join(c['refs'])}]")
                cb.setChecked(False)
                box_area.addWidget(cb)
                st["boxes"].append((cb, c))
        elif fam is None:
            box_area.addWidget(QLabel(
                "Pas de liste vérifiée pour cette cible : ajoute tes molécules ci-dessous."))

    def _pick_file():
        p, _ = QFileDialog.getOpenFileName(
            dlg, "Importer une molécule de référence", "",
            "Molécules (*.sdf *.mol *.mol2 *.pdb)")
        if p:
            st["file"] = p
            file_lbl.setText(Path(p).name)

    def _start():
        pid, fam = st["pid"], st["fam"]
        role_value = ROLES[role_combo.currentIndex()][1]
        jobs, local = [], []
        for cb, c in st["boxes"]:
            if cb.isChecked():
                jobs.append({"nom": c["nom"], "role": "inhibiteur de référence",
                             "pdb": c.get("pdb", []),
                             "queries": ri.QUERIES.get(c["nom"], [c["nom"]]),
                             "refs": c["refs"], "verifie": c.get("verifie", False),
                             "pompes": c.get("pompes")})
        n = name_edit.text().strip()
        if st["file"]:
            try:
                local.append(_import_local(st["file"], n or Path(st["file"]).stem,
                                           role_value, fam, pid))
            except Exception as exc:
                log.setPlainText(f"✖ import du fichier impossible : {exc}")
                return
        elif n:
            jobs.append({"nom": n, "role": role_value, "pdb": [], "queries": [n],
                         "refs": [], "verifie": False, "pompes": [fam] if fam else None})
        if not jobs and not local:
            log.setPlainText("Rien à enregistrer : coche un inhibiteur, saisis un nom "
                             "ou importe un fichier.")
            return
        st["local"] = local
        st["job"] = (pid, fam, st.get("cr"), st.get("role", "inconnu"), st.get("verified", False))
        if not jobs:
            _done([])
            return
        go.setEnabled(False)
        log.setPlainText("Téléchargement en cours…")
        w = _Worker(jobs, ri.OUT_ROOT / pid, dlg)
        st["worker"] = w
        w.done.connect(_done)
        w.start()

    def _done(records):
        go.setEnabled(True)
        pid, fam, cr, role, verified = st["job"]
        records = list(st.get("local", [])) + list(records)
        crystal = None
        if cr:
            crystal = {"pdb": cr["pdb"], "ligand": cr["cle"], "role": (
                "inhibiteur de référence" if role == "inhibiteur"
                else "substrat de référence" if role.startswith("substrat")
                else "ligand de référence (rôle inconnu)"), "verifie": verified}
        else:
            try:
                old = json.loads((ri.OUT_ROOT / pid / "references.json").read_text(
                    encoding="utf-8"))
                crystal = old.get("ligand_cristal")
            except Exception:
                crystal = None
        f = ri.save_registry(pid, fam, crystal, records)
        lines = []
        for r in records:
            if "erreur" in r:
                lines.append(f"✖ {r['nom']} : {r['erreur']}")
            else:
                lines.append(f"✔ {r['nom']} : {r['source']}, {r['dimension']}"
                             + (f", CID {r['cid']}" if r.get("cid") else "")
                             + f" ({r['date']})")
        lines.append(f"\nRegistre : {f}\nFichiers dans : {Path(f).parent}")
        st["file"] = None
        st["local"] = []
        file_lbl.setText("Aucun fichier choisi")
        name_edit.clear()
        _rebuild()
        log.setPlainText("\n".join(lines))

    file_btn.clicked.connect(lambda _=False: _pick_file())
    go.clicked.connect(lambda _=False: _start())
    tcombo.currentIndexChanged.connect(lambda _=0: _rebuild())
    st["keep"] = (dlg, _rebuild, _start, _done, _pick_file)
    _rebuild()
    return dlg


def open_dialog(host):
    dlg = build_dialog(host)
    if dlg is None:
        QMessageBox.information(host, "Molécules de référence", "Aucune cible disponible.")
        return
    dlg.exec()
