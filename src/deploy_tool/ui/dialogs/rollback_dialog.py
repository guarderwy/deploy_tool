"""回滚 & 设置对话框"""
from PyQt5 import QtWidgets, QtCore

from ...config.models import BackupInfo, Project


class RollbackDialog(QtWidgets.QDialog):
    """选择备份并回滚"""

    rollback_requested = QtCore.pyqtSignal(object)  # BackupInfo

    def __init__(self, backups: list[BackupInfo], project: Project, parent=None):
        super().__init__(parent)
        self.backups = backups
        self.project = project
        self.setWindowTitle("回滚 - 选择备份")
        self.resize(500, 400)
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        info = QtWidgets.QLabel(
            f"<b>项目:</b> {self.project.name}<br>"
            f"<b>远程路径:</b> {self.project.remote_path}"
        )
        layout.addWidget(info)

        self._list = QtWidgets.QListWidget()
        for b in self.backups:
            size_str = f"{b.size_bytes / 1024:.1f} KB" if b.size_bytes < 1024 * 1024 else f"{b.size_bytes / (1024 * 1024):.1f} MB"
            text = f"{b.created_at}  |  {size_str}"
            item = QtWidgets.QListWidgetItem(text)
            item.setData(QtCore.Qt.UserRole, b.id)
            self._list.addItem(item)
        layout.addWidget(self._list)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        rollback_btn = QtWidgets.QPushButton("回滚到此版本")
        rollback_btn.setObjectName("dangerBtn")
        rollback_btn.clicked.connect(self._do_rollback)
        btn_layout.addWidget(rollback_btn)
        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _do_rollback(self):
        item = self._list.currentItem()
        if not item:
            QtWidgets.QMessageBox.warning(self, "提示", "请先选择一个备份")
            return

        # 二次确认
        reply = QtWidgets.QMessageBox.question(
            self, "确认回滚",
            "回滚将覆盖服务器上的当前文件，确定要继续吗？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        bid = item.data(QtCore.Qt.UserRole)
        backup = next((b for b in self.backups if b.id == bid), None)
        if backup:
            self.rollback_requested.emit(backup)
            self.accept()


class SettingsDialog(QtWidgets.QDialog):
    """设置对话框"""

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("设置")
        self.resize(400, 300)
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        g1 = QtWidgets.QGroupBox("外观")
        f1 = QtWidgets.QFormLayout(g1)
        self.theme_combo = QtWidgets.QComboBox()
        self.theme_combo.addItems(["跟随系统", "暗色", "亮色"])
        theme_map = {"auto": 0, "dark": 1, "light": 2}
        self.theme_combo.setCurrentIndex(theme_map.get(self.store.config.theme, 0))
        f1.addRow("主题:", self.theme_combo)
        layout.addWidget(g1)

        g2 = QtWidgets.QGroupBox("日志")
        f2 = QtWidgets.QFormLayout(g2)
        self.log_combo = QtWidgets.QComboBox()
        self.log_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        idx = levels.index(self.store.config.log_level) if self.store.config.log_level in levels else 1
        self.log_combo.setCurrentIndex(idx)
        f2.addRow("日志级别:", self.log_combo)

        self.max_logs = QtWidgets.QSpinBox()
        self.max_logs.setRange(7, 365)
        self.max_logs.setValue(self.store.config.max_log_files)
        f2.addRow("保留天数:", self.max_logs)
        layout.addWidget(g2)

        g3 = QtWidgets.QGroupBox("备份")
        f3 = QtWidgets.QFormLayout(g3)
        self.max_backups = QtWidgets.QSpinBox()
        self.max_backups.setRange(1, 50)
        self.max_backups.setValue(self.store.config.max_backups_per_project)
        f3.addRow("每项目最大备份:", self.max_backups)
        layout.addWidget(g3)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QtWidgets.QPushButton("保存")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _save(self):
        theme_map = {0: "auto", 1: "dark", 2: "light"}
        self.store.config.theme = theme_map[self.theme_combo.currentIndex()]
        self.store.config.log_level = self.log_combo.currentText()
        self.store.config.max_log_files = self.max_logs.value()
        self.store.config.max_backups_per_project = self.max_backups.value()
        self.store.save()
        self.accept()
