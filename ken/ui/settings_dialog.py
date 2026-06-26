from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
)


@dataclass
class UiSettings:
    theme: str = "dark"
    animation_intensity: int = 72
    microphone: str = ""
    speaker: str = ""
    wake_word_enabled: bool = False
    startup_on_boot: bool = False


def _autostart_path() -> Path:
    return Path.home() / ".config" / "autostart" / "ken.desktop"


def _available_devices(kind: str) -> list[str]:
    try:
        import sounddevice as sd
    except Exception:
        return []

    devices = []
    for device in sd.query_devices():
        if kind == "input" and device.get("max_input_channels", 0) > 0:
            devices.append(str(device.get("name", "Unknown input")))
        elif kind == "output" and device.get("max_output_channels", 0) > 0:
            devices.append(str(device.get("name", "Unknown output")))
    return devices


def _sync_autostart(enabled: bool):
    path = _autostart_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not enabled:
        if path.exists():
            path.unlink()
        return
    path.write_text(
        "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                "Name=Ken Assistant",
                f"Exec={os.environ.get('KEN_GUI_AUTOSTART_CMD', 'ken gui')}",
                "X-GNOME-Autostart-enabled=true",
                "NoDisplay=false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


class SettingsDialog(QDialog):
    def __init__(self, settings: UiSettings | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ken Settings")
        self.setModal(True)
        self._settings = settings or UiSettings()

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.setCurrentText(self._settings.theme)

        self.animation_slider = QSlider(Qt.Orientation.Horizontal)
        self.animation_slider.setRange(25, 100)
        self.animation_slider.setValue(self._settings.animation_intensity)

        self.microphone_combo = QComboBox()
        self.microphone_combo.setEditable(True)
        self.microphone_combo.addItems(_available_devices("input"))
        if not self.microphone_combo.count():
            self.microphone_combo.addItem("Default microphone")
        if self._settings.microphone:
            self.microphone_combo.setCurrentText(self._settings.microphone)

        self.speaker_combo = QComboBox()
        self.speaker_combo.setEditable(True)
        self.speaker_combo.addItems(_available_devices("output"))
        if not self.speaker_combo.count():
            self.speaker_combo.addItem("Default speaker")
        if self._settings.speaker:
            self.speaker_combo.setCurrentText(self._settings.speaker)

        self.wake_word_checkbox = QCheckBox("Enable wake word")
        self.wake_word_checkbox.setChecked(self._settings.wake_word_enabled)

        self.startup_checkbox = QCheckBox("Start on boot")
        self.startup_checkbox.setChecked(self._settings.startup_on_boot)

        form.addRow("Theme", self.theme_combo)
        form.addRow("Animation intensity", self.animation_slider)
        form.addRow("Microphone", self.microphone_combo)
        form.addRow("Speaker", self.speaker_combo)
        form.addRow("", self.wake_word_checkbox)
        form.addRow("", self.startup_checkbox)
        layout.addLayout(form)

        note = QLabel("Wake word and device selection are stored locally for the UI layer.")
        note.setWordWrap(True)
        note.setObjectName("MutedLabel")
        layout.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        self._settings.theme = self.theme_combo.currentText().strip() or "dark"
        self._settings.animation_intensity = self.animation_slider.value()
        self._settings.microphone = self.microphone_combo.currentText().strip()
        self._settings.speaker = self.speaker_combo.currentText().strip()
        self._settings.wake_word_enabled = self.wake_word_checkbox.isChecked()
        self._settings.startup_on_boot = self.startup_checkbox.isChecked()
        _sync_autostart(self._settings.startup_on_boot)

        store = QSettings("Ken", "Ken")
        for key, value in asdict(self._settings).items():
            store.setValue(key, value)
        super().accept()

    @staticmethod
    def load() -> UiSettings:
        store = QSettings("Ken", "Ken")
        return UiSettings(
            theme=store.value("theme", "dark"),
            animation_intensity=int(store.value("animation_intensity", 72)),
            microphone=store.value("microphone", ""),
            speaker=store.value("speaker", ""),
            wake_word_enabled=store.value("wake_word_enabled", False, type=bool),
            startup_on_boot=store.value("startup_on_boot", False, type=bool),
        )


__all__ = ["SettingsDialog", "UiSettings"]