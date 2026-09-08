"""
language_manager.py
Detection automatique de la langue de l'interface (hors ligne, via la
locale du systeme d'exploitation) et gestion de la langue active.

Langues couvertes : en, fr, de, zh, ja (cf. src/translations.py).
Aucun appel reseau n'est effectue : QLocale::system() lit uniquement
la configuration regionale de l'OS.
"""
from __future__ import annotations

from PySide6.QtCore import QLocale, QObject, Signal

from src.translations import TR, tr as _tr, SUPPORTED_LANGUAGES, LANGUAGE_NAMES

# Langue de repli si celle du systeme n'est pas couverte.
DEFAULT_LANGUAGE = "en"


def detect_system_language() -> str:
    """
    Renvoie le code de langue du systeme d'exploitation (ex: 'fr', 'zh', 'ja')
    s'il fait partie de SUPPORTED_LANGUAGES, sinon DEFAULT_LANGUAGE.
    Fonctionne entierement hors ligne.
    """
    try:
        system_name = QLocale.system().name()  # ex: "fr_FR", "zh_CN", "ja_JP"
        primary = system_name.split("_")[0].lower()
    except Exception:
        primary = DEFAULT_LANGUAGE

    if primary in SUPPORTED_LANGUAGES:
        return primary
    return DEFAULT_LANGUAGE


class LanguageManager(QObject):
    """
    Point d'entree unique pour la langue active de l'interface.

    - Detection automatique au demarrage (hors ligne, via l'OS).
    - Changement manuel possible : set_language(code) ou cycle_language().
    - Emet `languageChanged(code)` pour que les widgets se retraduisent.

    Usage typique dans main_window.py :

        self.lang_mgr = LanguageManager()          # auto-detection
        self.lang_mgr.languageChanged.connect(self.retranslate_ui)
        ...
        def retranslate_ui(self, code=None):
            self.setWindowTitle(self.lang_mgr.t("window_title"))
            self.btn_run.setText(self.lang_mgr.t("btn_run"))
            # etc. pour chaque widget

        # bouton de langue dans la barre d'outils :
        self.btn_lang.clicked.connect(self.lang_mgr.cycle_language)
    """

    languageChanged = Signal(str)

    def __init__(self, initial_lang: str | None = None):
        super().__init__()
        lang = initial_lang or detect_system_language()
        self._lang = lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE

    @property
    def lang(self) -> str:
        return self._lang

    def set_language(self, code: str) -> None:
        if code not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Langue non supportee : {code!r} (attendu parmi {SUPPORTED_LANGUAGES})")
        if code != self._lang:
            self._lang = code
            self.languageChanged.emit(code)

    def cycle_language(self) -> str:
        """Passe a la langue suivante de SUPPORTED_LANGUAGES (pour un bouton unique)."""
        idx = SUPPORTED_LANGUAGES.index(self._lang)
        next_code = SUPPORTED_LANGUAGES[(idx + 1) % len(SUPPORTED_LANGUAGES)]
        self.set_language(next_code)
        return next_code

    def native_name(self, code: str | None = None) -> str:
        """Nom de la langue dans sa propre langue (pour l'afficher dans un menu/bouton)."""
        return LANGUAGE_NAMES.get(code or self._lang, code or self._lang)

    def t(self, key: str, **kwargs) -> str:
        """Raccourci : traduit `key` dans la langue actuellement active."""
        return _tr(key, lang=self._lang, **kwargs)
