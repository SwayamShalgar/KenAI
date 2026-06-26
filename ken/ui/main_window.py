from __future__ import annotations

from dataclasses import asdict

from PyQt6.QtCore import QPoint, QPropertyAnimation, QEasingCurve, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QIcon, QMouseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QDialog,
    QLineEdit,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QPlainTextEdit,
    QWidget,
)

from ken.config import config, resolve_model_name
from ken.ui.animations import fade_in
from ken.ui.bridge import AssistantBridge
from ken.ui.chat_widget import ChatWidget
from ken.ui.orb_widget import OrbState, OrbWidget
from ken.ui.settings_dialog import SettingsDialog, UiSettings
from ken.ui.themes import build_stylesheet, palette_for_theme, theme_for_name
from ken.ui.visualizer import VoiceVisualizer


class TitleBar(QWidget):
    minimize_requested = pyqtSignal()
    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos: QPoint | None = None
        self.setFixedHeight(56)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 10, 12, 10)
        layout.setSpacing(10)

        self.title = QLabel("Ken AI Assistant")
        self.title.setObjectName("TitleLabel")
        self.subtitle = QLabel("Voice-first desktop companion")
        self.subtitle.setObjectName("MutedLabel")

        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        title_box.addWidget(self.title)
        title_box.addWidget(self.subtitle)
        layout.addLayout(title_box)
        layout.addStretch(1)

        self.min_button = QPushButton("–")
        self.min_button.setFixedSize(38, 32)
        self.min_button.clicked.connect(self.minimize_requested.emit)
        layout.addWidget(self.min_button)

        self.close_button = QPushButton("✕")
        self.close_button.setFixedSize(38, 32)
        self.close_button.setObjectName("DangerButton")
        self.close_button.clicked.connect(self.close_requested.emit)
        layout.addWidget(self.close_button)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None


class KenMainWindow(QMainWindow):
    def __init__(self, *, voice_mode: bool = False, mode: str | None = None, model: str | None = None, benchmark: bool = False):
        super().__init__()
        self.setWindowTitle("Ken AI Assistant")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(1400, 920)

        self._settings = SettingsDialog.load()
        self._bridge = AssistantBridge(
            voice_mode=voice_mode,
            mode=mode or config.default_mode,
            model=model or config.model,
            benchmark=benchmark,
        )
        self._bridge.state_changed.connect(self._set_orb_state)
        self._bridge.status_changed.connect(self._set_status)
        self._bridge.level_changed.connect(self._set_level)
        self._bridge.error_occurred.connect(self._handle_error)
        self._bridge.user_message.connect(self._on_user_message)
        self._bridge.assistant_started.connect(self._on_assistant_started)
        self._bridge.assistant_chunk.connect(self._on_assistant_chunk)
        self._bridge.assistant_finished.connect(self._on_assistant_finished)
        self._bridge.conversation_cleared.connect(self._on_conversation_cleared)

        self._root = QFrame(self)
        self._root.setObjectName("RootPanel")
        self.setCentralWidget(self._root)

        self._build_layout()
        self._apply_settings(self._settings)
        fade_in(self._root, 260)

    def _build_layout(self):
        outer = QVBoxLayout(self._root)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(14)

        self.title_bar = TitleBar(self)
        self.title_bar.minimize_requested.connect(self.showMinimized)
        self.title_bar.close_requested.connect(self.close)
        outer.addWidget(self.title_bar)

        body = QGridLayout()
        body.setSpacing(14)
        outer.addLayout(body, 1)

        left_card = QFrame()
        left_card.setObjectName("GlassCard")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(14)

        self.status_label = QLabel("Idle")
        self.status_label.setObjectName("StatusPill")
        left_layout.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignLeft)

        self.orb = OrbWidget()
        self.orb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout.addWidget(self.orb, 1)

        self.visualizer = VoiceVisualizer()
        left_layout.addWidget(self.visualizer)

        quick_actions = QFrame()
        quick_layout = QHBoxLayout(quick_actions)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(10)

        self.listen_button = QPushButton("Start Listening")
        self.listen_button.setObjectName("PrimaryButton")
        self.listen_button.clicked.connect(self._start_listening)
        quick_layout.addWidget(self.listen_button)

        self.stop_button = QPushButton("Stop Listening")
        self.stop_button.clicked.connect(self._stop_listening)
        self.stop_button.setEnabled(False)
        quick_layout.addWidget(self.stop_button)

        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self._open_settings)
        quick_layout.addWidget(self.settings_button)

        self.history_button = QPushButton("History")
        self.history_button.clicked.connect(self._focus_history)
        quick_layout.addWidget(self.history_button)

        self.clear_button = QPushButton("Clear Chat")
        self.clear_button.clicked.connect(self._clear_chat)
        quick_layout.addWidget(self.clear_button)

        self.exit_button = QPushButton("Exit")
        self.exit_button.setObjectName("DangerButton")
        self.exit_button.clicked.connect(self.close)
        quick_layout.addWidget(self.exit_button)

        left_layout.addWidget(quick_actions)

        self.input_row = QFrame()
        input_layout = QHBoxLayout(self.input_row)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(10)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a message and press Enter")
        self.input.returnPressed.connect(self._send_typed_message)
        input_layout.addWidget(self.input, 1)
        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("PrimaryButton")
        self.send_button.clicked.connect(self._send_typed_message)
        input_layout.addWidget(self.send_button)
        self.chat = ChatWidget()
        
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(14)
        right_layout.addWidget(self.chat, 1)
        right_layout.addWidget(self.input_row, 0)

        body.addWidget(left_card, 0, 0)
        body.addWidget(right_panel, 0, 1)
        body.setColumnStretch(0, 4)
        body.setColumnStretch(1, 8)

    def _apply_settings(self, settings: UiSettings):
        theme = theme_for_name(settings.theme)
        app = QApplication.instance()
        if app is not None:
            app.setPalette(palette_for_theme(theme))
            app.setStyleSheet(build_stylesheet(theme, settings.animation_intensity))
        self.orb.set_animation_intensity(settings.animation_intensity)

    def _set_orb_state(self, state: str):
        mapping = {
            "idle": OrbState.idle,
            "listening": OrbState.listening,
            "processing": OrbState.processing,
            "speaking": OrbState.speaking,
            "error": OrbState.error,
        }
        self.orb.set_state(mapping.get(state, OrbState.idle))

    def _set_status(self, text: str):
        self.status_label.setText(text)

    def _set_level(self, value: float):
        self.visualizer.set_level(value)
        self.orb.set_level(value)

    def _on_user_message(self, text: str):
        self.chat.add_user_message(text)

    def _on_assistant_started(self):
        self.chat.begin_assistant_message()

    def _on_assistant_chunk(self, chunk: str):
        self.chat.append_assistant_chunk(chunk)

    def _on_assistant_finished(self, text: str):
        self.chat.finish_assistant_message(text)

    def _on_conversation_cleared(self):
        self.chat.clear_messages()

    def _handle_error(self, message: str):
        self.status_label.setText("Error")
        self.orb.set_state(OrbState.error)
        self.chat.add_user_message(f"Error: {message}")

    def _start_listening(self):
        self._bridge.start_listening()
        self.listen_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def _stop_listening(self):
        self._bridge.stop_listening()
        self.listen_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self._set_status("Idle")

    def _open_settings(self):
        dialog = SettingsDialog(self._settings, self)
        if dialog.exec():
            self._settings = dialog._settings
            self._apply_settings(self._settings)

    def _focus_history(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Session History")
        dialog.resize(820, 620)
        layout = QVBoxLayout(dialog)
        viewer = QPlainTextEdit(dialog)
        viewer.setReadOnly(True)
        lines = []
        for item in self._bridge.conversation:
            lines.append(f"{item.role.title()}: {item.text}")
        viewer.setPlainText("\n\n".join(lines) or "No conversation yet.")
        layout.addWidget(viewer)
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec()

    def _clear_chat(self):
        self._bridge.clear_chat()

    def _send_typed_message(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self._bridge.submit_text(text, source="typed")

    def closeEvent(self, event):
        self._bridge.shutdown()
        super().closeEvent(event)


def run_app(voice_mode: bool = False, mode: str | None = None, model: str | None = None, benchmark: bool = False):
    app = QApplication.instance() or QApplication([])
    window = KenMainWindow(voice_mode=voice_mode, mode=mode, model=model, benchmark=benchmark)
    window.show()
    if voice_mode:
        window._start_listening()
    return app.exec()


__all__ = ["KenMainWindow", "run_app"]