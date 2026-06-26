from __future__ import annotations

import html
import re
from dataclasses import dataclass

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextCursor, QTextDocument
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ken.ui.animations import fade_in


CODE_BLOCK_RE = re.compile(r"```(?P<lang>[a-zA-Z0-9_+-]*)\n(?P<code>.*?)```", re.DOTALL)


class SimpleCodeHighlighter(QSyntaxHighlighter):
    def __init__(self, document: QTextDocument, language: str = ""):
        super().__init__(document)
        self._language = language.lower().strip()
        self._keyword_format = QTextCharFormat()
        self._keyword_format.setForeground(QColor("#7CDFFF"))
        self._keyword_format.setFontWeight(QFont.Weight.Bold)
        self._string_format = QTextCharFormat()
        self._string_format.setForeground(QColor("#B1F7B0"))
        self._comment_format = QTextCharFormat()
        self._comment_format.setForeground(QColor("#7B8AAB"))
        self._comment_format.setFontItalic(True)

    def highlightBlock(self, text: str):
        if self._language in {"bash", "sh", "shell", "zsh"}:
            for keyword in ["cd", "ls", "sudo", "pip", "uv", "git", "python", "ollama"]:
                index = text.find(keyword)
                while index >= 0:
                    self.setFormat(index, len(keyword), self._keyword_format)
                    index = text.find(keyword, index + len(keyword))
            if text.lstrip().startswith("#"):
                self.setFormat(0, len(text), self._comment_format)
            return

        if self._language in {"python", "py"}:
            for keyword in ["def", "class", "return", "import", "from", "async", "await", "if", "else", "for", "while", "try", "except", "with", "as"]:
                index = text.find(keyword)
                while index >= 0:
                    self.setFormat(index, len(keyword), self._keyword_format)
                    index = text.find(keyword, index + len(keyword))
            if "#" in text:
                comment_index = text.find("#")
                self.setFormat(comment_index, len(text) - comment_index, self._comment_format)
            for match in re.finditer(r'".*?"|\'.*?\'', text):
                self.setFormat(match.start(), match.end() - match.start(), self._string_format)
            return

        for match in re.finditer(r'".*?"|\'.*?\'', text):
            self.setFormat(match.start(), match.end() - match.start(), self._string_format)


class CodeBlockWidget(QFrame):
    def __init__(self, code: str, language: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("GlassCard")
        self._code = code.rstrip()
        self._language = language.strip()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        header = QHBoxLayout()
        language_label = QLabel(self._language.upper() if self._language else "CODE")
        language_label.setObjectName("MutedLabel")
        language_label.setStyleSheet("font-size: 11px; letter-spacing: 1px;")
        header.addWidget(language_label)
        header.addStretch(1)
        copy_button = QPushButton("Copy code")
        copy_button.setObjectName("PrimaryButton")
        copy_button.clicked.connect(self._copy_code)
        header.addWidget(copy_button)
        layout.addLayout(header)

        self.editor = QPlainTextEdit()
        self.editor.setPlainText(self._code)
        self.editor.setReadOnly(True)
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.setMinimumHeight(120)
        self.editor.setFrameShape(QFrame.Shape.NoFrame)
        self.editor.setFont(QFont("JetBrains Mono, monospace", 10))
        self._highlighter = SimpleCodeHighlighter(self.editor.document(), self._language)
        layout.addWidget(self.editor)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(22)
        shadow.setColor(QColor(0, 0, 0, 110))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)

    def _copy_code(self):
        self.editor.selectAll()
        self.editor.copy()
        self.editor.moveCursor(QTextCursor.MoveOperation.End)


class MessageBubble(QFrame):
    def __init__(self, text: str, role: str, parent=None):
        super().__init__(parent)
        self.role = role
        if role == "user":
            self.setObjectName("UserBubble")
        else:
            self.setObjectName("AssistantBubble")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(16, 14, 16, 14)
        self._main_layout.setSpacing(10)
        self._content_widgets: list[QWidget] = []
        self._raw_text = ""
        self.set_message(text)
        fade_in(self)

    def clear_content(self):
        while self._main_layout.count():
            item = self._main_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()
        self._content_widgets.clear()

    def set_message(self, text: str):
        self._raw_text = text
        self.clear_content()
        text = text.strip()
        if not text:
            label = QLabel("")
            self._main_layout.addWidget(label)
            return

        last_end = 0
        for match in CODE_BLOCK_RE.finditer(text):
            before = text[last_end:match.start()].strip()
            if before:
                label = QLabel()
                label.setTextFormat(Qt.TextFormat.RichText)
                label.setWordWrap(True)
                label.setOpenExternalLinks(True)
                label.setText(self._markdown_to_html(before))
                self._main_layout.addWidget(label)
                self._content_widgets.append(label)
            widget = CodeBlockWidget(match.group("code"), match.group("lang"), self)
            self._main_layout.addWidget(widget)
            self._content_widgets.append(widget)
            last_end = match.end()

        tail = text[last_end:].strip()
        if tail:
            label = QLabel()
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setWordWrap(True)
            label.setOpenExternalLinks(True)
            label.setText(self._markdown_to_html(tail))
            self._main_layout.addWidget(label)
            self._content_widgets.append(label)

    def _markdown_to_html(self, text: str) -> str:
        escaped = html.escape(text)
        escaped = re.sub(r"`([^`]+)`", r"<code style='background: rgba(255,255,255,0.08); padding: 2px 5px; border-radius: 6px;'>\1</code>", escaped)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
        escaped = re.sub(r"\*(.+?)\*", r"<i>\1</i>", escaped)
        lines = []
        for line in escaped.splitlines():
            if line.startswith("- "):
                lines.append(f"<div style='margin-left: 12px;'>• {line[2:]}</div>")
            elif line.startswith("# "):
                lines.append(f"<div style='font-size: 18px; font-weight: 700; margin-bottom: 4px;'>{line[2:]}</div>")
            else:
                lines.append(line)
        return "<div style='line-height: 1.5; font-size: 13px;'>" + "<br>".join(lines) + "</div>"


class ChatWidget(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(4, 4, 12, 4)
        self._container_layout.setSpacing(20)
        self._container_layout.addStretch(1)
        self.setWidget(self._container)

        self._current_assistant: MessageBubble | None = None

    def clear_messages(self):
        while self._container_layout.count():
            item = self._container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._container_layout.addStretch(1)
        self._current_assistant = None

    def add_user_message(self, text: str):
        self._add_message(text, "user")

    def begin_assistant_message(self):
        self._current_assistant = self._add_message("", "assistant")

    def append_assistant_chunk(self, chunk: str):
        if self._current_assistant is None:
            self.begin_assistant_message()
        if self._current_assistant is not None:
            self._current_assistant.set_message(self._current_assistant._raw_text + chunk)
            self._scroll_to_bottom()

    def finish_assistant_message(self, text: str | None = None):
        if self._current_assistant is None:
            if text:
                self._current_assistant = self._add_message(text, "assistant")
        elif text is not None:
            self._current_assistant.set_message(text)
        self._current_assistant = None
        self._scroll_to_bottom()

    def _get_current_plain_text(self) -> str:
        if self._current_assistant is None:
            return ""
        return self._current_assistant._raw_text

    def _add_message(self, text: str, role: str) -> MessageBubble:
        bubble = MessageBubble(text, role, self._container)
        row = QWidget(self._container)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(0)
        if role == "user":
            row_layout.addStretch(1)
            row_layout.addWidget(bubble, 0)
            bubble.setMaximumWidth(int(self.viewport().width() * 0.78))
        else:
            row_layout.addWidget(bubble, 0)
            row_layout.addStretch(1)
            bubble.setMaximumWidth(int(self.viewport().width() * 0.84))
        insert_index = max(0, self._container_layout.count() - 1)
        self._container_layout.insertWidget(insert_index, row)
        self._scroll_to_bottom()
        return bubble

    def _scroll_to_bottom(self):
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())


__all__ = ["ChatWidget", "MessageBubble", "CodeBlockWidget"]