"""Traduction automatique des textes d'interface ecrits en francais directement dans le code.

La table associe chaque texte francais d'origine a ses traductions (en, de, zh, ja).
Le texte scientifique international (noms de molecules, unites, sigles) reste tel quel.
Un texte avec variables s'ecrit avec {} : « {} fichier(s) pret(s) » est reconnu
quelle que soit la valeur. Les tables sont dans ui_texts_a.py, ui_texts_b.py, etc.

Diagnostic : si le fichier ~/.vina_i18n_log existe, chaque texte francais affiche sans
traduction est note, puis ecrit dans ~/vina_textes_non_traduits.txt a la fermeture.
"""
import atexit
import importlib
import re
from functools import lru_cache
from pathlib import Path

LANGS = ("en", "de", "zh", "ja")
_PARTS = ("ui_texts_a", "ui_texts_b", "ui_texts_c", "ui_texts_d")

TABLE = {}
_EXACT = {}
_TEMPLATES = []
_lang = "fr"

_LOG_FLAG = Path.home() / ".vina_i18n_log"
_LOG_OUT = Path.home() / "vina_textes_non_traduits.txt"
_LOGGING = _LOG_FLAG.exists()
_MISSES = {}
_FR = re.compile(
    r"[éèêàçùôîûÉÈÊÀÇ]|\b(le|la|les|des|du|une|un|et|pour|avec|dans|sur|fichier|erreur|choisir|ouvrir|"
    r"lancer|aucun|aucune|enregistrer|annuler|prêt|calcul|campagne|seuil|ligand|récepteur)\b", re.I)
_PREFIX = re.compile(r"^([^\w«“\(\[]+)(\w.*)$", re.S)


def _load_parts():
    for name in _PARTS:
        try:
            mod = importlib.import_module(f"{__package__}.{name}")
        except ModuleNotFoundError as exc:
            if exc.name and exc.name.endswith(name):
                continue
            raise
        TABLE.update(mod.TABLE)


def _rebuild():
    _EXACT.clear()
    _TEMPLATES.clear()
    for fr, row in TABLE.items():
        key = fr.strip()
        if "{}" in key:
            rx = re.compile(re.escape(key).replace(re.escape("{}"), "(.+?)"), re.S)
            _TEMPLATES.append((rx, row))
        else:
            _EXACT[key] = row
    _translate_core.cache_clear()


@lru_cache(maxsize=8192)
def _translate_core(lang, core):
    idx = LANGS.index(lang)
    row = _EXACT.get(core)
    if row is not None:
        return row[idx] or core
    for rx, row in _TEMPLATES:
        m = rx.fullmatch(core)
        if m and row[idx]:
            try:
                return row[idx].format(*m.groups())
            except (IndexError, KeyError, ValueError):
                continue
    return core


def set_language(code):
    global _lang
    _lang = code if code in LANGS else "fr"


def active():
    return _lang != "fr"


def translate(text):
    """Traduit `text` dans la langue active ; renvoie le texte tel quel s'il est inconnu."""
    if _lang == "fr" or not isinstance(text, str):
        return text
    core = text.strip()
    if not core:
        return text
    out = _translate_core(_lang, core)
    if out != core:
        return text.replace(core, out, 1)
    m = _PREFIX.match(core)          # « ✓ Enregistrer » : symbole devant le texte
    if m:
        out2 = _translate_core(_lang, m.group(2))
        if out2 != m.group(2):
            return text.replace(core, m.group(1) + out2, 1)
    if len(core) >= 3 and core not in _MISSES and _FR.search(core) and _LOG_FLAG.exists():
        _MISSES[core] = 1
        try:
            with _LOG_OUT.open("a", encoding="utf-8") as f:
                f.write(repr(core) + "\n")
        except OSError:
            pass
    return text


def register(fr, row):
    TABLE[fr] = tuple(row)
    _rebuild()


def unregister(fr):
    TABLE.pop(fr, None)
    _rebuild()


def _write_misses():
    try:
        lignes = [f"{n}x | {t!r}" for t, n in sorted(_MISSES.items())]
        _LOG_OUT.write_text(f"{len(lignes)} textes francais non traduits\n" + "\n".join(lignes) + "\n",
                            encoding="utf-8")
    except OSError:
        pass


if _LOGGING:
    atexit.register(_write_misses)

_load_parts()
_rebuild()
