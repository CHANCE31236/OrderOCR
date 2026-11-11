from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

import cv2
import numpy as np


@dataclass(slots=True)
class OCRLine:
    box: list[list[float]]
    text: str
    confidence: float


class LocalOCR:
    _engine = None
    _lock = Lock()

    def _get_engine(self):
        if self.__class__._engine is None:
            with self._lock:
                if self.__class__._engine is None:
                    from rapidocr_onnxruntime import RapidOCR

                    self.__class__._engine = RapidOCR()
        return self.__class__._engine

    def recognize(self, image: np.ndarray) -> list[OCRLine]:
        result, _elapsed = self._get_engine()(image)
        lines: list[OCRLine] = []
        for item in result or []:
            if len(item) >= 3:
                box, text, confidence = item[0], item[1], item[2]
                lines.append(OCRLine(np.asarray(box).astype(float).tolist(), str(text), float(confidence)))
        return lines

    def text_score(self, image: np.ndarray) -> float:
        height, width = image.shape[:2]
        scale = min(1.0, 1400 / max(height, width))
        preview = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        lines = self.recognize(preview)
        return sum(max(0.0, line.confidence - 0.35) * min(len(line.text), 20) for line in lines)

    def as_dicts(self, image: np.ndarray) -> list[dict]:
        return [{"box": line.box, "text": line.text, "confidence": line.confidence} for line in self.recognize(image)]

