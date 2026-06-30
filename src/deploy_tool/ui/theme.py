"""主题系统 — 跟随 Windows 系统亮色/暗色模式"""
import winreg
from PyQt5 import QtWidgets, QtGui

# ---------- 暗色主题 QSS ----------
DARK_QSS = """
QMainWindow, QDialog, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QMenuBar {
    background-color: #181825;
    color: #cdd6f4;
    border-bottom: 1px solid #313244;
}
QMenuBar::item:selected {
    background-color: #313244;
}
QMenu {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
}
QMenu::item:selected {
    background-color: #45475a;
}
QTreeWidget, QListWidget, QTableWidget {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    alternate-background-color: #1e1e2e;
}
QTreeWidget::item:selected, QListWidget::item:selected {
    background-color: #45475a;
    color: #cdd6f4;
}
QTreeWidget::item:hover, QListWidget::item:hover {
    background-color: #313244;
}
QHeaderView::section {
    background-color: #11111b;
    color: #cdd6f4;
    border: none;
    border-bottom: 2px solid #313244;
    padding: 4px 8px;
}
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 6px 16px;
    min-width: 80px;
}
QPushButton:hover {
    background-color: #45475a;
    border-color: #585b70;
}
QPushButton:pressed {
    background-color: #585b70;
}
QPushButton:disabled {
    background-color: #1e1e2e;
    color: #6c7086;
}
QPushButton#primaryBtn {
    background-color: #1976D2;
    color: white;
    border: none;
    font-weight: bold;
}
QPushButton#primaryBtn:hover {
    background-color: #1E88E5;
}
QPushButton#dangerBtn {
    background-color: #C62828;
    color: white;
    border: none;
    font-weight: bold;
}
QPushButton#dangerBtn:hover {
    background-color: #D32F2F;
}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 4px;
    padding: 4px 8px;
}
QLineEdit:focus, QTextEdit:focus {
    border-color: #1976D2;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #181825;
    color: #cdd6f4;
    selection-background-color: #45475a;
}
QLabel {
    color: #cdd6f4;
}
QGroupBox {
    border: 1px solid #313244;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 16px;
    font-weight: bold;
    color: #cdd6f4;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QTabWidget::pane {
    border: 1px solid #313244;
    border-radius: 4px;
    background-color: #1e1e2e;
}
QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    border: 1px solid #313244;
    padding: 6px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border-bottom: 2px solid #1976D2;
}
QTabBar::tab:hover {
    background-color: #313244;
}
QSplitter::handle {
    background-color: #313244;
}
QScrollBar:vertical {
    background: #181825;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #585b70;
}
QScrollBar:horizontal {
    background: #181825;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #45475a;
    border-radius: 5px;
    min-width: 30px;
}
QProgressBar {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 4px;
    text-align: center;
    color: #cdd6f4;
}
QProgressBar::chunk {
    background-color: #1976D2;
    border-radius: 3px;
}
QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #313244;
}
QCheckBox {
    color: #cdd6f4;
}
QRadioButton {
    color: #cdd6f4;
}
QToolTip {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    padding: 4px;
}
"""

# ---------- 亮色主题 QSS ----------
LIGHT_QSS = """
QMainWindow, QDialog, QWidget {
    background-color: #eff1f5;
    color: #4c4f69;
}
QMenuBar {
    background-color: #dce0e8;
    color: #4c4f69;
    border-bottom: 1px solid #ccd0da;
}
QMenuBar::item:selected {
    background-color: #ccd0da;
}
QMenu {
    background-color: #eff1f5;
    color: #4c4f69;
    border: 1px solid #ccd0da;
}
QMenu::item:selected {
    background-color: #ccd0da;
}
QTreeWidget, QListWidget, QTableWidget {
    background-color: #e6e9ef;
    color: #4c4f69;
    border: 1px solid #ccd0da;
    alternate-background-color: #eff1f5;
}
QTreeWidget::item:selected, QListWidget::item:selected {
    background-color: #1e66f5;
    color: white;
}
QTreeWidget::item:hover, QListWidget::item:hover {
    background-color: #ccd0da;
}
QHeaderView::section {
    background-color: #dce0e8;
    color: #4c4f69;
    border: none;
    border-bottom: 2px solid #ccd0da;
    padding: 4px 8px;
}
QPushButton {
    background-color: #ccd0da;
    color: #4c4f69;
    border: 1px solid #bcc0cc;
    border-radius: 4px;
    padding: 6px 16px;
    min-width: 80px;
}
QPushButton:hover {
    background-color: #bcc0cc;
}
QPushButton:pressed {
    background-color: #acb0be;
}
QPushButton:disabled {
    background-color: #e6e9ef;
    color: #9ca0b0;
}
QPushButton#primaryBtn {
    background-color: #1e66f5;
    color: white;
    border: none;
    font-weight: bold;
}
QPushButton#primaryBtn:hover {
    background-color: #3465e0;
}
QPushButton#dangerBtn {
    background-color: #d20f39;
    color: white;
    border: none;
    font-weight: bold;
}
QPushButton#dangerBtn:hover {
    background-color: #c00e34;
}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {
    background-color: #e6e9ef;
    color: #4c4f69;
    border: 1px solid #ccd0da;
    border-radius: 4px;
    padding: 4px 8px;
}
QLineEdit:focus, QTextEdit:focus {
    border-color: #1e66f5;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #e6e9ef;
    color: #4c4f69;
    selection-background-color: #1e66f5;
    selection-color: white;
}
QLabel {
    color: #4c4f69;
}
QGroupBox {
    border: 1px solid #ccd0da;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 16px;
    font-weight: bold;
    color: #4c4f69;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QTabWidget::pane {
    border: 1px solid #ccd0da;
    border-radius: 4px;
    background-color: #eff1f5;
}
QTabBar::tab {
    background-color: #dce0e8;
    color: #6c6f85;
    border: 1px solid #ccd0da;
    padding: 6px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #eff1f5;
    color: #4c4f69;
    border-bottom: 2px solid #1e66f5;
}
QTabBar::tab:hover {
    background-color: #ccd0da;
}
QSplitter::handle {
    background-color: #ccd0da;
}
QScrollBar:vertical {
    background: #dce0e8;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #acb0be;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #9ca0b0;
}
QScrollBar:horizontal {
    background: #dce0e8;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #acb0be;
    border-radius: 5px;
    min-width: 30px;
}
QProgressBar {
    background-color: #dce0e8;
    border: 1px solid #ccd0da;
    border-radius: 4px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #1e66f5;
    border-radius: 3px;
}
QStatusBar {
    background-color: #dce0e8;
    color: #6c6f85;
    border-top: 1px solid #ccd0da;
}
QCheckBox {
    color: #4c4f69;
}
QRadioButton {
    color: #4c4f69;
}
QToolTip {
    background-color: #e6e9ef;
    color: #4c4f69;
    border: 1px solid #ccd0da;
    padding: 4px;
}
"""


def detect_system_theme() -> str:
    """检测 Windows 系统当前主题：'light' 或 'dark'"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return "light" if value == 1 else "dark"
    except Exception:
        return "light"


def apply_theme(app: QtWidgets.QApplication, mode: str = "auto"):
    """应用主题"""
    if mode == "auto":
        mode = detect_system_theme()
    app.setStyleSheet(DARK_QSS if mode == "dark" else LIGHT_QSS)
