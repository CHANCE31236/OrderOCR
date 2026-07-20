from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", str(Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts"))

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import QApplication, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from src.ocr.schemas import ReviewedRow, RowObservation
from src.storage.database import Database
from src.ui.main_window import MainWindow


OUTPUT = ROOT / "assets" / "screenshots"


class DemoStore:
    def __init__(self) -> None:
        self.values = {
            "language": "en",
            "vision_model": "vision-model",
            "verification_model": "vision-model",
            "minimum_confidence": 0.90,
            "save_row_crops": True,
            "output_directory": str(Path.home() / "Desktop" / "OrderExcel"),
            "api_retry_count": 4,
            "max_concurrency": 2,
            "auto_delete_task_images": False,
        }

    def get(self, key: str, default=None):
        return self.values.get(key, default)

    def update(self, values: dict) -> None:
        self.values.update(values)

    def as_dict(self) -> dict:
        return dict(self.values)

    def get_api_key(self) -> str:
        return "demo-key-not-used"

    def set_api_key(self, _value: str) -> None:
        return None


def create_demo_document(path: Path) -> None:
    image = QImage(1000, 1280, QImage.Format.Format_RGB32)
    image.fill(QColor("#f8f6f0"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor("#243447"), 3))
    painter.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
    painter.drawText(55, 85, "DEMO DELIVERY NOTE")
    painter.setFont(QFont("Segoe UI", 17))
    painter.drawText(55, 135, "Order: DEMO-2026-001")
    painter.drawText(720, 135, "Page 1 / 1")
    left, top, right, bottom = 55, 210, 945, 930
    painter.drawRect(left, top, right - left, bottom - top)
    columns = [left, 140, 520, 700, 820, right]
    for x in columns[1:-1]:
        painter.drawLine(x, top, x, bottom)
    row_height = 120
    for y in range(top + row_height, bottom, row_height):
        painter.drawLine(left, y, right, y)
    headers = [(72, "Row"), (170, "Product code"), (555, "Description"), (725, "Boxes"), (842, "Quantity")]
    painter.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
    for x, text in headers:
        painter.drawText(x, top + 75, text)
    rows = [
        ("1", "00001535", "Demo product A", "5", "150"),
        ("2", "DV1731-01", "Demo product B", "8", "240"),
        ("3", "FT7850-1", "Demo product C", "3", "90"),
        ("4", "ABC-0042", "Demo product D", "12", "360"),
    ]
    painter.setFont(QFont("Segoe UI", 15))
    for index, row in enumerate(rows, start=1):
        y = top + row_height * index + 75
        for x, text in zip((88, 170, 550, 750, 860), row):
            painter.drawText(x, y, text)
    painter.setPen(QPen(QColor("#d94841"), 6))
    painter.drawEllipse(724, top + row_height + 30, 100, 66)
    painter.setPen(QPen(QColor("#276fbf"), 5))
    painter.drawEllipse(724, top + row_height * 2 + 30, 100, 66)
    painter.setFont(QFont("Segoe Script", 22, QFont.Weight.Bold))
    painter.drawText(734, top + row_height * 3 + 105, "6")
    painter.end()
    image.save(str(path))


def demo_rows(row_crop: str) -> list[ReviewedRow]:
    values = [
        (1, "00001535", 5, "full_circle", None, 5, 0.99, "auto_confirmed", "Closed circle confirmed by both recognition passes"),
        (2, "DV1731-01", 8, "full_circle", None, 8, 0.94, "check_recommended", "Circle edge is slightly faint; review recommended"),
        (3, "FT7850-1", 3, "uncertain", 6, None, 0.71, "manual_review_required", "Handwritten override association is uncertain"),
        (4, "ABC-0042", 12, "no_circle", None, 0, 0.98, "auto_confirmed", "No closed circle detected"),
    ]
    rows: list[ReviewedRow] = []
    for number, code, printed, circle, override, final, confidence, status, reason in values:
        observation = RowObservation(
            row_number=number,
            product_code=code,
            printed_box_count=printed,
            printed_total_quantity=printed * 30,
            circle_status=circle,
            handwritten_override=override,
            override_is_clearly_associated=False,
            calculated_final_box_count=final,
            product_code_confidence=confidence,
            circle_confidence=confidence,
            overall_confidence=confidence,
            needs_review=status != "auto_confirmed",
            reason=reason,
            row_crop=row_crop,
        )
        rows.append(
            ReviewedRow(
                observation=observation,
                final_box_count=final,
                needs_review=status != "auto_confirmed",
                status=status,
                review_reason=reason,
            )
        )
    return rows


def save_window_screenshots(app: QApplication, document: Path) -> None:
    Database.incomplete_tasks = lambda _self: []
    window = MainWindow(DemoStore())
    window.resize(1500, 940)
    window.order_list.blockSignals(True)
    window.order_list.addItem("DEMO-2026-001")
    window.order_list.setCurrentRow(0)
    window.order_list.blockSignals(False)
    window.page_list.blockSignals(True)
    window.page_list.addItem("1/1 - demo-delivery-note.png")
    window.page_list.setCurrentRow(0)
    window.page_list.blockSignals(False)
    window.image_paths = [str(document)]
    window.original_view.set_image(document)
    window.corrected_view.set_image(document)
    window.row_view.set_image(document)
    window.table.set_rows(demo_rows(str(document)))
    window.progress.setRange(0, 4)
    window.progress.setValue(4)
    window.progress.setFormat("Recognition complete | 8 API calls")
    window.log.setPlainText("Recognition complete: 1 page, 1 order.\nReview the highlighted rows before export.")
    window.show()
    app.processEvents()
    window.tabs.setCurrentIndex(0)
    app.processEvents()
    window.grab().save(str(OUTPUT / "main-window.png"))
    window.tabs.setCurrentIndex(1)
    window.table.selectRow(1)
    app.processEvents()
    window.grab().save(str(OUTPUT / "recognition-results.png"))
    window.tabs.setCurrentIndex(2)
    window.table.selectRow(2)
    app.processEvents()
    window.grab().save(str(OUTPUT / "manual-review.png"))
    window.close()


def save_excel_example(app: QApplication) -> None:
    widget = QWidget()
    widget.setWindowTitle("OrderOCR Excel output example")
    widget.resize(920, 400)
    layout = QVBoxLayout(widget)
    heading = QLabel("Order DEMO-2026-001.xlsx")
    heading.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
    subtitle = QLabel("Example data only — no customer information")
    subtitle.setStyleSheet("color: #5f6b76;")
    table = QTableWidget(4, 2)
    table.setHorizontalHeaderLabels(["Product code", "Box count"])
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setStretchLastSection(True)
    table.setColumnWidth(0, 600)
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setStyleSheet(
        "QHeaderView::section { background: #1f5f8b; color: white; font-weight: 600; padding: 8px; }"
        "QTableWidget { gridline-color: #c8d2dc; font-size: 15px; }"
    )
    for row, values in enumerate((("00001535", "5"), ("DV1731-01", "8"), ("FT7850-1", "6"), ("ABC-0042", "0"))):
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            if column == 1:
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(row, column, item)
    layout.addWidget(heading)
    layout.addWidget(subtitle)
    layout.addWidget(table)
    widget.show()
    app.processEvents()
    widget.grab().save(str(OUTPUT / "excel-output.png"))
    widget.close()


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    with tempfile.TemporaryDirectory(prefix="orderocr_readme_") as temporary:
        document = Path(temporary) / "demo-delivery-note.png"
        create_demo_document(document)
        save_window_screenshots(app, document)
        save_excel_example(app)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
