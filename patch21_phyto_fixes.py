#!/usr/bin/env python3
"""
patch21_phyto_fixes.py  --  VinaStudio, onglet Phytomolécules

Corrige, en un seul passage :
  1. l'erreur 403 de Wikidata (User-Agent identifiable, SPARQL en POST,
     2 nouvelles tentatives sur 429/503, erreurs en français avec code HTTP) ;
  2. le faux positif « Plantae » (clé GBIF 6) : rangs supérieurs à la famille
     rejetés, LOTUS interrogé avec la clé GBIF de l'espèce confirmée,
     repli sur le genre avec message explicite ;
  3. la mise en page : image en colonne gauche sur toute la hauteur,
     tableau en colonne droite qui prend tout l'espace restant.

Fichiers modifiés : src/phyto_api.py et src/phyto_page.py (rien d'autre).

Usage (depuis la racine du projet) :
    python3 patch21_phyto_fixes.py
    python3 patch21_phyto_fixes.py --no-network     # sans le test réseau final

Sauvegarde préalable dans _archive_backups/<horodatage>_patch21/, vérification
des ancres, recompilation, restauration automatique en cas d'erreur.
Idempotent : une seconde exécution ne change rien.
"""

import importlib.util
import py_compile
import shutil
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

MARKER_NEW = "# --- patch21"
ANCHOR_OLD = "# --- patch20 :"

NEW_API = r'''"""
phyto_api.py
# --- patch16 phytomolecules tab ---
# --- patch20 : repli nom vernaculaire + requete LOTUS par ID GBIF ---
# --- patch21 : User-Agent + SPARQL en POST, filtre de rang GBIF, repli genre ---

Appels réseau pour l'onglet Phytomolécules :
- GBIF : confirmation du nom scientifique OU vernaculaire d'une plante
  (les rangs supérieurs à la famille sont toujours rejetés), + photo de référence
- LOTUS (données hébergées sur Wikidata) : molécules naturelles d'une espèce,
  regroupées par famille chimique. Interrogation par l'identifiant GBIF de
  l'espèce confirmée (wdt:P846) ; repli sur le nom, puis sur le genre.
- PubChem PUG REST : recherche de molécules organiques non phytochimiques
  par nom, et téléchargement groupé de SDF par lot de CID

Toutes les requêtes passent par _request() : User-Agent identifiable
(Wikidata renvoie 403 sans lui), nouvelles tentatives sur 429/503, messages
d'erreur en français avec le code HTTP.

Pour renseigner votre contact dans le User-Agent, définissez la variable
d'environnement VINASTUDIO_CONTACT (ex. votre e-mail) ou modifiez CONTACT.

NOTE : la couverture LOTUS/Wikidata est hétérogène selon les espèces et la
classification chimique est parfois absente pour certains composés.
"""

import os
import time
from pathlib import Path
from urllib.parse import quote

import requests

GBIF_MATCH_URL = "https://api.gbif.org/v1/species/match"
GBIF_SEARCH_URL = "https://api.gbif.org/v1/species/search"
GBIF_OCCURRENCE_URL = "https://api.gbif.org/v1/occurrence/search"
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
PUBCHEM_CID_BY_NAME_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/cids/JSON"
PUBCHEM_SDF_BATCH_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cids}/SDF"

GBIF_BACKBONE_KEY = "d7dddbf4-2cf0-4f39-9b2a-bb099caae36c"
GBIF_PLANTAE_KEY = 6

# Rangs acceptés pour confirmer une plante. Tout ce qui est plus haut que la
# famille (ordre, classe, embranchement, règne) est rejeté.
ACCEPTED_RANKS = {"SPECIES", "SUBSPECIES", "VARIETY", "GENUS", "FAMILY"}
SPECIES_LEVEL_RANKS = {"SPECIES", "SUBSPECIES", "VARIETY"}
MIN_FUZZY_CONFIDENCE = 80

REQUEST_TIMEOUT = 20
SPARQL_TIMEOUT = 60
SDF_TIMEOUT = 60
MAX_RETRIES = 2                 # 2 nouvelles tentatives après la première
RETRY_STATUS = (429, 503)
RETRY_BASE_DELAY = 2.0          # 2 s puis 4 s (attente croissante)
RETRY_MAX_DELAY = 30.0

CONTACT = os.environ.get("VINASTUDIO_CONTACT", "contact non renseigne")
USER_AGENT = ("VinaStudio/1.0 (usage academique; " + CONTACT + ") "
              "python-requests/" + requests.__version__)


# --------------------------------------------------------------------------
# Erreurs
# --------------------------------------------------------------------------

class PhytoError(Exception):
    kind = "other"


class PlantNotFound(PhytoError):
    kind = "not_found"


class PhytoNetworkError(PhytoError):
    kind = "network"

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def _http_message(service, code):
    if code == 403:
        msg = service + " a refusé la requête (HTTP 403, accès interdit)."
        if service == "Wikidata":
            msg += (" Wikidata exige un User-Agent identifiable : "
                    "définissez VINASTUDIO_CONTACT (votre e-mail).")
        return msg
    if code == 404:
        return service + " : ressource introuvable (HTTP 404)."
    if code == 429:
        return service + " : trop de requêtes (HTTP 429). Réessayez dans quelques instants."
    if 500 <= code <= 599:
        return service + " est momentanément indisponible (HTTP " + str(code) + ")."
    return service + " : erreur HTTP " + str(code) + "."


def _retry_delay(resp, attempt):
    delay = RETRY_BASE_DELAY * (2 ** attempt)
    retry_after = resp.headers.get("Retry-After")
    if retry_after:
        try:
            delay = max(delay, float(retry_after))
        except ValueError:
            pass
    return min(delay, RETRY_MAX_DELAY)


def _request(method, url, service, params=None, data=None, headers=None,
             timeout=REQUEST_TIMEOUT):
    """Requête HTTP unique pour tout le module : User-Agent, nouvelles
    tentatives sur 429/503, erreurs traduites en PhytoNetworkError (français)."""
    hdrs = {"User-Agent": USER_AGENT}
    if headers:
        hdrs.update(headers)
    total_attempts = MAX_RETRIES + 1
    for attempt in range(total_attempts):
        try:
            resp = requests.request(method, url, params=params, data=data,
                                    headers=hdrs, timeout=timeout)
        except requests.exceptions.Timeout:
            raise PhytoNetworkError(
                service + " : délai dépassé (" + str(timeout) + " s).")
        except requests.exceptions.ConnectionError:
            raise PhytoNetworkError(
                service + " : connexion impossible. Vérifiez votre accès Internet.")
        except requests.exceptions.RequestException as exc:
            raise PhytoNetworkError(service + " : erreur réseau (" + str(exc) + ").")
        if resp.status_code in RETRY_STATUS and attempt < total_attempts - 1:
            time.sleep(_retry_delay(resp, attempt))
            continue
        if resp.status_code >= 400:
            raise PhytoNetworkError(_http_message(service, resp.status_code),
                                    status=resp.status_code)
        return resp
    raise PhytoNetworkError(service + " : échec de la requête.")  # inatteignable


def _json(resp, service):
    try:
        return resp.json()
    except ValueError:
        raise PhytoNetworkError(service + " : réponse illisible (JSON invalide).")


# --------------------------------------------------------------------------
# GBIF : confirmation de la plante
# --------------------------------------------------------------------------

def _normalize_usage(d, mode):
    return {
        "canonicalName": d.get("canonicalName") or d.get("scientificName"),
        "scientificName": d.get("scientificName"),
        "usageKey": d.get("usageKey") or d.get("key"),
        "acceptedUsageKey": d.get("acceptedUsageKey"),
        "rank": d.get("rank"),
        "family": d.get("family"),
        "genus": d.get("genus"),
        "genusKey": d.get("genusKey"),
        "matchType": d.get("matchType"),
        "_lookup_mode": mode,
    }


def _is_valid_plant_match(data):
    """Vrai seulement pour une correspondance de rang famille ou inférieur.
    Rejette NONE, HIGHERRANK, le règne Plantae (clé 6) et tout rang supérieur."""
    if data.get("matchType") in (None, "NONE", "HIGHERRANK"):
        return False
    key = data.get("usageKey")
    if not key or key == GBIF_PLANTAE_KEY:
        return False
    if data.get("rank") not in ACCEPTED_RANKS:
        return False
    kingdom = data.get("kingdom")
    if kingdom and kingdom != "Plantae":
        return False
    if data.get("matchType") == "FUZZY":
        confidence = data.get("confidence")
        if confidence is not None and confidence < MIN_FUZZY_CONFIDENCE:
            return False
    return True


def _vernacular_score(result, wanted):
    for vn in result.get("vernacularNames") or []:
        if (vn.get("vernacularName") or "").strip().lower() == wanted:
            return 0
    return 1


def gbif_match_species(name):
    """Confirme le nom d'une plante via GBIF.
    1) matcher flou sur nom scientifique (tolère les fautes de frappe) ;
    2) sinon, recherche sur les noms vernaculaires (noms courants).
    Lève PlantNotFound si rien de valable (rang >= famille uniquement)."""
    name = (name or "").strip()
    if not name:
        raise PlantNotFound("Nom vide.")

    resp = _request("GET", GBIF_MATCH_URL, "GBIF",
                    params={"name": name, "kingdom": "Plantae"})
    data = _json(resp, "GBIF")
    if _is_valid_plant_match(data):
        return _normalize_usage(data, "scientific")

    resp2 = _request("GET", GBIF_SEARCH_URL, "GBIF", params={
        "q": name, "qField": "VERNACULAR", "rank": "SPECIES", "status": "ACCEPTED",
        "datasetKey": GBIF_BACKBONE_KEY, "highertaxonKey": GBIF_PLANTAE_KEY,
        "limit": 20,
    })
    results = _json(resp2, "GBIF").get("results", [])
    wanted = name.lower()
    results = sorted(results, key=lambda r: _vernacular_score(r, wanted))
    for r in results:
        key = r.get("key")
        if not key or key == GBIF_PLANTAE_KEY:
            continue
        if r.get("kingdom") != "Plantae":
            continue
        if r.get("rank") not in ACCEPTED_RANKS:
            continue
        return _normalize_usage(r, "vernacular")

    raise PlantNotFound("Aucune plante trouvée pour « " + name + " ».")


# --------------------------------------------------------------------------
# GBIF : photo de référence
# --------------------------------------------------------------------------

def gbif_reference_images(usage_key, limit=8):
    """URLs candidates de photos de référence (GBIF occurrences). Liste vide si rien."""
    resp = _request("GET", GBIF_OCCURRENCE_URL, "GBIF", params={
        "taxonKey": usage_key, "mediaType": "StillImage", "limit": limit,
    })
    urls = []
    for r in _json(resp, "GBIF").get("results", []):
        for media in r.get("media", []):
            url = media.get("identifier")
            if url and url not in urls:
                urls.append(url)
    return urls


def gbif_reference_image(usage_key):
    """Première URL de photo de référence, ou None (compatibilité)."""
    urls = gbif_reference_images(usage_key, limit=5)
    return urls[0] if urls else None


def download_image_bytes(url):
    return _request("GET", url, "Serveur d'images", timeout=REQUEST_TIMEOUT).content


def fetch_reference_image(usage_key):
    """Télécharge une photo de référence. Ne lève jamais : {'usage_key', 'data'}
    avec data=None si aucune image exploitable n'est disponible."""
    data = None
    try:
        for url in gbif_reference_images(usage_key)[:4]:
            try:
                content = download_image_bytes(url)
            except PhytoError:
                continue
            if content and len(content) > 1000:
                data = content
                break
    except PhytoError:
        data = None
    return {"usage_key": usage_key, "data": data}


# --------------------------------------------------------------------------
# LOTUS / Wikidata
# --------------------------------------------------------------------------

def _sparql_str(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def _run_sparql(query):
    """SPARQL en POST (évite les URL trop longues), Accept JSON, User-Agent."""
    resp = _request("POST", WIKIDATA_SPARQL_URL, "Wikidata",
                    data={"query": query},
                    headers={"Accept": "application/sparql-results+json"},
                    timeout=SPARQL_TIMEOUT)
    bindings = _json(resp, "Wikidata").get("results", {}).get("bindings", [])
    out, seen = [], set()
    for b in bindings:
        item = {
            "name": b.get("compoundLabel", {}).get("value", "?"),
            "pubchem_cid": b.get("cid", {}).get("value"),
            "chemical_class": b.get("classLabel", {}).get("value", "Non classé"),
        }
        sig = (item["name"], item["pubchem_cid"], item["chemical_class"])
        if sig in seen:
            continue
        seen.add(sig)
        out.append(item)
    return out


_SELECT = "SELECT DISTINCT ?compound ?compoundLabel ?cid ?classLabel WHERE {\n"
_TAIL = (
    "  OPTIONAL { ?compound wdt:P662 ?cid. }\n"
    "  OPTIONAL { ?compound wdt:P31 ?class. }\n"
    '  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }\n'
    "}\n"
    "LIMIT 500"
)


def _lotus_query_by_gbif_keys(keys):
    values = " ".join('"' + _sparql_str(k) + '"' for k in keys)
    query = (
        _SELECT
        + "  VALUES ?gbif { " + values + " }\n"
        + "  ?taxon wdt:P846 ?gbif.\n"
        + "  ?compound wdt:P703 ?taxon.\n"
        + _TAIL
    )
    return _run_sparql(query)


def _lotus_query_by_label(scientific_name):
    query = (
        _SELECT
        + '  ?taxon rdfs:label "' + _sparql_str(scientific_name) + '"@en.\n'
        + "  ?compound wdt:P703 ?taxon.\n"
        + _TAIL
    )
    return _run_sparql(query)


def _lotus_query_by_genus_key(genus_key):
    """Molécules de toutes les espèces dont le parent (P171) est le genre."""
    query = (
        _SELECT
        + '  ?genus wdt:P846 "' + _sparql_str(genus_key) + '".\n'
        + "  ?taxon wdt:P171 ?genus.\n"
        + "  ?compound wdt:P703 ?taxon.\n"
        + _TAIL
    )
    return _run_sparql(query)


def lotus_compounds_for_taxon(usage_key, scientific_name=None, accepted_key=None,
                              genus_key=None, genus_name=None, rank=None):
    """Composés LOTUS/Wikidata d'un taxon confirmé.
    1) identifiant GBIF de l'espèce (et de son nom accepté s'il diffère) ;
    2) repli par nom scientifique ;
    3) repli au niveau du genre (level='genus').
    Retourne {'usage_key', 'compounds', 'level', 'genus'}."""
    keys = []
    for k in (usage_key, accepted_key):
        if k and str(k) not in keys:
            keys.append(str(k))

    compounds, level = [], "species"
    if keys:
        compounds = _lotus_query_by_gbif_keys(keys)
    if not compounds and scientific_name:
        compounds = _lotus_query_by_label(scientific_name)

    if rank == "GENUS" and not genus_key:
        genus_key = usage_key
    if not compounds and genus_key and rank != "FAMILY":
        compounds = _lotus_query_by_genus_key(genus_key)
        if compounds:
            level = "genus"

    return {
        "usage_key": usage_key,
        "compounds": compounds,
        "level": level if compounds else "none",
        "genus": genus_name or (scientific_name if rank == "GENUS" else None),
    }


def group_by_family(compounds):
    families = {}
    for c in compounds:
        fam = c.get("chemical_class") or "Non classé"
        families.setdefault(fam, []).append(c)
    ordered = sorted(families.items(),
                     key=lambda kv: (kv[0] == "Non classé", -len(kv[1]), kv[0].lower()))
    return dict(ordered)


# --------------------------------------------------------------------------
# PubChem
# --------------------------------------------------------------------------

def pubchem_search_by_name(name):
    """Mode 'Autres molécules organiques' : recherche directe PubChem par nom.
    Liste vide si PubChem ne connaît pas ce nom (HTTP 404)."""
    url = PUBCHEM_CID_BY_NAME_URL.format(name=quote(name, safe=""))
    try:
        resp = _request("GET", url, "PubChem")
    except PhytoNetworkError as exc:
        if exc.status == 404:
            return []
        raise
    return _json(resp, "PubChem").get("IdentifierList", {}).get("CID", [])


def pubchem_download_sdf_batch(cids, out_file, batch_size=100):
    """Télécharge en lot les SDF PubChem et les concatène dans out_file,
    prêt pour extraction via src/docking/sdf_preparer.py::_split_sdf."""
    out_file = Path(out_file)
    with out_file.open("wb") as fh:
        for i in range(0, len(cids), batch_size):
            batch = cids[i:i + batch_size]
            url = PUBCHEM_SDF_BATCH_URL.format(cids=",".join(str(c) for c in batch))
            resp = _request("GET", url, "PubChem", timeout=SDF_TIMEOUT)
            fh.write(resp.content)
            if not resp.content.endswith(b"\n"):
                fh.write(b"\n")
            time.sleep(0.3)
    return out_file
'''

NEW_PAGE = r'''"""
phyto_page.py
# --- patch16 phytomolecules tab ---
# --- patch20 : image agrandie, tableau resserre, LOTUS via ID GBIF ---
# --- patch21 : mise en page 2 colonnes pleine hauteur, erreurs distinctes, repli genre ---

Onglet "Phytomolécules" de VinaStudio.
Pattern suivi : credits_page.py (QWidget autonome, réseau en arrière-plan
via QThread, styles hérités de l'app, traductions via lang_mgr.t() avec
repli défensif comme le patch12 : chaque clé a un texte français de repli).

Mise en page du panneau plante :
  colonne gauche (stretch 2) : image de la plante, sur toute la hauteur ;
  colonne droite (stretch 3) : recherche, statut, tableau (stretch 1),
  bouton de téléchargement en bas.
"""

import inspect
import re
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QRect, QRectF
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QTextOption
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QTreeWidget, QTreeWidgetItem, QMessageBox, QFileDialog, QStackedWidget,
    QHeaderView, QSizePolicy,
)

from src import phyto_api
from src.docking.sdf_preparer import _split_sdf

LIGAND_DIR = Path("docking/ligands/prepared")
FAMILY_ROLE = Qt.UserRole


def _t_resolve(lang_mgr, key, fallback):
    try:
        text = lang_mgr.t(key)
    except Exception:
        text = ""
    if not text or text == key:
        return fallback
    return text


class _NetworkWorker(QThread):
    """Exécute fn en arrière-plan. Les callbacks voyagent avec le signal et
    sont appelés par le thread principal (slot de PhytoPage), jamais ici."""
    finished_ok = Signal(object, object)       # (on_ok, résultat)
    failed = Signal(object, str, str)          # (on_fail, kind, message)

    def __init__(self, fn, on_ok, on_fail, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._on_ok = on_ok
        self._on_fail = on_fail
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
        except phyto_api.PhytoError as exc:
            self.failed.emit(self._on_fail, exc.kind, str(exc))
            return
        except Exception as exc:
            self.failed.emit(self._on_fail, "other", str(exc))
            return
        self.finished_ok.emit(self._on_ok, result)


class _CoverImage(QWidget):
    """Image qui remplit tout son rectangle (KeepAspectRatioByExpanding),
    recadrée au centre : jamais de bandes vides, quelle que soit la taille."""

    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._placeholder = placeholder
        self._cache = None
        self._cache_size = None
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMinimumSize(120, 120)

    def set_image(self, pixmap):
        self._pixmap = pixmap if (pixmap is not None and not pixmap.isNull()) else None
        self._cache = None
        self.update()

    def set_placeholder(self, text):
        self._placeholder = text
        self._pixmap = None
        self._cache = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        rect = self.rect()
        if self._pixmap is not None:
            if self._cache is None or self._cache_size != rect.size():
                self._cache = self._pixmap.scaled(
                    rect.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                self._cache_size = rect.size()
            sx = (self._cache.width() - rect.width()) // 2
            sy = (self._cache.height() - rect.height()) // 2
            painter.drawPixmap(rect, self._cache, QRect(sx, sy, rect.width(), rect.height()))
        else:
            painter.setPen(QColor(255, 255, 255, 140))
            option = QTextOption(Qt.AlignCenter)
            option.setWrapMode(QTextOption.WordWrap)
            painter.drawText(QRectF(rect.adjusted(12, 12, -12, -12)), self._placeholder, option)
        painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
        painter.end()


class PhytoPage(QWidget):
    def __init__(self, lang_mgr=None, parent=None):
        super().__init__(parent)
        self.lang_mgr = lang_mgr
        self._current_families = {}
        self._current_usage_key = None
        self._status_base = ""
        self._workers = []
        self._build_ui()

    def _t(self, key, fallback):
        if self.lang_mgr is None:
            return fallback
        return _t_resolve(self.lang_mgr, key, fallback)

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        root = QVBoxLayout(self)

        mode_row = QHBoxLayout()
        self.btn_mode_phyto = QPushButton(self._t("phyto_mode_plant", "Phytomolécules"))
        self.btn_mode_other = QPushButton(self._t("phyto_mode_other", "Autres molécules organiques"))
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
        root.addWidget(self.stack, 1)
        self.stack.addWidget(self._build_plant_panel())
        self.stack.addWidget(self._build_other_panel())

    def _switch_mode(self, index):
        self.btn_mode_phyto.setChecked(index == 0)
        self.btn_mode_other.setChecked(index == 1)
        self.stack.setCurrentIndex(index)

    def _build_plant_panel(self):
        panel = QWidget()
        outer = QHBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)

        # --- colonne gauche : image, toute la hauteur -------------------
        self.plant_image = _CoverImage(self._t("phyto_no_image_yet", "Aucune image."))
        outer.addWidget(self.plant_image, 2)

        # --- colonne droite ---------------------------------------------
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(8)

        search_row = QHBoxLayout()
        self.plant_input = QLineEdit()
        self.plant_input.setPlaceholderText(
            self._t("phyto_plant_placeholder", "Nom de la plante (scientifique ou courant)..."))
        self.plant_input.returnPressed.connect(self._on_search_plant)
        self.btn_search_plant = QPushButton(self._t("phyto_search_btn", "Rechercher"))
        self.btn_search_plant.setObjectName("PrimaryButton")
        self.btn_search_plant.clicked.connect(self._on_search_plant)
        search_row.addWidget(self.plant_input, 1)
        search_row.addWidget(self.btn_search_plant)
        right.addLayout(search_row)

        self.plant_name_label = QLabel(self._t("phyto_no_plant", "Aucune plante confirmée."))
        self.plant_name_label.setWordWrap(True)
        right.addWidget(self.plant_name_label)

        self.family_tree = QTreeWidget()
        self.family_tree.setHeaderLabels([
            self._t("phyto_col_family", "Famille chimique / molécule"),
            self._t("phyto_col_cid", "CID PubChem"),
        ])
        self.family_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.family_tree.setUniformRowHeights(True)
        header = self.family_tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.family_tree.itemSelectionChanged.connect(self._on_family_selection_changed)
        right.addWidget(self.family_tree, 1)

        self.btn_download_family = QPushButton(
            self._t("phyto_download_family", "Télécharger cette famille depuis PubChem"))
        self.btn_download_family.setObjectName("PrimaryButton")
        self.btn_download_family.clicked.connect(self._on_download_selected_family)
        self.btn_download_family.setEnabled(False)
        right.addWidget(self.btn_download_family)

        outer.addLayout(right, 3)
        return panel

    def _build_other_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        row = QHBoxLayout()
        self.other_input = QLineEdit()
        self.other_input.setPlaceholderText(
            self._t("phyto_other_placeholder", "Nom de la molécule (médicament, composé organique)..."))
        self.other_input.returnPressed.connect(self._on_search_other)
        self.btn_search_other = QPushButton(self._t("phyto_search_btn", "Rechercher"))
        self.btn_search_other.setObjectName("PrimaryButton")
        self.btn_search_other.clicked.connect(self._on_search_other)
        row.addWidget(self.other_input, 1)
        row.addWidget(self.btn_search_other)
        layout.addLayout(row)
        self.other_result_label = QLabel("")
        self.other_result_label.setWordWrap(True)
        layout.addWidget(self.other_result_label)
        layout.addStretch(1)
        return panel

    # ------------------------------------------------------- réseau (async)

    def _run_async(self, fn, on_ok, *args, on_fail=None, **kwargs):
        worker = _NetworkWorker(fn, on_ok, on_fail, *args, **kwargs)
        worker.finished_ok.connect(self._dispatch_ok)
        worker.failed.connect(self._dispatch_failed)
        self._workers.append(worker)
        worker.start()

    def _dispatch_ok(self, callback, result):
        if callback is not None:
            callback(result)

    def _dispatch_failed(self, callback, kind, message):
        if callback is None:
            callback = self._on_generic_error
        callback(kind, message)

    def _on_generic_error(self, kind, message):
        QMessageBox.warning(self, self._t("phyto_error_title", "Erreur réseau"), message)

    # ------------------------------------------------------------- plante

    def _reset_results(self):
        self._current_families = {}
        self._current_usage_key = None
        self._status_base = ""
        self.family_tree.clear()
        self.btn_download_family.setEnabled(False)
        self.plant_image.set_placeholder(self._t("phyto_no_image_yet", "Aucune image."))

    def _on_search_plant(self):
        name = self.plant_input.text().strip()
        if not name:
            return
        self._reset_results()
        self.plant_name_label.setText(self._t("phyto_searching", "Recherche en cours..."))
        self.btn_search_plant.setEnabled(False)
        self._run_async(phyto_api.gbif_match_species, self._on_gbif_matched, name,
                        on_fail=self._on_match_failed)

    def _on_match_failed(self, kind, message):
        self.btn_search_plant.setEnabled(True)
        self._reset_results()
        if kind == "not_found":
            self.plant_name_label.setText(
                self._t("phyto_not_found", "Aucune plante trouvée pour ce nom."))
            return
        self.plant_name_label.setText(
            self._t("phyto_search_failed", "La recherche a échoué."))
        self._on_generic_error(kind, message)

    def _on_gbif_matched(self, match):
        self.btn_search_plant.setEnabled(True)
        canonical = match.get("canonicalName") or match.get("scientificName") or "?"
        if match.get("_lookup_mode") == "vernacular":
            prefix = self._t("phyto_confirmed_vernacular", "Confirmé (nom courant reconnu) : ")
        else:
            prefix = self._t("phyto_confirmed_prefix", "Confirmé : ")
        base = prefix + canonical
        if match.get("family"):
            base += "  (" + match["family"] + ")"
        self._status_base = base
        self.plant_name_label.setText(
            base + "\n" + self._t("phyto_loading_molecules", "Recherche des molécules..."))

        usage_key = match.get("usageKey")
        self._current_usage_key = usage_key
        self.plant_image.set_placeholder(
            self._t("phyto_image_loading", "Recherche de l'image de référence..."))
        self._run_async(phyto_api.fetch_reference_image, self._on_gbif_image, usage_key)
        self._run_async(
            phyto_api.lotus_compounds_for_taxon, self._on_lotus_result,
            usage_key, canonical,
            accepted_key=match.get("acceptedUsageKey"),
            genus_key=match.get("genusKey"),
            genus_name=match.get("genus"),
            rank=match.get("rank"),
            on_fail=self._on_lotus_failed,
        )

    def _on_gbif_image(self, result):
        if result.get("usage_key") != self._current_usage_key:
            return  # résultat d'une recherche précédente
        data = result.get("data")
        pix = QPixmap()
        if data and pix.loadFromData(data):
            self.plant_image.set_image(pix)
        else:
            self.plant_image.set_placeholder(
                self._t("phyto_no_reference_image", "Aucune image de référence disponible."))

    def _on_lotus_failed(self, kind, message):
        self.plant_name_label.setText(
            self._status_base + "\n"
            + self._t("phyto_molecules_failed", "Molécules indisponibles : ") + message)

    def _on_lotus_result(self, result):
        if result.get("usage_key") != self._current_usage_key:
            return  # résultat d'une recherche précédente
        compounds = result.get("compounds", [])
        level = result.get("level")
        genus = result.get("genus") or "?"
        self._current_families = phyto_api.group_by_family(compounds)
        self.family_tree.clear()

        if not compounds:
            self.plant_name_label.setText(
                self._status_base + "\n"
                + self._t("phyto_no_compounds",
                          "Aucune molécule trouvée dans LOTUS/Wikidata pour cette plante."))
            return

        note = ""
        if level == "genus":
            note = "\n" + self._t(
                "phyto_genus_fallback",
                "Aucune donnée pour l'espèce, molécules du genre {genus} affichées."
            ).replace("{genus}", genus)
        self.plant_name_label.setText(
            self._status_base + note + "\n"
            + str(len(compounds)) + " "
            + self._t("phyto_molecules_count", "molécule(s) dans")
            + " " + str(len(self._current_families))
            + " " + self._t("phyto_families_count", "famille(s)."))

        for family, mols in self._current_families.items():
            fam_item = QTreeWidgetItem([family + " (" + str(len(mols)) + ")", ""])
            fam_item.setData(0, FAMILY_ROLE, family)
            for m in mols:
                QTreeWidgetItem(fam_item, [m.get("name", "?"), str(m.get("pubchem_cid") or "")])
            self.family_tree.addTopLevelItem(fam_item)
        self.family_tree.collapseAll()

    # ---------------------------------------------------------- téléchargement

    def _selected_family_name(self):
        items = self.family_tree.selectedItems()
        if not items:
            return None
        item = items[0]
        top = item.parent() or item
        return top.data(0, FAMILY_ROLE)

    def _on_family_selection_changed(self):
        self.btn_download_family.setEnabled(self._selected_family_name() is not None)

    def _on_download_selected_family(self):
        family_name = self._selected_family_name()
        if family_name is None:
            return
        mols = self._current_families.get(family_name, [])
        cids = []
        for m in mols:
            try:
                cid = int(m["pubchem_cid"])
            except (KeyError, TypeError, ValueError):
                continue
            if cid not in cids:
                cids.append(cid)
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
        safe_name = re.sub(r"[^\w\-]+", "_", family_name).strip("_") or "famille"
        out_file = out_dir / (safe_name + "_batch.sdf")
        self.btn_download_family.setEnabled(False)
        self.plant_name_label.setText(
            self._status_base + "\n"
            + self._t("phyto_downloading", "Téléchargement PubChem en cours : ")
            + str(len(cids)) + " CID...")
        self._run_async(
            phyto_api.pubchem_download_sdf_batch,
            lambda path: self._on_family_downloaded(path, out_dir),
            cids, out_file,
            on_fail=self._on_download_failed,
        )

    def _on_download_failed(self, kind, message):
        self._on_family_selection_changed()
        self.plant_name_label.setText(self._status_base)
        self._on_generic_error(kind, message)

    def _on_family_downloaded(self, sdf_path, out_dir):
        self._on_family_selection_changed()
        self.plant_name_label.setText(self._status_base)
        try:
            sig = inspect.signature(_split_sdf)
            kwargs = {}
            if "sdf_path" in sig.parameters:
                kwargs["sdf_path"] = sdf_path
            if "work_dir" in sig.parameters:
                kwargs["work_dir"] = out_dir
            _split_sdf(**kwargs)
            QMessageBox.information(
                self, self._t("phyto_done_title", "Terminé"),
                self._t("phyto_done_msg", "Famille téléchargée et extraite dans le dossier ligand."))
        except Exception as exc:
            QMessageBox.warning(
                self, self._t("phyto_error_title", "Erreur"),
                "Extraction SDF impossible (" + str(exc) + "). "
                "Fichier SDF groupé disponible ici : " + str(sdf_path))

    # ------------------------------------------------ autres molécules organiques

    def _on_search_other(self):
        name = self.other_input.text().strip()
        if not name:
            return
        self.other_result_label.setText(self._t("phyto_searching", "Recherche en cours..."))
        self.btn_search_other.setEnabled(False)
        self._run_async(phyto_api.pubchem_search_by_name, self._on_other_found, name,
                        on_fail=self._on_other_failed)

    def _on_other_failed(self, kind, message):
        self.btn_search_other.setEnabled(True)
        self.other_result_label.setText(message)

    def _on_other_found(self, cids):
        self.btn_search_other.setEnabled(True)
        if not cids:
            self.other_result_label.setText(self._t("phyto_no_result", "Aucun résultat."))
            return
        shown = cids[:30]
        text = self._t("phyto_cids_found", "CID PubChem trouvés : ") + ", ".join(str(c) for c in shown)
        if len(cids) > len(shown):
            text += " ... (+" + str(len(cids) - len(shown)) + ")"
        self.other_result_label.setText(text)

    def shutdown(self):
        for w in self._workers:
            if w.isRunning():
                w.wait(500)
'''


def find_file(root, name):
    direct = root / "src" / name
    if direct.is_file():
        return direct
    found = [p for p in root.rglob(name)
             if "_archive_backups" not in p.parts and "__pycache__" not in p.parts]
    if len(found) == 1:
        return found[0]
    raise SystemExit("ERREUR : " + name + " introuvable ou ambigu (" + str(len(found))
                     + " résultats). Lancez ce script depuis la racine du projet.")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def live_check(api_file):
    """Test réseau réel (informatif : n'annule jamais le patch)."""
    print("\n=== TEST RÉSEAU RÉEL (informatif) ===")
    spec = importlib.util.spec_from_file_location("phyto_api_live", str(api_file))
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    print("User-Agent envoyé :", api.USER_AGENT)

    try:
        t0 = time.time()
        resp = api._request(
            "POST", api.WIKIDATA_SPARQL_URL, "Wikidata",
            data={"query": "SELECT ?a WHERE { BIND(1 AS ?a) }"},
            headers={"Accept": "application/sparql-results+json"},
            timeout=api.SPARQL_TIMEOUT)
        print("Wikidata SPARQL (requête triviale)  -> HTTP", resp.status_code,
              "(%.1f s)" % (time.time() - t0))
    except api.PhytoError as exc:
        print("Wikidata SPARQL (requête triviale)  -> ÉCHEC :", exc,
              "| code HTTP :", getattr(exc, "status", None))

    matches = {}
    for label, name in (("nom scientifique avec faute", "anona senegalensis"),
                        ("nom courant", "corossol sauvage"),
                        ("doit être rejeté", "oingon")):
        try:
            m = api.gbif_match_species(name)
            matches[name] = m
            print("GBIF  %-28s '%s' -> %s | rang %s | clé %s | mode %s" % (
                label, name, m["canonicalName"], m["rank"], m["usageKey"], m["_lookup_mode"]))
        except api.PlantNotFound:
            print("GBIF  %-28s '%s' -> rejeté (aucune plante trouvée)" % (label, name))
        except api.PhytoError as exc:
            print("GBIF  %-28s '%s' -> ERREUR : %s" % (label, name, exc))

    m = matches.get("anona senegalensis")
    if m:
        try:
            t0 = time.time()
            res = api.lotus_compounds_for_taxon(
                m["usageKey"], m["canonicalName"], accepted_key=m.get("acceptedUsageKey"),
                genus_key=m.get("genusKey"), genus_name=m.get("genus"), rank=m.get("rank"))
            fams = api.group_by_family(res["compounds"])
            print("LOTUS Annona senegalensis -> HTTP 200 | niveau : %s | %d molécules | "
                  "%d familles (%.1f s)" % (res["level"], len(res["compounds"]), len(fams),
                                            time.time() - t0))
            for fam, mols in list(fams.items())[:5]:
                print("     -", fam, "(" + str(len(mols)) + ")")
        except api.PhytoError as exc:
            print("LOTUS Annona senegalensis -> ÉCHEC :", exc,
                  "| code HTTP :", getattr(exc, "status", None))


def main():
    root = Path.cwd()
    api_path = find_file(root, "phyto_api.py")
    page_path = find_file(root, "phyto_page.py")
    old_api, old_page = read(api_path), read(page_path)

    # --- idempotence -----------------------------------------------------
    if MARKER_NEW in old_api and MARKER_NEW in old_page:
        print("patch21 déjà appliqué : rien à faire.")
        if "--no-network" not in sys.argv:
            live_check(api_path)
        return

    # --- ancres : unicité et cohérence -------------------------------------
    for label, text in (("phyto_api.py", old_api), ("phyto_page.py", old_page)):
        n = text.count(ANCHOR_OLD)
        if n != 1:
            raise SystemExit("ERREUR : ancre '" + ANCHOR_OLD + "' trouvée " + str(n)
                             + " fois dans " + label + " (attendu : 1). Aucun fichier modifié.")
        if MARKER_NEW in text:
            raise SystemExit("ERREUR : " + label + " contient déjà patch21 mais pas l'autre "
                             "fichier : état incohérent. Aucun fichier modifié.")
    if "class PhytoPage" not in old_page:
        raise SystemExit("ERREUR : classe PhytoPage introuvable dans phyto_page.py. Aucun fichier modifié.")

    sdf = None
    for cand in (api_path.parent / "docking" / "sdf_preparer.py",):
        if cand.is_file():
            sdf = cand
    if sdf is None or "def _split_sdf" not in read(sdf):
        print("AVERTISSEMENT : src/docking/sdf_preparer.py::_split_sdf introuvable ; "
              "l'extraction automatique des SDF échouera.")

    # --- sauvegarde --------------------------------------------------------
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = root / "_archive_backups" / (stamp + "_patch21")
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(api_path, backup / "phyto_api.py")
    shutil.copy2(page_path, backup / "phyto_page.py")
    print("Sauvegarde :", backup)

    # --- application + recompilation, restauration si erreur --------------
    try:
        write(api_path, NEW_API)
        write(page_path, NEW_PAGE)
        tmp = Path(tempfile.mkdtemp())
        for path in (api_path, page_path):
            py_compile.compile(str(path), cfile=str(tmp / (path.name + "c")), doraise=True)
        assert MARKER_NEW in read(api_path) and MARKER_NEW in read(page_path)
    except Exception as exc:
        shutil.copy2(backup / "phyto_api.py", api_path)
        shutil.copy2(backup / "phyto_page.py", page_path)
        raise SystemExit("ERREUR pendant le patch (" + repr(exc) + ") : fichiers restaurés "
                         "depuis " + str(backup))

    print("OK : src/phyto_api.py et src/phyto_page.py mis à jour et recompilés.")
    print("Aucun autre fichier (Docking / Analyse / Visualisation / Crédits) n'a été touché.")
    print("Astuce : export VINASTUDIO_CONTACT='votre@email' pour l'inclure dans le User-Agent.")
    if "--no-network" not in sys.argv:
        live_check(api_path)
    print("\nLancez ensuite :  cd src && python3 main.py")


if __name__ == "__main__":
    main()
