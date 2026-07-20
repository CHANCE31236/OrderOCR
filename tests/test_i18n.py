from __future__ import annotations

from src.ui.i18n import LANGUAGES, TRANSLATIONS, translate


class FakeStore:
    def __init__(self) -> None:
        self.values = {
            "language": "zh_CN",
            "vision_model": "test-model",
            "verification_model": "test-model",
            "minimum_confidence": 0.9,
            "save_row_crops": True,
            "output_directory": "C:/tmp",
            "api_retry_count": 2,
            "max_concurrency": 2,
            "auto_delete_task_images": False,
        }

    def get(self, key, default=None):
        return self.values.get(key, default)

    def update(self, values):
        self.values.update(values)

    def as_dict(self):
        return dict(self.values)

    def get_api_key(self):
        return "test-key"

    def set_api_key(self, _key):
        return None


def test_all_languages_have_exactly_the_same_keys():
    expected = set(TRANSLATIONS["zh_CN"])
    assert set(LANGUAGES) == set(TRANSLATIONS)
    assert expected
    for language, texts in TRANSLATIONS.items():
        assert set(texts) == expected, language
        assert all(value.strip() for value in texts.values())


def test_formatting_is_supported_in_all_languages():
    for language in LANGUAGES:
        result = translate(language, "added_images", added=2, total=5)
        assert "2" in result and "5" in result


def test_main_window_switches_language_live(qtbot, monkeypatch):
    import src.ui.main_window as main_window

    monkeypatch.setattr(main_window.Database, "incomplete_tasks", lambda _self: [])
    store = FakeStore()
    window = main_window.MainWindow(store)
    qtbot.addWidget(window)
    assert not window.language_button.icon().isNull()
    assert window.windowTitle() == "订单纸单识别器"
    window.set_language("en")
    assert window.windowTitle() == "Order Paper OCR"
    assert window.table.horizontalHeaderItem(1).text() == "Product code"
    window.set_language("fr")
    assert window.windowTitle() == "Reconnaissance de bons de commande"
    assert window.table.horizontalHeaderItem(1).text() == "Référence produit"
    assert store.get("language") == "fr"


def test_settings_dialog_language_changes_immediately(qtbot):
    from src.ui.settings_dialog import SettingsDialog

    store = FakeStore()
    dialog = SettingsDialog(store)
    qtbot.addWidget(dialog)
    dialog.language_combo.setCurrentIndex(dialog.language_combo.findData("en"))
    assert dialog.windowTitle() == "Settings - Order Paper OCR"
    dialog.language_combo.setCurrentIndex(dialog.language_combo.findData("fr"))
    assert dialog.buttons.button(dialog.buttons.StandardButton.Save).text() == "Enregistrer"
