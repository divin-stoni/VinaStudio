# -*- coding: utf-8 -*-
"""Ajoute les molecules de reference au lot de docking, avec leur role."""
import datetime
import json
import re
import shutil
import subprocess
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
from src import reference_inhibitors as ri, guide_assistant

LABELS = {
    "INH": "inhibiteur de référence",
    "INH-USER": "inhibiteur ajouté par l'utilisateur (non vérifié)",
    "SUB": "substrat de référence",
    "CRISTAL-INH": "ligand du cristal, inhibiteur de référence",
    "CRISTAL-SUB": "ligand du cristal, substrat de référence",
    "CRISTAL-REF": "ligand du cristal, rôle inconnu",
}


def _pids(target, pair_members):
    if target == "MexB + MexR":
        return ["mexb_paeruginosa"]
    if pair_members:
        return [pair_members[0]]
    return [{"MexB": "mexb_paeruginosa", "MexR": "mexr_paeruginosa"}.get(target, target)]


def _slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")[:40] or "ref"


def _collect(pid):
    reg = ri.OUT_ROOT / pid / "references.json"
    if not reg.exists():
        return []
    d = json.loads(reg.read_text(encoding="utf-8"))
    items = []
    for r in d.get("references", []):
        f = r.get("fichier")
        if f and Path(f).exists():
            code = "INH-USER" if "utilisateur" in (r.get("role") or "") else "INH"
            items.append({"code": code, "nom": r["nom"], "src": f, "kind": "sdf", "rec": r})
    c = d.get("ligand_cristal")
    if c:
        try:
            from src.gui.validation_ui import WORK_DIR
            tag = str(c.get("ligand", "")).replace(":", "_")
            f = Path(WORK_DIR) / pid / f"{tag}_cristal.pdbqt"
            if f.exists():
                role = c.get("role") or ""
                code = ("CRISTAL-INH" if role.startswith("inhibiteur")
                        else "CRISTAL-SUB" if role.startswith("substrat") else "CRISTAL-REF")
                items.append({"code": code, "nom": str(c.get("ligand")), "src": str(f),
                              "kind": "pdbqt", "rec": c})
        except Exception:
            pass
    return items


def _obabel(sdf, out, dim):
    from src.tools.obabel_locator import resolve_obabel_executable, obabel_subprocess_env
    exe = resolve_obabel_executable()
    if exe == "obabel":
        exe = shutil.which("obabel") or exe
    cmd = [exe, str(sdf), "-O", str(out), "-p", "7.4", "--partialcharge", "gasteiger"]
    if str(dim).upper() != "3D":
        cmd.append("--gen3d")
    cp = subprocess.run(cmd, capture_output=True, text=True, env=obabel_subprocess_env(),
                        stdin=subprocess.DEVNULL, timeout=180)
    ok = cp.returncode == 0 and Path(out).exists() and Path(out).stat().st_size > 0
    return ok, cp.stderr[-200:]


def choose_references(host, target, pair_members):
    """None : pas de references, on continue. False : annule. Liste : fichiers PDBQT a ajouter."""
    pids = _pids(target, pair_members)
    items = []
    for pid in pids:
        for it in _collect(pid):
            it["pid"] = pid
            items.append(it)
    if not items:
        return None

    lines = [f"<li><b>{it['nom']}</b> : {LABELS[it['code']]}</li>" for it in items]
    redock = []
    for pid in pids:
        v = guide_assistant.load_validation(pid)
        if v:
            redock.append(f"re-docking existant ({pid}) : pose n°1 à {v.get('rmsd_top', 0):.2f} Å"
                          f", niveau {v.get('niveau', 'non évalué')}")
    box = QMessageBox(host)
    box.setWindowTitle("Molécules de référence")
    box.setTextFormat(Qt.RichText)
    box.setText(
        "Des molécules de référence existent pour cette cible. Elles seront dockées dans les "
        "mêmes conditions que tes molécules (même boîte, mêmes paramètres) :"
        f"<ul>{''.join(lines)}</ul>"
        + ("<p>" + "<br>".join(redock) + "</p>" if redock else "")
        + "<p>L'analyse <b>inclura</b> ces références et les données du re-docking. "
          "Leur rôle est écrit dans le nom du fichier (préfixe REF-).</p>")
    b_yes = box.addButton("Inclure les références", QMessageBox.AcceptRole)
    b_no = box.addButton("Docker sans références", QMessageBox.DestructiveRole)
    box.addButton("Annuler", QMessageBox.RejectRole)
    box.exec()
    clicked = box.clickedButton()
    if clicked is b_no:
        return None
    if clicked is not b_yes:
        return False

    QApplication.setOverrideCursor(Qt.WaitCursor)
    paths, roles, errors = [], {}, []
    try:
        for it in items:
            outdir = ri.OUT_ROOT / it["pid"] / "pdbqt"
            outdir.mkdir(parents=True, exist_ok=True)
            out = outdir / f"REF-{it['code']}__{_slug(it['nom'])}.pdbqt"
            if it["kind"] == "pdbqt":
                shutil.copy2(it["src"], out)
                ok, err = True, ""
            else:
                ok, err = _obabel(it["src"], out, it["rec"].get("dimension", "3D"))
            if ok:
                paths.append(str(out))
                roles[out.name] = {"role": LABELS[it["code"]], "pompe_profil": it["pid"],
                                   "source": it["rec"].get("source"), "cid": it["rec"].get("cid"),
                                   "refs": it["rec"].get("refs"), "verifie": it["rec"].get("verifie"),
                                   "dimension": it["rec"].get("dimension")}
            else:
                errors.append(f"{it['nom']} : conversion impossible ({err.strip()[:80]})")
    finally:
        QApplication.restoreOverrideCursor()

    if paths:
        f = ri.ROOT / "docking" / "results" / "roles_campagne.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({
            "date": datetime.datetime.now().isoformat(timespec="seconds"),
            "cible": target, "references": roles, "redocking": redock,
            "preparation": "Open Babel, pH 7.4, charges Gasteiger (3D généré si structure 2D)"},
            indent=2, ensure_ascii=False), encoding="utf-8")
    if errors:
        QMessageBox.warning(host, "Références non converties", "\n".join(errors))
    return paths or None
