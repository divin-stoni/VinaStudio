"""
phyto_api.py
# --- patch16 phytomolecules tab ---
# --- patch20 : repli nom vernaculaire + requete LOTUS par ID GBIF ---
# --- patch21 : User-Agent + SPARQL en POST, filtre de rang GBIF, repli genre ---
# --- patch22 : photos représentatives (Wikipédia > iNaturalist > GBIF), cycle de photos ---

Appels réseau pour l'onglet Phytomolécules :
- GBIF : confirmation du nom scientifique OU vernaculaire d'une plante
  (les rangs supérieurs à la famille sont toujours rejetés)
- Photo de référence : Wikipédia (photo de l'article, la plus représentative),
  puis iNaturalist (photos de taxon choisies), puis GBIF en dernier recours
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
GBIF_SPECIES_MEDIA_URL = "https://api.gbif.org/v1/species/{key}/media"
WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
INAT_TAXA_URL = "https://api.inaturalist.org/v1/taxa"
INAT_TAXON_URL = "https://api.inaturalist.org/v1/taxa/{id}"
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
        "species": d.get("species"),
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
# Photo de référence
# --------------------------------------------------------------------------
# Les photos d'observation GBIF sont des clichés de terrain (buissons, sols...)
# souvent peu représentatifs. Ordre de préférence :
#   1. Wikipédia : image principale de l'article de la plante ;
#   2. iNaturalist : photos de taxon (choisies par la communauté) ;
#   3. GBIF : médias du taxon, puis observations (dernier recours).

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
MAX_ORIGINAL_WIDTH = 4000


def _looks_like_image(content):
    """Reconnaît JPEG / PNG / WEBP / GIF par leur signature (écarte HTML, SVG, TIFF)."""
    if not content or len(content) < 12:
        return False
    return (content[:3] == b"\xff\xd8\xff"
            or content[:8] == b"\x89PNG\r\n\x1a\n"
            or (content[:4] == b"RIFF" and content[8:12] == b"WEBP")
            or content[:4] == b"GIF8")


def _cand(url, source):
    return {"url": url, "source": source}


def gbif_reference_images(usage_key, limit=8):
    """URLs de photos d'observation GBIF (occurrences). Liste vide si rien."""
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
    """Première URL de photo d'observation, ou None (compatibilité)."""
    urls = gbif_reference_images(usage_key, limit=5)
    return urls[0] if urls else None


def _wikipedia_candidates(names):
    for name in names:
        url = WIKIPEDIA_SUMMARY_URL.format(title=quote(name.replace(" ", "_"), safe=""))
        try:
            data = _json(_request("GET", url, "Wikipédia"), "Wikipédia")
        except PhytoError:
            continue
        if data.get("type") != "standard":
            continue
        original = data.get("originalimage") or {}
        thumb = data.get("thumbnail") or {}
        chosen = None
        osrc = original.get("source") or ""
        if (osrc.lower().endswith(IMAGE_EXTENSIONS)
                and 0 < (original.get("width") or 0) <= MAX_ORIGINAL_WIDTH):
            chosen = osrc
        elif thumb.get("source"):
            chosen = thumb["source"]
        if chosen:
            return [_cand(chosen, "Wikipédia")]
    return []


def _inat_photo_url(photo):
    return (photo.get("large_url") or photo.get("medium_url")
            or (photo.get("url") or "").replace("/square.", "/medium."))


def _inat_candidates(names):
    wanted = {n.lower() for n in names}
    try:
        resp = _request("GET", INAT_TAXA_URL, "iNaturalist",
                        params={"q": names[0], "per_page": 5, "is_active": "true"})
        results = _json(resp, "iNaturalist").get("results", [])
    except PhytoError:
        return []
    taxon = None
    for r in results:
        if (r.get("name") or "").lower() in wanted:
            taxon = r
            break
    if taxon is None:
        return []          # aucun taxon exactement homonyme : on n'invente rien
    photos = [taxon.get("default_photo") or {}]
    try:
        detail = _json(_request("GET", INAT_TAXON_URL.format(id=taxon["id"]), "iNaturalist"),
                       "iNaturalist")
        for tp in (detail.get("results") or [{}])[0].get("taxon_photos", [])[:8]:
            photos.append(tp.get("photo") or {})
    except (PhytoError, KeyError, IndexError):
        pass
    out, seen_ids = [], set()
    for photo in photos:
        url = _inat_photo_url(photo)
        pid = photo.get("id") or url
        if url and pid not in seen_ids:
            seen_ids.add(pid)
            out.append(_cand(url, "iNaturalist"))
    return out


def _gbif_media_candidates(usage_key):
    resp = _request("GET", GBIF_SPECIES_MEDIA_URL.format(key=usage_key), "GBIF")
    out = []
    for r in _json(resp, "GBIF").get("results", []):
        if r.get("type") == "StillImage" and r.get("identifier"):
            out.append(_cand(r["identifier"], "GBIF"))
    return out


def reference_image_candidates(usage_key, canonical_name=None, species_name=None):
    """Liste ordonnée de {'url', 'source'}. Ne lève jamais."""
    names = []
    for n in (canonical_name, species_name):
        if n and n.lower() not in [x.lower() for x in names]:
            names.append(n)
    sources = []
    if names:
        sources.append(lambda: _wikipedia_candidates(names))
        sources.append(lambda: _inat_candidates(names))
    if usage_key:
        sources.append(lambda: _gbif_media_candidates(usage_key))
        sources.append(lambda: [_cand(u, "GBIF (observation)")
                                for u in gbif_reference_images(usage_key, 8)])
    out, seen = [], set()
    for fn in sources:
        try:
            items = fn()
        except PhytoError:
            items = []
        for item in items:
            if item["url"] not in seen:
                seen.add(item["url"])
                out.append(item)
    return out


def download_image_bytes(url):
    return _request("GET", url, "Serveur d'images", timeout=REQUEST_TIMEOUT).content


def download_first_image(candidates, start=0, skip=None):
    """Télécharge la première image valide à partir de l'indice start (circulaire),
    en ignorant l'indice skip. Retourne {'data', 'index', 'source'} ou None."""
    n = len(candidates)
    for k in range(n):
        i = (start + k) % n
        if i == skip:
            continue
        try:
            content = download_image_bytes(candidates[i]["url"])
        except PhytoError:
            continue
        if len(content) > 1000 and _looks_like_image(content):
            return {"data": content, "index": i, "source": candidates[i]["source"]}
    return None


def fetch_reference_image(usage_key, canonical_name=None, species_name=None):
    """Meilleure photo disponible + liste des autres candidates. Ne lève jamais."""
    try:
        cands = reference_image_candidates(usage_key, canonical_name, species_name)
        found = download_first_image(cands, 0) if cands else None
    except PhytoError:
        cands, found = [], None
    return {
        "usage_key": usage_key,
        "candidates": cands,
        "data": found["data"] if found else None,
        "index": found["index"] if found else -1,
        "source": found["source"] if found else None,
    }


def fetch_next_image(usage_key, candidates, start, skip=None):
    """Photo suivante parmi les candidates (clic sur l'image). Ne lève jamais."""
    try:
        found = download_first_image(candidates, start, skip)
    except PhytoError:
        found = None
    return {
        "usage_key": usage_key,
        "data": found["data"] if found else None,
        "index": found["index"] if found else -1,
        "source": found["source"] if found else None,
    }


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


# ==========================================================================
# --- patch23 : suggestions en cas d'ambiguïté, molécules en tableau, image 2D
# ==========================================================================
import unicodedata

GBIF_SUGGEST_URL = "https://api.gbif.org/v1/species/suggest"
PUBCHEM_PROPS_URL = ("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cids}"
                     "/property/Title,MolecularFormula,MolecularWeight,IUPACName/JSON")
PUBCHEM_PNG_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/PNG"
PUBCHEM_AUTOCOMPLETE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/autocomplete/compound/{name}/json"

MAX_CANDIDATES = 12
MAX_MOLECULES = 30
_RANK_ORDER = {"SPECIES": 0, "SUBSPECIES": 1, "VARIETY": 2, "GENUS": 3, "FAMILY": 4}
_FRENCH_CODES = ("fra", "fre", "fr")


def _fold(text):
    """Minuscules + sans accents : « Avocat » et « avocát » se comparent égaux."""
    text = unicodedata.normalize("NFD", str(text or ""))
    return "".join(c for c in text if unicodedata.category(c) != "Mn").casefold().strip()


def _plausible_plant(d):
    """Filtre tolérant (alternatives GBIF, résultats de recherche) : rang famille
    ou inférieur, règne Plantae, jamais la clé 6 (Plantae)."""
    key = d.get("usageKey") or d.get("key")
    if not key or key == GBIF_PLANTAE_KEY:
        return False
    if d.get("matchType") in ("NONE", "HIGHERRANK"):
        return False
    if d.get("rank") not in ACCEPTED_RANKS:
        return False
    if d.get("kingdom") and d.get("kingdom") != "Plantae":
        return False
    conf = d.get("confidence")
    if d.get("matchType") == "FUZZY" and conf is not None and conf < MIN_FUZZY_CONFIDENCE:
        return False
    return True


def _vernacular_hit(result, wanted):
    """(nom trouvé, exact ?, langue) pour le nom courant demandé, ou (None, False, None)."""
    partial = None
    for vn in result.get("vernacularNames") or []:
        vname = (vn.get("vernacularName") or "").strip()
        f = _fold(vname)
        if len(f) < 3:
            continue
        if f == wanted:
            return vname, True, vn.get("language")
        if partial is None and (wanted in f or f in wanted):
            partial = (vname, vn.get("language"))
    if partial:
        return partial[0], False, partial[1]
    return None, False, None


def _make_candidate(d, mode, score, matched=None, lang=None):
    cand = _normalize_usage(d, mode)
    cand["status"] = d.get("status")
    cand["confidence"] = d.get("confidence")
    cand["matched"] = matched
    cand["score"] = score
    # Un synonyme est présenté sous son nom accepté (plus parlant pour l'utilisateur)
    if d.get("status") == "SYNONYM" and d.get("species") and d.get("rank") in SPECIES_LEVEL_RANKS:
        cand["canonicalName"] = d["species"]
        cand["_lookup_mode"] = "synonym"
    french = 0 if (lang or "").lower() in _FRENCH_CODES else 1
    cand["_sort"] = (score, french, _RANK_ORDER.get(cand.get("rank"), 9),
                     (cand.get("canonicalName") or "").lower())
    return cand


def _add_candidate(pool, cand):
    key = str(cand.get("acceptedUsageKey") or cand.get("usageKey"))
    old = pool.get(key)
    if old is None or cand["_sort"] < old["_sort"]:
        pool[key] = cand


def gbif_find_candidates(name):
    """Toutes les correspondances plausibles pour un nom de plante.
    Sources : 1) nom scientifique (exact, approché, alternatives GBIF, synonymes) ;
    2) noms courants (espèces, genres, familles) ; 3) début de nom scientifique.
    Retourne {'query', 'candidates' (triés), 'ambiguous'}.
    ambiguous = pas de correspondance scientifique exacte ET plusieurs candidats
    -> l'interface affiche alors un tableau de suggestions à cliquer.
    Lève PlantNotFound si rien de valable, ou l'erreur réseau si tout a échoué."""
    name = (name or "").strip()
    if not name:
        raise PlantNotFound("Nom vide.")
    wanted = _fold(name)
    pool, errors = {}, []

    # 1) nom scientifique : correspondance principale + alternatives proches
    try:
        data = _json(_request("GET", GBIF_MATCH_URL, "GBIF", params={
            "name": name, "kingdom": "Plantae", "verbose": "true"}), "GBIF")
        alts = data.get("alternatives") or (data.get("diagnostics") or {}).get("alternatives") or []
        for d in [data] + list(alts):
            if not isinstance(d, dict) or not _plausible_plant(d):
                continue
            exact = d.get("matchType") == "EXACT"
            _add_candidate(pool, _make_candidate(
                d, "scientific" if exact else "fuzzy", 0 if exact else 2))
    except PhytoError as exc:
        errors.append(exc)

    # 2) noms courants (espèce, genre ou famille)
    try:
        resp = _request("GET", GBIF_SEARCH_URL, "GBIF", params={
            "q": name, "qField": "VERNACULAR", "rank": ["SPECIES", "GENUS", "FAMILY"],
            "status": "ACCEPTED", "datasetKey": GBIF_BACKBONE_KEY,
            "highertaxonKey": GBIF_PLANTAE_KEY, "limit": 40})
        for r in _json(resp, "GBIF").get("results", []):
            if not _plausible_plant(r):
                continue
            vname, exact, lang = _vernacular_hit(r, wanted)
            if vname is None:
                continue
            _add_candidate(pool, _make_candidate(
                r, "vernacular", 1 if exact else 3, matched=vname, lang=lang))
    except PhytoError as exc:
        errors.append(exc)

    # 3) début de nom scientifique (saisie incomplète)
    if len(name) >= 3:
        try:
            resp = _request("GET", GBIF_SUGGEST_URL, "GBIF", params={
                "q": name, "datasetKey": GBIF_BACKBONE_KEY,
                "rank": ["SPECIES", "GENUS", "FAMILY"], "limit": 15})
            items = _json(resp, "GBIF")
            for r in items if isinstance(items, list) else []:
                if not isinstance(r, dict) or not _plausible_plant(r):
                    continue
                if r.get("status") not in (None, "ACCEPTED"):
                    continue
                _add_candidate(pool, _make_candidate(r, "prefix", 4))
        except PhytoError as exc:
            errors.append(exc)

    cands = sorted(pool.values(), key=lambda c: c["_sort"])[:MAX_CANDIDATES]
    if not cands:
        if errors:
            raise errors[0]
        raise PlantNotFound("Aucune plante trouvée pour « " + name + " ».")
    ambiguous = cands[0]["score"] != 0 and len(cands) > 1
    return {"query": name, "candidates": cands, "ambiguous": ambiguous}


# --------------------------------------------------------------------------
# PubChem : tableau de molécules, suggestions, structure 2D
# --------------------------------------------------------------------------

def pubchem_molecule_details(cids):
    """Nom, formule, masse et nom IUPAC pour une liste de CID (un seul appel).
    Si PubChem ne répond pas aux propriétés, les lignes gardent au moins le CID."""
    cids = [int(c) for c in cids][:MAX_MOLECULES]
    if not cids:
        return []
    by_cid = {}
    try:
        url = PUBCHEM_PROPS_URL.format(cids=",".join(str(c) for c in cids))
        data = _json(_request("GET", url, "PubChem"), "PubChem")
        for row in data.get("PropertyTable", {}).get("Properties", []):
            by_cid[int(row["CID"])] = row
    except (PhytoError, KeyError, ValueError):
        pass
    out = []
    for cid in cids:
        row = by_cid.get(cid, {})
        out.append({
            "kind": "mol", "cid": cid,
            "title": row.get("Title") or "",
            "formula": row.get("MolecularFormula") or "",
            "weight": str(row.get("MolecularWeight") or ""),
            "iupac": row.get("IUPACName") or "",
        })
    return out


def pubchem_autocomplete(name, limit=10):
    """Noms de composés proches (service d'autocomplétion PubChem). [] si échec."""
    url = PUBCHEM_AUTOCOMPLETE_URL.format(name=quote(name, safe=""))
    try:
        data = _json(_request("GET", url, "PubChem", params={"limit": limit}), "PubChem")
    except PhytoError:
        return []
    return list((data.get("dictionary_terms") or {}).get("compound") or [])


def pubchem_search_molecules(name):
    """Recherche par nom : tableau de molécules si PubChem connaît le nom,
    sinon suggestions de noms proches. Retourne un dict avec 'query'."""
    cids = pubchem_search_by_name(name)
    if cids:
        return {"query": name, "total": len(cids),
                "molecules": pubchem_molecule_details(cids), "suggestions": []}
    return {"query": name, "total": 0, "molecules": [],
            "suggestions": pubchem_autocomplete(name)}


def pubchem_fetch_2d_png(cid, size=600):
    """Image PNG de la structure 2D d'un CID (dessinée par PubChem)."""
    resp = _request("GET", PUBCHEM_PNG_URL.format(cid=int(cid)), "PubChem",
                    params={"image_size": str(size) + "x" + str(size)})
    if not _looks_like_image(resp.content):
        raise PhytoNetworkError("PubChem : image 2D illisible.")
    return resp.content
