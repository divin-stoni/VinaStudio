#!/usr/bin/env python3
"""
patch16_phytomolecules_tab.py

Ajoute l'onglet "Phytomolecules" a VinaStudio, en un seul passage :
  1. Sauvegarde complete du projet dans _archive_backups/<horodatage>/
  2. Cree src/phyto_api.py (GBIF + LOTUS/Wikidata + PubChem)
  3. Cree src/gui/phyto_page.py (le nouvel onglet, sur le pattern de
     credits_page.py : QThread pour le reseau, lang_mgr.t() defensif,
     reutilise src/docking/sdf_preparer.py::_split_sdf)
  4. Patche src/gui/main_window.py :
       - import de PhytoPage
       - instanciation + ajout au workspace, juste avant CreditsPage
       - nettoyage a la fermeture (shutdown), meme bloc try/except que
         Credits
       - tentative automatique d'ajout du bouton d'onglet horizontal
         (TopTab) ; si le bloc ne peut pas etre identifie sans ambiguite,
         cette seule etape est sautee et le script l'indique clairement
         a la fin (rien d'autre n'est perdu)
  5. Verifie que chaque fichier modifie compile ; restaure depuis la
     sauvegarde en cas d'echec de compilation
  6. Idempotent : si deja applique, le relancer ne fait rien de plus

Usage :
    python3 patch16_phytomolecules_tab.py [chemin_racine_projet]
"""

import datetime
import py_compile
import re
import shutil
import sys
from pathlib import Path

DEFAULT_CANDIDATES = [Path.home() / "MexAB_MexR_Analyzer_BETA", Path.cwd()]

MARKER = "# --- patch16 phytomolecules tab ---"

# ---------------------------------------------------------------------------
# Contenu des nouveaux fichiers (delimiteur exterieur : ''' ; les docstrings
# internes utilisent """ pour ne jamais entrer en collision)
# ---------------------------------------------------------------------------

PHYTO_API_CONTENT = '''"""
phyto_api.py
# --- patch16 phytomolecules tab ---

Appels reseau pour l'onglet Phytomolecules :
- GBIF : confirmation du nom scientifique d'une plante + photo de reference
- LOTUS (donnees hebergees sur Wikidata) : molecules naturelles d'une
  espece, regroupees par famille chimique
- PubChem PUG REST : recherche de molecules organiques non phytochimiques
  par nom, et telechargement groupe de SDF par lot de CID

Suit le pattern deja utilise par src/fetch_mw_logp.py (requests + BASE_URL).

NOTE : la couverture LOTUS/Wikidata est heterogene selon les especes et la
classification chimique est parfois absente pour certains composes -- a
valider sur des cas reels une fois l'onglet teste dans l'app.
"""

import time
from pathlib import Path
from urllib.parse import quote

import requests

GBIF_MATCH_URL = "https://api.gbif.org/v1/species/match"
GBIF_OCCURRENCE_URL = "https://api.gbif.org/v1/occurrence/search"
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
PUBCHEM_CID_BY_NAME_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/cids/JSON"
PUBCHEM_SDF_BATCH_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cids}/SDF"

REQUEST_TIMEOUT = 20


def gbif_match_species(name):
    """Confirme le nom scientifique d'une plante via GBIF (premiere
    verification : le nom ; la seconde verification est la photo,
    recuperee ensuite par gbif_reference_image)."""
    resp = requests.get(GBIF_MATCH_URL, params={"name": name, "kingdom": "Plantae"},
                         timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if data.get("matchType") == "NONE" or "usageKey" not in data:
        raise ValueError("Aucune correspondance GBIF fiable pour '" + name + "'.")
    return data


def gbif_reference_image(usage_key):
    """Cherche une photo de reference via l'API occurrence GBIF. None si rien trouve."""
    resp = requests.get(GBIF_OCCURRENCE_URL, params={
        "taxonKey": usage_key, "mediaType": "StillImage", "limit": 5,
    }, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    for r in resp.json().get("results", []):
        for media in r.get("media", []):
            url = media.get("identifier")
            if url:
                return url
    return None


def lotus_compounds_for_species(scientific_name):
    """Molecules naturelles rapportees chez une espece, via Wikidata (LOTUS)."""
    query = (
        "SELECT ?compound ?compoundLabel ?cid ?classLabel WHERE {\\n"
        + '  ?taxon rdfs:label "' + scientific_name + '"@en.\\n'
        + "  ?compound wdt:P703 ?taxon.\\n"
        + "  OPTIONAL { ?compound wdt:P662 ?cid. }\\n"
        + "  OPTIONAL { ?compound wdt:P31 ?class. }\\n"
        + '  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }\\n'
        + "}\\n"
        + "LIMIT 500"
    )
    resp = requests.get(WIKIDATA_SPARQL_URL, params={"query": query, "format": "json"},
                         headers={"Accept": "application/sparql-results+json"},
                         timeout=REQUEST_TIMEOUT * 2)
    resp.raise_for_status()
    bindings = resp.json().get("results", {}).get("bindings", [])
    out = []
    for b in bindings:
        out.append({
            "name": b.get("compoundLabel", {}).get("value", "?"),
            "pubchem_cid": b.get("cid", {}).get("value"),
            "chemical_class": b.get("classLabel", {}).get("value", "Non classe"),
        })
    return out


def group_by_family(compounds):
    families = {}
    for c in compounds:
        fam = c.get("chemical_class") or "Non classe"
        families.setdefault(fam, []).append(c)
    return families


def pubchem_search_by_name(name):
    """Mode 'Autres molecules organiques' : recherche directe PubChem par nom."""
    url = PUBCHEM_CID_BY_NAME_URL.format(name=quote(name))
    resp = requests.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json().get("IdentifierList", {}).get("CID", [])


def pubchem_download_sdf_batch(cids, out_file, batch_size=100):
    """Telecharge en lot les SDF PubChem et les concatene dans out_file,
    pret pour extraction via src/docking/sdf_preparer.py::_split_sdf."""
    out_file = Path(out_file)
    with out_file.open("w", encoding="utf-8") as fh:
        for i in range(0, len(cids), batch_size):
            batch = cids[i:i + batch_size]
            url = PUBCHEM_SDF_BATCH_URL.format(cids=",".join(str(c) for c in batch))
            resp = requests.get(url, timeout=REQUEST_TIMEOUT * 3)
            resp.raise_for_status()
            fh.write(resp.text)
            time.sleep(0.3)
    return out_file
'''

PHYTO_PAGE_CONTENT = '''"""
phyto_page.py
# --- patch16 phytomolecules tab ---

Onglet "Phytomolecules" de VinaStudio.
Pattern suivi : credits_page.py (QWidget autonome, reseau en arriere-plan
via QThread, styles herites de l'app, traductions via lang_mgr.t() avec
repli defensif comme le patch12).
"""

import inspect
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QTreeWidget, QTreeWidgetItem, QMessageBox, QFileDialog, QStackedWidget,
)

from src import phyto_api
from src.docking.sdf_preparer import _split_sdf

LIGAND_DIR = Path("docking/ligands/prepared")


def _t_resolve(lang_mgr, key, fallback):
    try:
        text = lang_mgr.t(key)
    except Exception:
        text = ""
    if not text or text == key:
        return fallback
    return text


class _NetworkWorker(QThread):
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.finished_ok.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class PhytoPage(QWidget):
    def __init__(self, lang_mgr=None, parent=None):
        super().__init__(parent)
        self.lang_mgr = lang_mgr
        self._current_families = {}
        self._workers = []
        self._build_ui()

    def _t(self, key, fallback):
        if self.lang_mgr is None:
            return fallback
        return _t_resolve(self.lang_mgr, key, fallback)

    def _build_ui(self):
        root = QVBoxLayout(self)

        mode_row = QHBoxLayout()
        self.btn_mode_phyto = QPushButton(self._t("phyto_mode_plant", "Phytomolecules"))
        self.btn_mode_other = QPushButton(self._t("phyto_mode_other", "Autres molecules organiques"))
        self.btn_mode_phyto.setObjectName("PrimaryButton")
        self.btn_mode_phyto.setCheckable(True)
        self.btn_mode_other.setCheckable(True)
        self.btn_mode_phyto.setChecked(True)
        self.btn_mode_phyto.clicked.connect(lambda: self._switch_mode(0))
        self.btn_mode_other.clicked.connect(lambda: self._switch_mode(1))
        mode_row.addWidget(self.btn_mode_phyto)
        mode_row.addWidget(self.btn_mode_other)
        mode_row.addStretch(1)
        root.addLayout(mode_row)

        self.stack = QStackedWidget()
        root.addWidget(self.stack)
        self.stack.addWidget(self._build_plant_panel())
        self.stack.addWidget(self._build_other_panel())

    def _switch_mode(self, index):
        self.btn_mode_phyto.setChecked(index == 0)
        self.btn_mode_other.setChecked(index == 1)
        self.stack.setCurrentIndex(index)

    def _build_plant_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        search_row = QHBoxLayout()
        self.plant_input = QLineEdit()
        self.plant_input.setPlaceholderText(self._t("phyto_plant_placeholder", "Nom de la plante..."))
        self.btn_search_plant = QPushButton(self._t("phyto_search_btn", "Rechercher"))
        self.btn_search_plant.setObjectName("PrimaryButton")
        self.btn_search_plant.clicked.connect(self._on_search_plant)
        search_row.addWidget(self.plant_input)
        search_row.addWidget(self.btn_search_plant)
        layout.addLayout(search_row)

        verif_row = QHBoxLayout()
        self.plant_image_label = QLabel()
        self.plant_image_label.setFixedSize(160, 160)
        self.plant_image_label.setAlignment(Qt.AlignCenter)
        self.plant_image_label.setStyleSheet("border: 1px solid rgba(255,255,255,60);")
        self.plant_name_label = QLabel(self._t("phyto_no_plant", "Aucune plante confirmee."))
        verif_row.addWidget(self.plant_image_label)
        verif_row.addWidget(self.plant_name_label, 1)
        layout.addLayout(verif_row)

        self.family_tree = QTreeWidget()
        self.family_tree.setHeaderLabels([
            self._t("phyto_col_family", "Famille chimique"),
            self._t("phyto_col_cid", "CID PubChem"),
        ])
        layout.addWidget(self.family_tree, 1)
        self.family_tree.itemSelectionChanged.connect(self._on_family_selection_changed)

        self.btn_download_family = QPushButton(
            self._t("phyto_download_family", "Telecharger cette famille depuis PubChem"))
        self.btn_download_family.setObjectName("PrimaryButton")
        self.btn_download_family.clicked.connect(self._on_download_selected_family)
        self.btn_download_family.setEnabled(False)
        layout.addWidget(self.btn_download_family)

        return panel

    def _build_other_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        row = QHBoxLayout()
        self.other_input = QLineEdit()
        self.other_input.setPlaceholderText(
            self._t("phyto_other_placeholder", "Nom de la molecule (medicament, compose organique)..."))
        self.btn_search_other = QPushButton(self._t("phyto_search_btn", "Rechercher"))
        self.btn_search_other.setObjectName("PrimaryButton")
        self.btn_search_other.clicked.connect(self._on_search_other)
        row.addWidget(self.other_input)
        row.addWidget(self.btn_search_other)
        layout.addLayout(row)
        self.other_result_label = QLabel("")
        layout.addWidget(self.other_result_label)
        layout.addStretch(1)
        return panel

    def _run_async(self, fn, on_ok, *args, **kwargs):
        worker = _NetworkWorker(fn, *args, **kwargs)
        worker.finished_ok.connect(on_ok)
        worker.failed.connect(self._on_network_error)
        self._workers.append(worker)
        worker.start()

    def _on_network_error(self, message):
        QMessageBox.warning(self, self._t("phyto_error_title", "Erreur reseau"), message)

    def _on_search_plant(self):
        name = self.plant_input.text().strip()
        if not name:
            return
        self.plant_name_label.setText(self._t("phyto_searching", "Recherche en cours..."))
        self._run_async(phyto_api.gbif_match_species, self._on_gbif_matched, name)

    def _on_gbif_matched(self, match):
        canonical = match.get("canonicalName") or match.get("scientificName") or "?"
        self.plant_name_label.setText(self._t("phyto_confirmed_prefix", "Confirme : ") + canonical)
        usage_key = match.get("usageKey")
        if usage_key:
            self._run_async(phyto_api.gbif_reference_image, self._on_gbif_image, usage_key)
        self._run_async(phyto_api.lotus_compounds_for_species, self._on_lotus_compounds, canonical)

    def _on_gbif_image(self, url):
        if not url:
            return
        try:
            import requests
            data = requests.get(url, timeout=15).content
            pix = QPixmap()
            pix.loadFromData(data)
            self.plant_image_label.setPixmap(
                pix.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            pass

    def _on_lotus_compounds(self, compounds):
        self._current_families = phyto_api.group_by_family(compounds)
        self.family_tree.clear()
        for family, mols in self._current_families.items():
            fam_item = QTreeWidgetItem([family + " (" + str(len(mols)) + ")", ""])
            for m in mols:
                QTreeWidgetItem(fam_item, [m.get("name", "?"), str(m.get("pubchem_cid") or "")])
            self.family_tree.addTopLevelItem(fam_item)
        self.family_tree.expandAll()

    def _on_family_selection_changed(self):
        items = self.family_tree.selectedItems()
        self.btn_download_family.setEnabled(bool(items) and items[0].parent() is None)

    def _on_download_selected_family(self):
        items = self.family_tree.selectedItems()
        if not items or items[0].parent() is not None:
            return
        family_label = items[0].text(0)
        family_name = family_label.rsplit(" (", 1)[0]
        mols = self._current_families.get(family_name, [])
        cids = [int(m["pubchem_cid"]) for m in mols if m.get("pubchem_cid")]
        if not cids:
            QMessageBox.information(
                self, self._t("phyto_info_title", "Information"),
                self._t("phyto_no_cid", "Aucun CID PubChem disponible pour cette famille."))
            return
        chosen = QFileDialog.getExistingDirectory(
            self, self._t("phyto_choose_dir", "Dossier de destination"), str(LIGAND_DIR))
        if not chosen:
            return
        out_dir = Path(chosen)
        out_file = out_dir / (family_name.replace(" ", "_") + "_batch.sdf")
        self._run_async(
            phyto_api.pubchem_download_sdf_batch,
            lambda path: self._on_family_downloaded(path, out_dir),
            cids, out_file,
        )

    def _on_family_downloaded(self, sdf_path, out_dir):
        try:
            sig = inspect.signature(_split_sdf)
            kwargs = {}
            if "sdf_path" in sig.parameters:
                kwargs["sdf_path"] = sdf_path
            if "work_dir" in sig.parameters:
                kwargs["work_dir"] = out_dir
            _split_sdf(**kwargs)
            QMessageBox.information(
                self, self._t("phyto_done_title", "Termine"),
                self._t("phyto_done_msg", "Famille telechargee et extraite dans le dossier ligand."))
        except TypeError as exc:
            QMessageBox.warning(
                self, self._t("phyto_error_title", "Erreur"),
                "Signature de _split_sdf inattendue (" + str(exc) + "). "
                "Fichier SDF groupe disponible ici : " + str(sdf_path))

    def _on_search_other(self):
        name = self.other_input.text().strip()
        if not name:
            return
        self.other_result_label.setText(self._t("phyto_searching", "Recherche en cours..."))
        self._run_async(phyto_api.pubchem_search_by_name, self._on_other_found, name)

    def _on_other_found(self, cids):
        if not cids:
            self.other_result_label.setText(self._t("phyto_no_result", "Aucun resultat."))
            return
        self.other_result_label.setText(
            self._t("phyto_cids_found", "CID PubChem trouves : ")
            + ", ".join(str(c) for c in cids))

    def shutdown(self):
        for w in self._workers:
            if w.isRunning():
                w.wait(500)
'''


def backup_project(root):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = root / "_archive_backups" / ts / "pre_patch16"
    dest.mkdir(parents=True, exist_ok=True)
    src_dir = root / "src"
    if src_dir.exists():
        shutil.copytree(src_dir, dest / "src", dirs_exist_ok=True)
    print("[OK] Sauvegarde de src/ effectuee dans " + str(dest))
    return dest


def compile_or_restore(path, backup_copy, project_root):
    try:
        py_compile.compile(str(path), doraise=True)
        print("[OK] Compile : " + str(path.relative_to(project_root)))
    except py_compile.PyCompileError as exc:
        print("[ERREUR] Echec de compilation sur " + str(path) + " : " + str(exc))
        if backup_copy.exists():
            shutil.copy2(backup_copy, path)
            print("[RESTAURE] " + str(path) + " remis dans son etat d'avant patch.")
        sys.exit(1)


def find_project_root(arg):
    if arg:
        p = Path(arg).expanduser()
        if p.exists():
            return p
        print("[!] Chemin fourni introuvable : " + str(p), file=sys.stderr)
        sys.exit(1)
    for cand in DEFAULT_CANDIDATES:
        if (cand / "src").exists():
            return cand
    print("[!] Projet introuvable automatiquement, donne le chemin en argument.", file=sys.stderr)
    sys.exit(1)


def patch_main_window(main_window_path):
    report = []
    text = main_window_path.read_text(encoding="utf-8")

    if MARKER in text or "PhytoPage" in text:
        report.append("main_window.py deja patche (marqueur present) -> rien refait.")
        return report

    original = text

    import_anchor = "from src.gui.credits_page import CreditsPage"
    if import_anchor in text:
        text = text.replace(
            import_anchor,
            import_anchor + "\nfrom src.gui.phyto_page import PhytoPage  " + MARKER,
            1,
        )
        report.append("Import de PhytoPage ajoute.")
    else:
        report.append("ECHEC : ligne d'import de CreditsPage introuvable, import PhytoPage NON ajoute.")

    inst_pattern = re.compile(
        r"(self\.credits_page\s*=\s*CreditsPage\(\)\s*\n\s*\n\s*self\.workspace\.addWidget\(\s*self\.credits_page\s*\))"
    )
    m = inst_pattern.search(text)
    if m:
        replacement = (
            "self.phyto_page = PhytoPage(lang_mgr=self.lang_mgr)\n\n"
            "        self.workspace.addWidget(self.phyto_page)\n\n        "
            + m.group(1)
        )
        text = text[:m.start()] + replacement + text[m.end():]
        report.append("Instanciation + ajout au workspace de PhytoPage effectues (juste avant CreditsPage).")
    else:
        report.append(
            "ECHEC : bloc 'self.credits_page = CreditsPage() / self.workspace.addWidget(...)' "
            "non trouve sous la forme exacte attendue -> instanciation PhytoPage NON ajoutee. "
            "A faire a la main : dupliquer ces 2 lignes pour phyto_page, juste avant."
        )

    shutdown_anchor = (
        '                if hasattr(self, "credits_page"):\n'
        '                    self.credits_page.shutdown()'
    )
    if shutdown_anchor in text:
        text = text.replace(
            shutdown_anchor,
            shutdown_anchor + '\n                if hasattr(self, "phyto_page"):\n'
                              '                    self.phyto_page.shutdown()',
            1,
        )
        report.append("Nettoyage a la fermeture (shutdown) ajoute pour phyto_page.")
    else:
        report.append("ECHEC : bloc de shutdown de credits_page introuvable -> shutdown phyto_page NON ajoute.")

    toolbar_match = re.search(r"def create_toolbar\(.*?\n(?=    def |\Z)", text, re.DOTALL)
    if toolbar_match:
        block = toolbar_match.group(0)
        credit_hits = [ln for ln in block.splitlines() if re.search(r"credit", ln, re.IGNORECASE)]
        if len(credit_hits) == 0:
            report.append(
                "Bouton TopTab 'Phytomolecules' NON ajoute automatiquement : aucune reference a "
                "Credits/credits trouvee dans create_toolbar() (l'onglet Credits n'est peut-etre pas "
                "un TopTab dans ta version -> a verifier/ajouter a la main)."
            )
        else:
            report.append(
                "Bouton TopTab 'Phytomolecules' NON ajoute automatiquement par prudence "
                "(create_toolbar() contient " + str(len(credit_hits)) + " ligne(s) mentionnant 'credit', "
                "pas assez univoque pour dupliquer le bloc sans risque). "
                "Lignes concernees, a dupliquer/adapter a la main pour Phytomolecules :\n    "
                + "\n    ".join(l.strip() for l in credit_hits)
            )
    else:
        report.append("ECHEC : fonction create_toolbar() introuvable -> bouton TopTab NON ajoute.")

    if text != original:
        main_window_path.write_text(text, encoding="utf-8")

    return report


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    root = find_project_root(arg)
    src = root / "src"

    backup_dir = backup_project(root)

    phyto_api_path = src / "phyto_api.py"
    phyto_page_path = src / "gui" / "phyto_page.py"
    main_window_path = src / "gui" / "main_window.py"

    if not phyto_api_path.exists():
        phyto_api_path.write_text(PHYTO_API_CONTENT, encoding="utf-8")
        print("[OK] Cree : " + str(phyto_api_path))
    else:
        print("[SKIP] " + str(phyto_api_path) + " existe deja, non ecrase.")

    if not phyto_page_path.exists():
        phyto_page_path.write_text(PHYTO_PAGE_CONTENT, encoding="utf-8")
        print("[OK] Cree : " + str(phyto_page_path))
    else:
        print("[SKIP] " + str(phyto_page_path) + " existe deja, non ecrase.")

    mw_backup_copy = backup_dir / "src" / "gui" / "main_window.py"
    report = patch_main_window(main_window_path)

    compile_or_restore(phyto_api_path, phyto_api_path, root)
    compile_or_restore(phyto_page_path, phyto_page_path, root)
    compile_or_restore(main_window_path, mw_backup_copy, root)

    print("")
    print("=" * 78)
    print("RAPPORT PATCH16 - Onglet Phytomolecules")
    print("=" * 78)
    for line in report:
        print("- " + line)
    print("=" * 78)
    print("Fichiers crees : src/phyto_api.py, src/gui/phyto_page.py")
    print("Prochaine etape reelle : lancer l'app et verifier l'onglet/le bouton.")


if __name__ == "__main__":
    main()
