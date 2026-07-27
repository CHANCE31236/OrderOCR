from __future__ import annotations

import sys
import tempfile
from pathlib import Path


def _configure_frozen_path() -> None:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def _self_test() -> int:
    """供打包验收使用：验证 exe 内的 OpenCV、RapidOCR、规则和资源文件。"""
    import cv2
    import numpy as np

    from src.business.quantity_rules import calculate_final_quantity
    from src.ocr.local_ocr import LocalOCR
    from src.utils.paths import resource_path

    image = np.full((180, 850, 3), 255, np.uint8)
    cv2.putText(image, "00001535  10", (30, 115), cv2.FONT_HERSHEY_SIMPLEX, 1.7, (0, 0, 0), 3, cv2.LINE_AA)
    if not LocalOCR().recognize(image):
        raise RuntimeError("打包后的 RapidOCR 自检失败")
    if calculate_final_quantity(10, "full_circle").final_box_count != 10:
        raise RuntimeError("规则引擎自检失败")
    for required_resource in (resource_path("config", "settings.json"), resource_path("assets", "language.svg")):
        if not required_resource.exists():
            raise RuntimeError(f"配置资源未打包：{required_resource.name}")
    with tempfile.TemporaryDirectory(prefix="orderocr_selftest_"):
        pass
    return 0


def main() -> int:
    _configure_frozen_path()
    if "--self-test" in sys.argv:
        return _self_test()
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from src.storage.settings_store import SettingsStore
    from src.ui.main_window import MainWindow
    from src.utils.paths import resource_path

    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    app.setApplicationName("订单纸单识别器")
    app.setOrganizationName("OrderOCR")
    icon = resource_path("assets", "app.ico")
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    store = SettingsStore()
    window = MainWindow(store)
    window.show()
    if not store.get_api_key():
        window.open_settings(required=True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
