from src.i18n.language_manager import LanguageManager
from src.translations import SUPPORTED_LANGUAGES, TR


def test_every_translation_entry_has_all_supported_languages():
    for key, translations in TR.items():
        assert set(translations) == set(SUPPORTED_LANGUAGES), key
        assert all(value.strip() for value in translations.values()), key


def test_language_manager_switches_and_formats_new_ui_text():
    manager = LanguageManager(initial_lang="fr")

    assert manager.t("header_active_target") == "Cible active"
    manager.set_language("en")

    assert manager.t("header_active_target") == "Active target"
    assert manager.t("credits_load_error", error="boom") == "Error while loading: boom"
