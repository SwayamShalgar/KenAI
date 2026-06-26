from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtGui import QColor, QPalette


@dataclass(frozen=True)
class ThemeSpec:
    name: str
    window_bg: str
    panel_bg: str
    panel_bg_alt: str
    border: str
    text: str
    muted_text: str
    accent: str
    accent_soft: str
    danger: str
    success: str


DARK_THEME = ThemeSpec(
    name="dark",
    window_bg="#050814",
    panel_bg="rgba(11, 16, 28, 0.85)",
    panel_bg_alt="rgba(18, 25, 40, 0.88)",
    border="rgba(255, 255, 255, 0.06)",
    text="#EAF2FF",
    muted_text="#8BA2C8",
    accent="#78D8FF",
    accent_soft="rgba(120, 216, 255, 0.15)",
    danger="#FF6B86",
    success="#7CF2B0",
)

LIGHT_THEME = ThemeSpec(
    name="light",
    window_bg="#EDF2F7",
    panel_bg="rgba(255, 255, 255, 0.78)",
    panel_bg_alt="rgba(245, 247, 252, 0.9)",
    border="rgba(15, 23, 42, 0.08)",
    text="#0B1220",
    muted_text="#5B6478",
    accent="#1A7DFF",
    accent_soft="rgba(26, 125, 255, 0.12)",
    danger="#D84763",
    success="#067A46",
)


def theme_for_name(name: str) -> ThemeSpec:
    if name.strip().lower() == "light":
        return LIGHT_THEME
    return DARK_THEME


def build_stylesheet(theme: ThemeSpec, animation_intensity: int = 70) -> str:
    glow = max(0.12, min(animation_intensity / 100.0, 1.0))
    return f"""
    QWidget {{
        color: {theme.text};
        font-family: Inter, "Segoe UI", "Noto Sans", sans-serif;
    }}
    QMainWindow {{
        background: transparent;
    }}
    QFrame#RootPanel {{
        background-color: {theme.panel_bg};
        border: 1px solid {theme.border};
        border-radius: 24px;
    }}
    QFrame#GlassCard {{
        background-color: {theme.panel_bg_alt};
        border: 1px solid {theme.border};
        border-radius: 22px;
    }}
    QFrame#UserBubble {{
        background-color: rgba(30, 60, 110, 0.65);
        border: 1px solid rgba(120, 216, 255, 0.15);
        border-radius: 18px;
    }}
    QFrame#AssistantBubble {{
        background-color: rgba(22, 28, 45, 0.7);
        border: 1px solid {theme.border};
        border-radius: 18px;
    }}
    QLabel#TitleLabel {{
        font-size: 16px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }}
    QLabel#StatusPill {{
        padding: 7px 14px;
        border-radius: 999px;
        background-color: {theme.accent_soft};
        color: {theme.text};
        border: 1px solid rgba(255, 255, 255, {glow});
    }}
    QLabel#MutedLabel {{
        color: {theme.muted_text};
    }}
    QPushButton {{
        border: 1px solid {theme.border};
        border-radius: 16px;
        padding: 10px 14px;
        background-color: rgba(255, 255, 255, 0.04);
    }}
    QPushButton:hover {{
        background-color: rgba(255, 255, 255, 0.08);
        border-color: rgba(255, 255, 255, 0.14);
    }}
    QPushButton:pressed {{
        background-color: rgba(255, 255, 255, 0.12);
    }}
    QPushButton#PrimaryButton {{
        background-color: {theme.accent_soft};
        border: 1px solid rgba(255, 255, 255, 0.16);
        font-weight: 600;
    }}
    QPushButton#DangerButton {{
        background-color: rgba(255, 107, 134, 0.14);
        border: 1px solid rgba(255, 107, 134, 0.22);
    }}
    QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background-color: rgba(8, 12, 22, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 18px;
        padding: 12px 16px;
        font-size: 14px;
        selection-background-color: {theme.accent};
        selection-color: #04101d;
    }}
    QComboBox::drop-down {{
        border: 0;
        width: 28px;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 4px 2px 4px 2px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(255, 255, 255, 0.16);
        border-radius: 5px;
        min-height: 28px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: rgba(255, 255, 255, 0.26);
    }}
    """


def palette_for_theme(theme: ThemeSpec) -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(theme.window_bg))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(theme.text))
    palette.setColor(QPalette.ColorRole.Base, QColor(theme.panel_bg_alt))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(theme.panel_bg))
    palette.setColor(QPalette.ColorRole.Text, QColor(theme.text))
    palette.setColor(QPalette.ColorRole.Button, QColor(theme.panel_bg_alt))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme.text))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(theme.accent))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#07111A"))
    return palette