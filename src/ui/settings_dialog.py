from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.ui.i18n import LANGUAGES, normalize_language, translate


class SettingsDialog(QDialog):
    def __init__(self, store, required: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.store = store
        self.required = required
        self.setMinimumWidth(620)
        values = store.as_dict()
        self.language = normalize_language(values.get("language"))
        self._labels: dict[str, QLabel] = {}

        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.vision_model = QLineEdit(values.get("vision_model", ""))
        self.verification_model = QLineEdit(values.get("verification_model", ""))
        self.confidence = QDoubleSpinBox()
        self.confidence.setRange(0.5, 1.0)
        self.confidence.setDecimals(2)
        self.confidence.setSingleStep(0.01)
        self.confidence.setValue(float(values.get("minimum_confidence", 0.9)))
        self.save_crops = QCheckBox()
        self.save_crops.setChecked(bool(values.get("save_row_crops", True)))
        self.output = QLineEdit(values.get("output_directory", ""))
        self.browse_button = QPushButton()
        self.browse_button.clicked.connect(self._browse)
        output_row = QWidget()
        output_layout = QHBoxLayout(output_row)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.addWidget(self.output)
        output_layout.addWidget(self.browse_button)
        self.retries = QSpinBox()
        self.retries.setRange(1, 10)
        self.retries.setValue(int(values.get("api_retry_count", 4)))
        self.concurrency = QSpinBox()
        self.concurrency.setRange(1, 8)
        self.concurrency.setValue(int(values.get("max_concurrency", 2)))
        self.auto_delete = QCheckBox()
        self.auto_delete.setChecked(bool(values.get("auto_delete_task_images", False)))
        self.language_combo = QComboBox()
        for code, native_name in LANGUAGES.items():
            self.language_combo.addItem(native_name, code)
        self.language_combo.setCurrentIndex(max(0, self.language_combo.findData(self.language)))
        self.language_combo.currentIndexChanged.connect(self._language_changed)

        self.form = QFormLayout()
        self._add_row("language", self.language_combo)
        self._add_row("api_key", self.api_key)
        self._add_row("vision_model", self.vision_model)
        self._add_row("verification_model", self.verification_model)
        self._add_row("minimum_confidence", self.confidence)
        self._add_row("crops", self.save_crops)
        self._add_row("output_directory", output_row)
        self._add_row("api_retries", self.retries)
        self._add_row("concurrency", self.concurrency)
        self._add_row("privacy_cleanup", self.auto_delete)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(self.form)
        layout.addWidget(self.note)
        layout.addWidget(self.buttons)
        self._apply_language()

    def _add_row(self, key: str, field: QWidget) -> None:
        label = QLabel()
        self._labels[key] = label
        self.form.addRow(label, field)

    def t(self, key: str, **values: object) -> str:
        return translate(self.language, key, **values)

    def _language_changed(self) -> None:
        self.language = normalize_language(self.language_combo.currentData())
        self._apply_language()

    def _apply_language(self) -> None:
        self.setWindowTitle(self.t("settings_title"))
        for key, label in self._labels.items():
            label.setText(self.t(key))
        self.api_key.setPlaceholderText(self.t("api_placeholder"))
        self.save_crops.setText(self.t("save_crops"))
        self.auto_delete.setText(self.t("auto_delete"))
        self.browse_button.setText(self.t("browse"))
        self.note.setText(self.t("privacy_note"))
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setText(self.t("save"))
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(self.t("cancel"))

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, self.t("select_output"), self.output.text())
        if folder:
            self.output.setText(folder)

    def accept(self) -> None:
        key = self.api_key.text().strip()
        if self.required and not key and not self.store.get_api_key():
            QMessageBox.warning(self, self.t("api_required"), self.t("api_required_body"))
            return
        if not self.vision_model.text().strip() or not self.verification_model.text().strip():
            QMessageBox.warning(self, self.t("invalid_config"), self.t("model_required"))
            return
        if not self.output.text().strip():
            QMessageBox.warning(self, self.t("invalid_config"), self.t("output_required"))
            return
        if key:
            try:
                self.store.set_api_key(key)
            except Exception as exc:
                QMessageBox.critical(self, self.t("key_save_failed"), self.t("key_save_failed_body", error=exc))
                return
        self.store.update(
            {
                "language": self.language,
                "vision_model": self.vision_model.text().strip(),
                "verification_model": self.verification_model.text().strip(),
                "minimum_confidence": self.confidence.value(),
                "save_row_crops": self.save_crops.isChecked(),
                "output_directory": str(Path(self.output.text().strip())),
                "api_retry_count": self.retries.value(),
                "max_concurrency": self.concurrency.value(),
                "auto_delete_task_images": self.auto_delete.isChecked(),
            }
        )
        super().accept()
