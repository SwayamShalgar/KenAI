from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QLinearGradient
from PyQt6.QtWidgets import QWidget

from ken.ui.animations import clamp, ease


class VoiceVisualizer(QWidget):
    def __init__(self, parent=None, bars: int = 24):
        super().__init__(parent)
        self.setMinimumHeight(92)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._bars = [0.08 for _ in range(bars)]
        self._target_bars = [0.08 for _ in range(bars)]
        self._level = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def set_level(self, value: float):
        self._level = clamp(value)
        width = len(self._target_bars)
        for index in range(width):
            offset = abs(index - (width - 1) / 2) / max(1, width / 2)
            shaped = max(0.04, self._level * (1.0 - offset * 0.58))
            self._target_bars[index] = shaped

    def _tick(self):
        for index, value in enumerate(self._bars):
            self._bars[index] = ease(value, self._target_bars[index], 0.16)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(12, 16, -12, -16)
        bar_width = rect.width() / max(1, len(self._bars))
        tl = rect.topLeft()
        br = rect.bottomRight()
        gradient = QLinearGradient(float(tl.x()), float(tl.y()), float(br.x()), float(br.y()))
        gradient.setColorAt(0.0, QColor(120, 216, 255, 220))
        gradient.setColorAt(0.6, QColor(94, 129, 255, 220))
        gradient.setColorAt(1.0, QColor(193, 110, 255, 220))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)

        for index, value in enumerate(self._bars):
            height = max(4, rect.height() * value)
            x = rect.left() + index * bar_width + bar_width * 0.16
            y = rect.center().y() - height * 0.5
            r = QRectF(float(x), float(y), float(bar_width * 0.7), float(height))
            painter.drawRoundedRect(r, 5.0, 5.0)

        painter.setPen(QPen(QColor(255, 255, 255, 24), 1.0))
        painter.drawRoundedRect(rect, 16, 16)


__all__ = ["VoiceVisualizer"]