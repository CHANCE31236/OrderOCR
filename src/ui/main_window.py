from __future__ import annotations

import traceback
import uuid
from pathlib import Path

from PySide6.QtCore import QThread, Signal, Slot, Qt
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QIcon
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.business.validators import SUPPORTED_IMAGE_SUFFIXES, duplicate_product_codes
from src.export.audit_exporter import export_audit_log
from src.export.excel_exporter import ExportBlockedError, export_order_excel
from src.ocr.pipeline import CancelledError, PipelineResult, ProcessedPage, RecognitionPipeline
from src.business.confidence import reconcile_row
from src.ocr.row_verifier import RowVerifier
from src.ocr.vision_client import VisionClient
from src.storage.cache import JsonCache
from src.storage.database import Database
from src.ui.image_viewer import ImageViewer
from src.ui.i18n import LANGUAGES, join_items, normalize_language, translate
from src.ui.review_table import ReviewTable
from src.ui.settings_dialog import SettingsDialog
from src.utils.logging import configure_logging
from src.utils.paths import resource_path


class RecognitionWorker(QThread):
    progress = Signal(int, int, str, int)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, store, paths: list[str], database: Database, parent=None) -> None:
        super().__init__(parent)
        self.pipeline = RecognitionPipeline(store, database)
        self.paths = paths

    def run(self) -> None:
        try:
            result = self.pipeline.run(self.paths, lambda done, total, message, calls: self.progress.emit(done, total, message, calls))
            self.completed.emit(result)
        except CancelledError:
            self.failed.emit("The task was cancelled")
        except Exception as exc:
            self.failed.emit(f"{exc}\n\n{traceback.format_exc(limit=4)}")


class RecheckWorker(QThread):
    completed = Signal(int, object)
    failed = Signal(str)

    def __init__(self, store, page: ProcessedPage, row_index: int, parent=None) -> None:
        super().__init__(parent)
        self.store = store
        self.page = page
        self.row_index = row_index

    def run(self) -> None:
        try:
            settings = self.store.as_dict()
            key = self.store.get_api_key()
            client = VisionClient(key or "", settings)
            verifier = RowVerifier(client, settings["verification_model"])
            first = self.page.reviewed_rows[self.row_index].observation
            row_path = Path(first.row_crop)
            columns_path = row_path.with_name(row_path.stem + "_box_quantity.jpg")
            verification = verifier.verify(
                page_path=self.page.corrected_path,
                row_path=row_path,
                columns_path=columns_path,
                cache_key=f"manual_recheck_{uuid.uuid4().hex}",
                row_number=first.row_number,
            )
            result = reconcile_row(first, verification, float(settings.get("minimum_confidence", 0.9)))
            self.completed.emit(self.row_index, result)
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self, settings_store) -> None:
        super().__init__()
        self.store = settings_store
        self.database = Database()
        self.logger = configure_logging()
        self.image_paths: list[str] = []
        self.result: PipelineResult | None = None
        self.worker: RecognitionWorker | None = None
        self.recheck_worker: RecheckWorker | None = None
        self.current_page: ProcessedPage | None = None
        self.language = normalize_language(self.store.get("language", "zh_CN"))
        self.resize(1500, 940)
        self.setAcceptDrops(True)
        self._build_ui()
        self._apply_language()
        self._restore_incomplete_task()

    def _build_ui(self) -> None:
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)
        self.toolbar_actions: dict[str, QAction] = {}
        for key, callback in (("import_images", self.import_images), ("start_recognition", self.start_recognition), ("pause_resume", self.toggle_pause), ("cancel_task", self.cancel_task), ("settings", self.open_settings), ("clear_cache", self.clear_cache)):
            action = QAction(self)
            action.triggered.connect(callback)
            self.toolbar.addAction(action)
            self.toolbar_actions[key] = action
        self.language_menu = QMenu(self)
        self.language_actions: dict[str, QAction] = {}
        for code, native_name in LANGUAGES.items():
            action = QAction(native_name, self, checkable=True)
            action.setData(code)
            action.triggered.connect(lambda _checked=False, selected=code: self.set_language(selected))
            self.language_menu.addAction(action)
            self.language_actions[code] = action
        self.language_button = QToolButton(self)
        self.language_button.setIcon(QIcon(str(resource_path("assets", "language.svg"))))
        self.language_button.setMenu(self.language_menu)
        self.language_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.language_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toolbar.addWidget(self.language_button)

        self.order_list = QListWidget()
        self.page_list = QListWidget()
        self.order_list.currentTextChanged.connect(self._order_selected)
        self.page_list.currentRowChanged.connect(self._page_selected)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.order_label = QLabel()
        left_layout.addWidget(self.order_label)
        left_layout.addWidget(self.order_list, 2)
        self.page_label = QLabel()
        left_layout.addWidget(self.page_label)
        left_layout.addWidget(self.page_list, 3)
        left.setMinimumWidth(230)

        self.original_view = ImageViewer()
        self.corrected_view = ImageViewer()
        self.row_view = ImageViewer()
        self.tabs = QTabWidget()
        self.tabs.addTab(self.original_view, "")
        self.tabs.addTab(self.corrected_view, "")
        self.tabs.addTab(self.row_view, "")

        self.table = ReviewTable(self.language)
        self.table.itemSelectionChanged.connect(self._row_selected)
        self.table.row_edited.connect(self._record_edit)
        buttons = QHBoxLayout()
        self.action_buttons: dict[str, QPushButton] = {}
        for key, callback in (("recheck_row", self.recheck_current_row), ("confirm_row", self.confirm_current_row), ("confirm_high", self.confirm_high_confidence), ("export_excel", self.export_excel)):
            button = QPushButton()
            button.clicked.connect(callback)
            buttons.addWidget(button)
            self.action_buttons[key] = button
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.addWidget(self.tabs, 3)
        center_layout.addWidget(self.table, 4)
        center_layout.addLayout(buttons)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(center)
        splitter.setStretchFactor(1, 1)
        self.progress = QProgressBar()
        self.progress.setFormat("")
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(1000)
        self.log.setMaximumHeight(150)
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addWidget(splitter, 1)
        layout.addWidget(self.progress)
        self.log_label = QLabel()
        layout.addWidget(self.log_label)
        layout.addWidget(self.log)
        self.setCentralWidget(root)
        self.statusBar().showMessage("")

    def t(self, key: str, **values: object) -> str:
        return translate(self.language, key, **values)

    def set_language(self, language: str) -> None:
        self.language = normalize_language(language)
        self.store.update({"language": self.language})
        self._apply_language()

    def _apply_language(self) -> None:
        self.setWindowTitle(self.t("app_title"))
        self.toolbar.setWindowTitle(self.t("toolbar"))
        for key, action in self.toolbar_actions.items():
            action.setText(self.t(key))
        self.language_button.setText(self.t("language"))
        self.language_button.setToolTip("Language")
        for code, action in self.language_actions.items():
            action.setChecked(code == self.language)
        self.order_label.setText(self.t("orders"))
        self.page_label.setText(self.t("pages"))
        self.tabs.setTabText(0, self.t("original_image"))
        self.tabs.setTabText(1, self.t("corrected_image"))
        self.tabs.setTabText(2, self.t("row_zoom"))
        self.original_view.set_placeholder(self.t("original_preview"))
        self.corrected_view.set_placeholder(self.t("corrected_preview"))
        self.row_view.set_placeholder(self.t("row_preview"))
        for key, button in self.action_buttons.items():
            button.setText(self.t(key))
        self.table.set_language(self.language)
        if self.progress.value() == 0:
            self.progress.setFormat(self.t("waiting"))
        self.log_label.setText(self.t("log"))
        self.statusBar().showMessage(self.t("drag_hint"))

    def append_log(self, text: str) -> None:
        self.log.appendPlainText(text)
        self.logger.info(text)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() and any(Path(url.toLocalFile()).suffix.lower() in SUPPORTED_IMAGE_SUFFIXES for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        self._add_images([url.toLocalFile() for url in event.mimeData().urls()])

    @Slot()
    def import_images(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, self.t("select_images"), "", self.t("image_filter"))
        self._add_images(paths)

    def _add_images(self, paths: list[str]) -> None:
        added = 0
        for path in paths:
            if Path(path).suffix.lower() in SUPPORTED_IMAGE_SUFFIXES and path not in self.image_paths:
                self.image_paths.append(path)
                added += 1
        self.page_list.clear()
        self.page_list.addItems([Path(path).name for path in self.image_paths])
        if self.image_paths:
            self.original_view.set_image(self.image_paths[0])
        self.append_log(self.t("added_images", added=added, total=len(self.image_paths)))

    @Slot()
    def start_recognition(self) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, self.t("task_running_title"), self.t("task_running_body"))
            return
        if not self.image_paths:
            QMessageBox.warning(self, self.t("no_images_title"), self.t("no_images_body"))
            return
        if not self.store.get_api_key():
            self.open_settings(required=True)
            if not self.store.get_api_key():
                return
        self.result = None
        self.order_list.clear()
        self.table.set_rows([])
        self.worker = RecognitionWorker(self.store, self.image_paths, self.database, self)
        self.worker.progress.connect(self._on_progress)
        self.worker.completed.connect(self._on_completed)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()
        self.append_log(self.t("started"))

    @Slot(int, int, str, int)
    def _on_progress(self, done: int, total: int, message: str, calls: int) -> None:
        self.progress.setRange(0, total)
        self.progress.setValue(done)
        self.progress.setFormat(self.t("progress", message=message, calls=calls))
        self.statusBar().showMessage(message)

    @Slot(object)
    def _on_completed(self, result: PipelineResult) -> None:
        self.result = result
        self.order_list.addItems(sorted(result.groups))
        self.progress.setValue(self.progress.maximum())
        self.progress.setFormat(self.t("completed", calls=result.api_calls))
        for error in result.errors:
            self.append_log(self.t("warning", error=error))
        self.append_log(self.t("complete_log", pages=len(result.pages), orders=len(result.groups)))
        if self.order_list.count():
            self.order_list.setCurrentRow(0)

    @Slot(str)
    def _on_failed(self, error: str) -> None:
        self.progress.setFormat("The task failed or was cancelled")
        self.append_log(error)
        QMessageBox.critical(self, self.t("recognition_incomplete"), error)

    @Slot()
    def toggle_pause(self) -> None:
        if not self.worker or not self.worker.isRunning():
            return
        if self.worker.pipeline.run_event.is_set():
            self.worker.pipeline.pause()
            self.append_log(self.t("paused"))
        else:
            self.worker.pipeline.resume()
            self.append_log(self.t("resumed"))

    @Slot()
    def cancel_task(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.pipeline.cancel()
            self.append_log(self.t("cancelling"))

    @Slot()
    def open_settings(self, required: bool = False) -> None:
        dialog = SettingsDialog(self.store, required=required, parent=self)
        result = dialog.exec()
        if result == SettingsDialog.DialogCode.Accepted:
            self.language = normalize_language(self.store.get("language", self.language))
            self._apply_language()
        if required and not self.store.get_api_key():
            self.append_log(self.t("no_key"))

    @Slot()
    def clear_cache(self) -> None:
        if QMessageBox.question(self, self.t("clear_cache_title"), self.t("clear_cache_body")) == QMessageBox.StandardButton.Yes:
            JsonCache().clear()
            self.append_log(self.t("cache_cleared"))

    def _order_selected(self, order_number: str) -> None:
        self.page_list.clear()
        if not self.result or not order_number:
            return
        pages = [page for page in self.result.pages if page.extraction.order_number == order_number]
        pages.sort(key=lambda page: (page.extraction.page_number is None, page.extraction.page_number or 0))
        for page in pages:
            number = page.extraction.page_number if page.extraction.page_number is not None else "?"
            total = page.extraction.total_pages if page.extraction.total_pages is not None else "?"
            warning = " ⚠" if page.warnings else ""
            self.page_list.addItem(f"{number}/{total} - {Path(page.source_path).name}{warning}")
            self.page_list.item(self.page_list.count() - 1).setData(Qt.ItemDataRole.UserRole, page)
        if self.page_list.count():
            self.page_list.setCurrentRow(0)

    def _page_selected(self, index: int) -> None:
        item = self.page_list.item(index)
        if not item or not isinstance(item.data(Qt.ItemDataRole.UserRole), ProcessedPage):
            if self.result is None and 0 <= index < len(self.image_paths):
                self.original_view.set_image(self.image_paths[index])
            return
        self.current_page = item.data(Qt.ItemDataRole.UserRole)
        self.original_view.set_image(self.current_page.source_path)
        self.corrected_view.set_image(self.current_page.corrected_path)
        self.table.set_rows(self.current_page.reviewed_rows)
        if self.current_page.warnings:
            self.append_log("; ".join(self.current_page.warnings))

    def _row_selected(self) -> None:
        row = self.table.current_reviewed_row()
        self.row_view.set_image(row.observation.row_crop if row else None)

    @Slot(dict)
    def _record_edit(self, payload: dict) -> None:
        if self.result:
            self.database.audit(self.result.task_id, "manual_edit", payload)
            self.append_log(self.t("edited", row=payload["row_index"] + 1))
            self.table.refresh_row(payload["row_index"])

    @Slot()
    def confirm_current_row(self) -> None:
        row = self.table.current_reviewed_row()
        if not row:
            return
        if row.final_box_count is None or not row.observation.product_code.strip():
            QMessageBox.warning(self, self.t("cannot_confirm"), self.t("cannot_confirm_body"))
            return
        before = row.model_dump(mode="json")
        row.needs_review = False
        row.manually_confirmed = True
        row.status = "manually_confirmed"
        row.review_reason = "Confirmed by the user in the review interface"
        if self.result:
            self.database.audit(self.result.task_id, "manual_confirm", {"before": before, "after": row.model_dump(mode="json")})
        self.table.refresh_row(self.table.currentRow())

    @Slot()
    def confirm_high_confidence(self) -> None:
        if not self.current_page:
            return
        threshold = float(self.store.get("minimum_confidence", 0.9))
        count = 0
        for row in self.current_page.reviewed_rows:
            if row.status == "auto_confirmed" and row.observation.overall_confidence >= threshold:
                row.needs_review = False
                row.manually_confirmed = True
                row.status = "manually_confirmed"
                count += 1
        self.table.set_rows(self.current_page.reviewed_rows)
        self.append_log(self.t("high_confirmed", count=count))

    @Slot()
    def recheck_current_row(self) -> None:
        if not self.current_page or self.table.currentRow() < 0:
            return
        if self.recheck_worker and self.recheck_worker.isRunning():
            QMessageBox.information(self, self.t("rechecking"), self.t("rechecking_body"))
            return
        if not self.store.get_api_key():
            self.open_settings(required=True)
            if not self.store.get_api_key():
                return
        row_index = self.table.currentRow()
        self.recheck_worker = RecheckWorker(self.store, self.current_page, row_index, self)
        self.recheck_worker.completed.connect(self._recheck_completed)
        self.recheck_worker.failed.connect(lambda error: QMessageBox.critical(self, self.t("recheck_failed"), error))
        self.recheck_worker.start()
        self.append_log(self.t("recheck_start", row=row_index + 1))

    @Slot(int, object)
    def _recheck_completed(self, row_index: int, reviewed_row) -> None:
        if not self.current_page:
            return
        before = self.current_page.reviewed_rows[row_index].model_dump(mode="json")
        self.current_page.reviewed_rows[row_index] = reviewed_row
        if self.result:
            self.database.audit(self.result.task_id, "manual_recheck", {"before": before, "after": reviewed_row.model_dump(mode="json")})
        self.table.set_rows(self.current_page.reviewed_rows)
        self.table.selectRow(row_index)
        self.append_log(self.t("recheck_done", row=row_index + 1))

    @Slot()
    def export_excel(self) -> None:
        if not self.result or not self.order_list.currentItem():
            QMessageBox.warning(self, self.t("no_results"), self.t("no_results_body"))
            return
        order_number = self.order_list.currentItem().text()
        group = self.result.groups[order_number]
        if group.export_blocked:
            details = []
            if group.missing_pages:
                details.append(self.t("missing_pages", items=join_items(self.language, group.missing_pages)))
            if group.duplicate_pages:
                details.append(self.t("duplicate_pages", items=join_items(self.language, group.duplicate_pages)))
            if group.similar_order_warning:
                details.append(self.t("similar_orders", items=join_items(self.language, group.similar_order_warning)))
            separator = "；" if self.language == "zh_CN" else "; "
            QMessageBox.critical(self, self.t("export_blocked"), separator.join(details) + " " + self.t("verify_pages"))
            return
        pages = [page for page in self.result.pages if page.extraction.order_number == order_number]
        rows = [row for page in pages for row in page.reviewed_rows]
        duplicates = duplicate_product_codes([row.observation.product_code for row in rows])
        allow_duplicates = False
        if duplicates:
            answer = QMessageBox.question(self, self.t("duplicate_products"), self.t("duplicate_prompt", items=join_items(self.language, duplicates)))
            allow_duplicates = answer == QMessageBox.StandardButton.Yes
            if not allow_duplicates:
                return
        try:
            output = self.store.get("output_directory")
            excel_path = export_order_excel(order_number, rows, output, allow_duplicates=allow_duplicates)
            audit_payload = {
                "order_number": order_number,
                "pages": [page.audit_payload() for page in pages],
                "manual_audit_events": self.database.audit_events(self.result.task_id),
                "final_export_values": [{"product_code": row.observation.product_code, "box_count": row.final_box_count} for row in rows],
            }
            audit_path = export_audit_log(order_number, output, audit_payload)
        except (ExportBlockedError, OSError, ValueError) as exc:
            QMessageBox.critical(self, self.t("export_failed"), str(exc))
            return
        self.append_log(self.t("exported", excel=excel_path, audit=audit_path))
        QMessageBox.information(self, self.t("export_success"), self.t("export_paths", excel=excel_path, audit=audit_path))

    def _restore_incomplete_task(self) -> None:
        tasks = self.database.incomplete_tasks()
        if not tasks:
            return
        payload = tasks[0]["payload"]
        existing = [path for path in payload.get("images", []) if Path(path).exists()]
        if existing and QMessageBox.question(self, self.t("restore_title"), self.t("restore_body", count=len(existing))) == QMessageBox.StandardButton.Yes:
            self._add_images(existing)
            self.append_log(self.t("restored"))
