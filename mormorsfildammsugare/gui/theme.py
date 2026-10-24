"""KDE Plasma & Native Linux Theme Integration for MormorsFilDammsugare.

Reads system color schemes from ~/.config/kdeglobals (KDE Plasma 5 / 6)
and configures QPalette, QIcon, and widget styling to feel 100% native on SteamOS Desktop.
"""

from __future__ import annotations

import configparser
import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPalette
from PyQt6.QtWidgets import QApplication, QWidget


def _parse_rgb(val: str, fallback: tuple[int, int, int]) -> QColor:
    try:
        parts = [int(p.strip()) for p in val.split(",")[:3]]
        return QColor(*parts)
    except Exception:
        return QColor(*fallback)


class KDETheme:
    """Manages KDE Plasma color scheme parsing and Qt styling."""

    def __init__(self):
        self.kdeglobals_path = Path.home() / ".config" / "kdeglobals"
        self.has_kde = self.kdeglobals_path.exists()
        self.config = configparser.ConfigParser()
        if self.has_kde:
            try:
                self.config.read(self.kdeglobals_path)
            except Exception:
                self.has_kde = False

        self._load_colors()

    def _load_colors(self):
        # Window
        self.win_bg = self._get_color("Colors:Window", "BackgroundNormal", (36, 39, 44))
        self.win_fg = self._get_color("Colors:Window", "ForegroundNormal", (241, 241, 242))
        self.win_alt = self._get_color("Colors:Window", "BackgroundAlternate", (49, 54, 59))

        # View / Lists / Tables
        self.view_bg = self._get_color("Colors:View", "BackgroundNormal", (21, 28, 35))
        self.view_fg = self._get_color("Colors:View", "ForegroundNormal", (239, 240, 241))
        self.view_alt = self._get_color("Colors:View", "BackgroundAlternate", (26, 33, 42))

        # Button
        self.btn_bg = self._get_color("Colors:Button", "BackgroundNormal", (36, 39, 44))
        self.btn_fg = self._get_color("Colors:Button", "ForegroundNormal", (239, 240, 241))
        self.btn_hover = self._get_color("Colors:Button", "DecorationHover", (85, 161, 205))
        self.btn_focus = self._get_color("Colors:Button", "DecorationFocus", (52, 108, 146))

        # Selection / Highlights
        self.sel_bg = self._get_color("Colors:Selection", "BackgroundNormal", (86, 159, 204))
        self.sel_fg = self._get_color("Colors:Selection", "ForegroundNormal", (31, 31, 38))

        # Tooltip
        self.tip_bg = self._get_color("Colors:Tooltip", "BackgroundNormal", (36, 39, 44))
        self.tip_fg = self._get_color("Colors:Tooltip", "ForegroundNormal", (239, 240, 241))

        # Accent
        self.accent = self._get_color("Colors:Window", "ForegroundActive", (61, 174, 233))

    def _get_color(self, section: str, option: str, fallback: tuple[int, int, int]) -> QColor:
        if self.has_kde and self.config.has_option(section, option):
            return _parse_rgb(self.config.get(section, option), fallback)
        return QColor(*fallback)

    @property
    def is_dark(self) -> bool:
        # Determine luminance of window background
        r, g, b = self.win_bg.red(), self.win_bg.green(), self.win_bg.blue()
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        return lum < 128

    def create_palette(self) -> QPalette:
        palette = QPalette()

        # Window
        palette.setColor(QPalette.ColorRole.Window, self.win_bg)
        palette.setColor(QPalette.ColorRole.WindowText, self.win_fg)

        # Base / View
        palette.setColor(QPalette.ColorRole.Base, self.view_bg)
        palette.setColor(QPalette.ColorRole.AlternateBase, self.view_alt)
        palette.setColor(QPalette.ColorRole.Text, self.view_fg)

        # Buttons
        palette.setColor(QPalette.ColorRole.Button, self.btn_bg)
        palette.setColor(QPalette.ColorRole.ButtonText, self.btn_fg)

        # Selections
        palette.setColor(QPalette.ColorRole.Highlight, self.sel_bg)
        palette.setColor(QPalette.ColorRole.HighlightedText, self.sel_fg)

        # Tooltips
        palette.setColor(QPalette.ColorRole.ToolTipBase, self.tip_bg)
        palette.setColor(QPalette.ColorRole.ToolTipText, self.tip_fg)

        # Links
        palette.setColor(QPalette.ColorRole.Link, self.accent)

        return palette

    def build_stylesheet(self) -> str:
        """Returns clean, Breeze-matching QSS widget styles using KDE colors."""
        w_bg = self.win_bg.name()
        w_fg = self.win_fg.name()
        v_bg = self.view_bg.name()
        v_fg = self.view_fg.name()
        v_alt = self.view_alt.name()
        b_bg = self.btn_bg.name()
        b_fg = self.btn_fg.name()
        b_hov = self.btn_hover.name()
        b_foc = self.btn_focus.name()
        s_bg = self.sel_bg.name()
        s_fg = self.sel_fg.name()
        acc = self.accent.name()

        # Border color slightly lighter than window if dark, darker if light
        border_col = "#3a414b" if self.is_dark else "#c8cdd2"
        subtle_bg = "#2b3038" if self.is_dark else "#e4e7ea"

        return f"""
        /* KDE Breeze-Compliant MormorsFilDammsugare Stylesheet */
        QMainWindow {{
            background-color: {w_bg};
            color: {w_fg};
        }}

        QWidget {{
            color: {w_fg};
            font-size: 13px;
        }}

        /* Clean Tab Widget with Breeze Indicator */
        QTabWidget::pane {{
            border: 1px solid {border_col};
            border-radius: 6px;
            background-color: {w_bg};
            top: -1px;
            padding: 4px;
        }}

        QTabBar::tab {{
            background-color: {subtle_bg};
            color: {w_fg};
            border: 1px solid {border_col};
            border-bottom: none;
            padding: 8px 18px;
            margin-right: 3px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
            font-weight: 500;
        }}

        QTabBar::tab:selected {{
            background-color: {w_bg};
            border-color: {border_col};
            border-bottom: 2px solid {acc};
            font-weight: bold;
        }}

        QTabBar::tab:hover:!selected {{
            background-color: {border_col};
        }}

        /* Buttons */
        QPushButton {{
            background-color: {b_bg};
            color: {b_fg};
            border: 1px solid {border_col};
            border-radius: 5px;
            padding: 6px 14px;
            min-height: 20px;
        }}

        QPushButton:hover {{
            background-color: {subtle_bg};
            border-color: {b_hov};
        }}

        QPushButton:pressed {{
            background-color: {v_bg};
            border-color: {b_foc};
        }}

        QPushButton:disabled {{
            opacity: 0.5;
            color: #7f8c8d;
        }}

        /* Input Fields */
        QLineEdit, QComboBox {{
            background-color: {v_bg};
            color: {v_fg};
            border: 1px solid {border_col};
            border-radius: 4px;
            padding: 5px 8px;
            selection-background-color: {s_bg};
            selection-color: {s_fg};
        }}

        QLineEdit:focus, QComboBox:focus {{
            border: 1px solid {acc};
        }}

        /* Group Box */
        QGroupBox {{
            font-weight: bold;
            border: 1px solid {border_col};
            border-radius: 6px;
            margin-top: 14px;
            padding-top: 10px;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 4px;
            color: {acc};
        }}

        /* Table & Lists */
        QTableWidget {{
            background-color: {v_bg};
            alternate-background-color: {v_alt};
            color: {v_fg};
            border: 1px solid {border_col};
            border-radius: 4px;
            gridline-color: {border_col};
            selection-background-color: {s_bg};
            selection-color: {s_fg};
        }}

        QHeaderView::section {{
            background-color: {subtle_bg};
            color: {w_fg};
            padding: 5px 8px;
            border: 1px solid {border_col};
            font-weight: bold;
        }}

        /* Progress Bar */
        QProgressBar {{
            background-color: {v_bg};
            border: 1px solid {border_col};
            border-radius: 5px;
            text-align: center;
            color: {w_fg};
            font-weight: bold;
            min-height: 18px;
        }}

        QProgressBar::chunk {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                        stop:0 {b_foc}, stop:1 {acc});
            border-radius: 4px;
        }}

        /* Scrollbars */
        QScrollBar:vertical {{
            background: {w_bg};
            width: 12px;
            margin: 0;
        }}

        QScrollBar::handle:vertical {{
            background: {border_col};
            min-height: 24px;
            border-radius: 4px;
            margin: 2px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: {b_hov};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        """


def apply_kde_theme(app: QApplication, window: QWidget | None = None) -> KDETheme:
    """Configures the QApplication to honor KDE Plasma system theme."""
    kde = KDETheme()

    # Apply base style and palette
    app.setStyle("Fusion")
    app.setPalette(kde.create_palette())
    app.setStyleSheet(kde.build_stylesheet())

    # Set icon theme
    theme_name = "breeze-dark" if kde.is_dark else "breeze"
    QIcon.setThemeName(theme_name)

    # Set application window icon from assets
    asset_dir = Path(__file__).parent / "assets"
    png_icon = asset_dir / "mormors-fildammsugare.png"
    svg_icon = asset_dir / "mormors-fildammsugare.svg"

    app_icon = None
    if png_icon.exists():
        app_icon = QIcon(str(png_icon))
    elif svg_icon.exists():
        app_icon = QIcon(str(svg_icon))

    if app_icon and not app_icon.isNull():
        app.setWindowIcon(app_icon)
        if window:
            window.setWindowIcon(app_icon)

    return kde
