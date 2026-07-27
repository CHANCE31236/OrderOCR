from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem

from src.ocr.schemas import CircleStatus, ReviewedRow
from src.ui.i18n import normalize_language, translate


class ReviewTable(QTableWidget):
    row_edited = Signal(dict)
    HEADER_KEYS = ["row_number", "product_code", "printed_boxes", "circle_status", "handwritten", "final_boxes", "code_confidence", "circle_confidence", "status", "reason"]
    EDITABLE = {1, 2, 3, 4, 5}

    def __init__(self, language: str = "zh_CN", parent=None) -> None:
        super().__init__(0, len(self.HEADER_KEYS), parent)
        self.language = normalize_language(language)
        self.setHorizontalHeaderLabels([translate(self.language, key) for key in self.HEADER_KEYS])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self._rows: list[ReviewedRow] = []
        self._loading = False
        self.itemChanged.connect(self._on_item_changed)

    def set_language(self, language: str) -> None:
        self.language = normalize_language(language)
        self.setHorizontalHeaderLabels([translate(self.language, key) for key in self.HEADER_KEYS])
        self.set_rows(self._rows)

    def _circle_label(self, status: str) -> str:
        return translate(self.language, {"full_circle": "circle_full", "no_circle": "circle_none", "uncertain": "circle_uncertain"}.get(status, status))

    def _circle_value(self, label: str) -> CircleStatus:
        label = label.strip()
        for value, key in (("full_circle", "circle_full"), ("no_circle", "circle_none"), ("uncertain", "circle_uncertain")):
            if label in {value, translate(self.language, key)}:
                return CircleStatus(value)
        return CircleStatus(label)

    def _status_label(self, status: str) -> str:
        key = {"需要人工确认": "status_review", "建议检查": "status_check", "已自动确认": "status_auto", "人工已确认": "status_manual"}.get(status)
        return translate(self.language, key) if key else status

    def set_rows(self, rows: list[ReviewedRow]) -> None:
        self._loading = True
        self._rows = rows
        self.setRowCount(len(rows))
        for index, row in enumerate(rows):
            obs = row.observation
            values = [
                obs.row_number,
                obs.product_code,
                "" if obs.printed_box_count is None else obs.printed_box_count,
                self._circle_label(str(obs.circle_status)),
                "" if obs.handwritten_override is None else obs.handwritten_override,
                "" if row.final_box_count is None else row.final_box_count,
                f"{obs.product_code_confidence:.2f}",
                f"{obs.circle_confidence:.2f}",
                self._status_label(row.status),
                row.review_reason,
            ]
            color = QColor("#d96c6c") if row.status == "需要人工确认" else QColor("#d6b95f") if row.status == "建议检查" else QColor("#72c98f")
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column not in self.EDITABLE:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setBackground(color)
                self.setItem(index, column, item)
        self._loading = False

    def current_reviewed_row(self) -> ReviewedRow | None:
        index = self.currentRow()
        return self._rows[index] if 0 <= index < len(self._rows) else None

    def refresh_row(self, index: int) -> None:
        if 0 <= index < len(self._rows):
            current = self.currentRow()
            self.set_rows(self._rows)
            if current >= 0:
                self.selectRow(current)

    @staticmethod
    def _optional_int(text: str) -> int | None:
        text = text.strip()
        if not text:
            return None
        value = int(text)
        if value < 0:
            raise ValueError("箱数不能为负数")
        return value

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading or item.column() not in self.EDITABLE:
            return
        row_index = item.row()
        model = self._rows[row_index]
        before = model.model_dump(mode="json")
        try:
            if item.column() == 1:
                model.observation.product_code = item.text()
            elif item.column() == 2:
                model.observation.printed_box_count = self._optional_int(item.text())
            elif item.column() == 3:
                model.observation.circle_status = self._circle_value(item.text())
            elif item.column() == 4:
                model.observation.handwritten_override = self._optional_int(item.text())
                model.observation.override_is_clearly_associated = model.observation.handwritten_override is not None
            elif item.column() == 5:
                model.final_box_count = self._optional_int(item.text())
            model.needs_review = True
            model.manually_confirmed = False
            model.status = "需要人工确认"
            model.review_reason = "人工修改后等待确认"
            self.row_edited.emit({"row_index": row_index, "before": before, "after": model.model_dump(mode="json")})
        except (ValueError, TypeError):
            self.set_rows(self._rows)
