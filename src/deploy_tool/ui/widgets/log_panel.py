"""日志面板 — 底部可折叠日志输出"""
from PyQt5 import QtWidgets, QtCore, QtGui


class LogPanel(QtWidgets.QWidget):
    """底部日志面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题栏
        header = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(header)
        hl.setContentsMargins(8, 2, 8, 2)
        self._title = QtWidgets.QLabel("日志")
        self._title.setStyleSheet("font-weight: bold;")
        hl.addWidget(self._title)
        hl.addStretch()
        self._toggle_btn = QtWidgets.QPushButton("_")
        self._toggle_btn.setFixedSize(24, 24)
        self._toggle_btn.clicked.connect(self._toggle)
        clear_btn = QtWidgets.QPushButton("清空")
        clear_btn.setFixedSize(50, 24)
        clear_btn.clicked.connect(self._clear)
        hl.addWidget(clear_btn)
        hl.addWidget(self._toggle_btn)
        layout.addWidget(header)

        # 日志文本框
        self._text = QtWidgets.QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setMaximumBlockCount(5000)
        font = QtGui.QFont("Consolas", 10)
        self._text.setFont(font)
        layout.addWidget(self._text)

        self._collapsed = False

    def append(self, text: str, color: str = None):
        """追加日志文本"""
        self._text.moveCursor(QtGui.QTextCursor.End)
        if color:
            fmt = QtGui.QTextCharFormat()
            fmt.setForeground(QtGui.QColor(color))
            self._text.setCurrentCharFormat(fmt)
        self._text.insertPlainText(text + "\n")
        if color:
            # 还原默认颜色
            default_color = "#cdd6f4" if self._is_dark() else "#4c4f69"
            fmt2 = QtGui.QTextCharFormat()
            fmt2.setForeground(QtGui.QColor(default_color))
            self._text.setCurrentCharFormat(fmt2)

    def info(self, text: str):
        self.append(f"[INFO] {text}", "#a6e3a1")

    def warn(self, text: str):
        self.append(f"[WARN] {text}", "#f9e2af")

    def error(self, text: str):
        self.append(f"[ERROR] {text}", "#f38ba8")

    def _toggle(self):
        self._collapsed = not self._collapsed
        self._text.setVisible(not self._collapsed)
        self._toggle_btn.setText("+" if self._collapsed else "_")

    def _clear(self):
        self._text.clear()

    def _is_dark(self) -> bool:
        """简单检测当前是否暗色主题"""
        return True
