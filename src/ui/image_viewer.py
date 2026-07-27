from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy


class ImageViewer(QLabel):
    def __init__(self, placeholder: str = "暂无图片", parent=None) -> None:
        super().__init__(placeholder, parent)
        self._placeholder = placeholder
        self._pixmap = QPixmap()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(260, 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("QLabel { background:#18212f; color:#9aa8bb; border:1px solid #344256; border-radius:6px; }")

    def set_image(self, path: str | Path | None) -> None:
        if not path or not Path(path).exists():
            self._pixmap = QPixmap()
            self.setText(self._placeholder)
            return
        self._pixmap = QPixmap(str(path))
        self.setText("")
        self._refresh()

    def set_placeholder(self, text: str) -> None:
        self._placeholder = text
        if self._pixmap.isNull():
            self.setText(text)

    def _refresh(self) -> None:
        if not self._pixmap.isNull():
            self.setPixmap(self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh()
