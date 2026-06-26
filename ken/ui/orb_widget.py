from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import QPointF, QTimer, Qt, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QRadialGradient
from PyQt6.QtWidgets import QWidget

from ken.ui.animations import clamp, ease


class OrbState(str, Enum):
    idle = "idle"
    listening = "listening"
    processing = "processing"
    speaking = "speaking"
    error = "error"


@dataclass
class Particle:
    angle: float
    radius: float
    speed: float
    size: float


class OrbWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setSizePolicy(
            self.sizePolicy().horizontalPolicy(),
            self.sizePolicy().verticalPolicy(),
        )
        self._state = OrbState.idle
        self._level = 0.0
        self._target_level = 0.0
        self._glow = 0.26
        self._time = 0.0
        self._animation_intensity = 72
        self._particles = [
            Particle(
                angle=random.uniform(0, math.tau),
                radius=random.uniform(118, 148),
                speed=random.uniform(0.12, 0.32),
                size=random.uniform(2.2, 4.8),
            )
            for _ in range(16)
        ]
        self._pulse = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def set_animation_intensity(self, value: int):
        self._animation_intensity = max(1, min(100, value))
        self.update()

    def set_state(self, state: OrbState | str):
        if isinstance(state, str):
            state = OrbState(state)
        if state != self._state:
            self._state = state
            self.update()

    def state(self) -> OrbState:
        return self._state

    def set_level(self, value: float):
        self._target_level = clamp(value, 0.0, 1.0)

    def level(self) -> float:
        return self._level

    def _tick(self):
        self._time += 0.016
        self._level = ease(self._level, self._target_level, 0.18)
        if self._state == OrbState.idle:
            self._pulse = (math.sin(self._time * 2.2) + 1.0) * 0.5
        elif self._state == OrbState.listening:
            self._pulse = (math.sin(self._time * 6.5) + 1.0) * 0.5
        elif self._state == OrbState.processing:
            self._pulse = (math.sin(self._time * 10.0) + 1.0) * 0.5
        elif self._state == OrbState.speaking:
            self._pulse = (math.sin(self._time * 8.0) + 1.0) * 0.5
        else:
            self._pulse = 0.7 + 0.3 * math.sin(self._time * 18.0)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        center_pt = self.rect().center()
        center = QPointF(float(center_pt.x()), float(center_pt.y()))
        base_radius = min(self.width(), self.height()) * 0.22
        activity = clamp(max(self._level, self._pulse * 0.45))
        scale = 1.0 + activity * 0.17
        if self._state == OrbState.processing:
            scale += 0.05
        elif self._state == OrbState.speaking:
            scale += activity * 0.08
        elif self._state == OrbState.error:
            scale -= 0.04

        orb_radius = base_radius * scale
        halo_radius = orb_radius * (2.3 + activity * 0.5)

        outer = QRadialGradient(center, float(halo_radius))
        outer.setColorAt(0.0, QColor(120, 216, 255, int(110 + 100 * activity)))
        outer.setColorAt(0.35, QColor(90, 120, 255, int(70 + 60 * activity)))
        outer.setColorAt(0.7, QColor(20, 24, 42, 28))
        outer.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(outer)
        painter.drawEllipse(center, float(halo_radius), float(halo_radius))

        fill_center = QPointF(center.x() - (-orb_radius * 0.16), center.y() - (orb_radius * 0.22))
        fill = QRadialGradient(fill_center, float(orb_radius * 1.4))
        if self._state == OrbState.error:
            fill.setColorAt(0.0, QColor(255, 144, 172))
            fill.setColorAt(0.55, QColor(210, 68, 113))
            fill.setColorAt(1.0, QColor(71, 19, 48))
        elif self._state == OrbState.speaking:
            fill.setColorAt(0.0, QColor(192, 236, 255))
            fill.setColorAt(0.5, QColor(88, 195, 255))
            fill.setColorAt(1.0, QColor(32, 102, 176))
        else:
            fill.setColorAt(0.0, QColor(213, 249, 255))
            fill.setColorAt(0.35, QColor(112, 214, 255))
            fill.setColorAt(1.0, QColor(32, 82, 170))

        path = QPainterPath()
        path.addEllipse(center, float(orb_radius), float(orb_radius))
        painter.setBrush(fill)
        painter.drawPath(path)

        gloss_center = QPointF(center.x() - (orb_radius * 0.3), center.y() - (orb_radius * 0.42))
        gloss = QRadialGradient(gloss_center, float(orb_radius * 1.2))
        gloss.setColorAt(0.0, QColor(255, 255, 255, 150))
        gloss.setColorAt(0.18, QColor(255, 255, 255, 56))
        gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(gloss)
        painter.drawEllipse(center, float(orb_radius * 0.74), float(orb_radius * 0.74))

        ring_color = QColor(120, 216, 255, 125 if self._state != OrbState.error else 90)
        ring_pen = QPen(ring_color, 2.0)
        painter.setPen(ring_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        ring_radius = orb_radius * (1.28 + activity * 0.12)
        painter.drawEllipse(center, float(ring_radius), float(ring_radius))

        second_pen = QPen(QColor(255, 255, 255, 58), 1.2)
        painter.setPen(second_pen)
        painter.drawEllipse(center, float(ring_radius * 1.12), float(ring_radius * 1.12))

        painter.setPen(Qt.PenStyle.NoPen)
        particle_color = QColor(180, 238, 255, int(80 + 150 * activity))
        for index, particle in enumerate(self._particles):
            angle = particle.angle + self._time * particle.speed * (1.0 + activity * 0.4)
            px = center.x() + math.cos(angle) * particle.radius
            py = center.y() + math.sin(angle) * particle.radius
            if self._state == OrbState.error and index % 3 == 0:
                particle_color = QColor(255, 126, 152, 140)
            painter.setBrush(particle_color)
            size = particle.size * (0.9 + activity * 0.85)
            painter.drawEllipse(QPointF(px, py), float(size), float(size))

        if self._state == OrbState.processing:
            swirl_pen = QPen(QColor(120, 216, 255, 120), 3.0)
            painter.setPen(swirl_pen)
            swirl_radius = orb_radius * 1.52
            start = int((self._time * 100) % 360) * 16
            painter.drawArc(
                int(center.x() - swirl_radius),
                int(center.y() - swirl_radius),
                int(swirl_radius * 2),
                int(swirl_radius * 2),
                start,
                int(110 * 16),
            )

    def sizeHint(self):
        return self.minimumSize()


__all__ = ["OrbWidget", "OrbState"]