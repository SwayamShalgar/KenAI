from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QSequentialAnimationGroup, Qt
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QWidget


def fade_in(widget: QWidget, duration: int = 220) -> QPropertyAnimation:
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    effect.setOpacity(0.0)
    animation = QPropertyAnimation(effect, b"opacity", widget)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setDuration(duration)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    return animation


def breathing_animation(widget: QWidget, minimum: float = 0.94, maximum: float = 1.04) -> QSequentialAnimationGroup:
    group = QSequentialAnimationGroup(widget)
    grow = QPropertyAnimation(widget, b"windowOpacity", widget)
    grow.setDuration(900)
    grow.setStartValue(minimum)
    grow.setEndValue(maximum)
    grow.setEasingCurve(QEasingCurve.Type.InOutSine)
    shrink = QPropertyAnimation(widget, b"windowOpacity", widget)
    shrink.setDuration(900)
    shrink.setStartValue(maximum)
    shrink.setEndValue(minimum)
    shrink.setEasingCurve(QEasingCurve.Type.InOutSine)
    group.addAnimation(grow)
    group.addAnimation(shrink)
    group.setLoopCount(-1)
    return group


def ease(value: float, target: float, rate: float = 0.12) -> float:
    return value + (target - value) * rate


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(value, upper))