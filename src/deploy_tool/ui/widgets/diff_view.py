"""差异文件预览 — 右侧差异文件列表"""
from PyQt5 import QtWidgets, QtCore, QtGui

from ...config.models import FileDiff, DiffStatus


class DiffViewWidget(QtWidgets.QWidget):
    """差异文件预览"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.diffs: list[FileDiff] = []
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QtWidgets.QHBoxLayout()
        self._all_btn = QtWidgets.QPushButton("全选")
        self._all_btn.setFixedWidth(60)
        self._all_btn.clicked.connect(self._select_all)
        self._none_btn = QtWidgets.QPushButton("反选")
        self._none_btn.setFixedWidth(60)
        self._none_btn.clicked.connect(self._select_none)
        toolbar.addWidget(self._all_btn)
        toolbar.addWidget(self._none_btn)

        self._filter_combo = QtWidgets.QComboBox()
        self._filter_combo.addItems(["全部", "新增", "修改", "删除"])
        self._filter_combo.currentIndexChanged.connect(self._apply_filter)
        toolbar.addWidget(self._filter_combo)

        self._stats_label = QtWidgets.QLabel("")
        toolbar.addWidget(self._stats_label)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 文件列表
        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderLabels(["", "文件路径", "状态", "本地大小", "远程大小"])
        self._tree.setRootIsDecorated(True)
        self._tree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # 列宽
        self._tree.setColumnWidth(0, 30)   # checkbox 列
        self._tree.setColumnWidth(1, 260)
        self._tree.setColumnWidth(2, 60)
        self._tree.setColumnWidth(3, 90)
        self._tree.setColumnWidth(4, 90)

        self._tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._tree)

    def set_diffs(self, diffs: list[FileDiff]):
        """设置差异列表"""
        self.diffs = diffs
        self._apply_filter()

    def get_selected(self) -> list[FileDiff]:
        """返回勾选的文件差异"""
        return [d for d in self.diffs if d.selected]

    def _apply_filter(self):
        """应用过滤器刷新列表"""
        filter_idx = self._filter_combo.currentIndex()
        status_map = {0: None, 1: DiffStatus.NEW, 2: DiffStatus.MODIFIED, 3: DiffStatus.DELETED}
        target_status = status_map.get(filter_idx)

        self._tree.clear()
        filtered = self.diffs
        if target_status:
            filtered = [d for d in self.diffs if d.status == target_status]

        for d in filtered:
            item = QtWidgets.QTreeWidgetItem()
            # checkbox
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(0, QtCore.Qt.Checked if d.selected else QtCore.Qt.Unchecked)
            item.setData(0, QtCore.Qt.UserRole, d.relative_path)

            # 路径
            item.setText(1, d.relative_path)

            # 状态
            status_text, color = self._status_info(d.status)
            item.setText(2, status_text)
            item.setForeground(2, QtGui.QColor(color))

            # 大小
            if d.status != DiffStatus.DELETED:
                item.setText(3, self._format_size(d.local_size))
                item.setToolTip(3, f"{d.local_size} 字节")
            if d.status != DiffStatus.NEW:
                item.setText(4, self._format_size(d.remote_size))
                item.setToolTip(4, f"{d.remote_size} 字节")

            self._tree.addTopLevelItem(item)

        # 更新统计
        total = len(self.diffs)
        new = sum(1 for d in self.diffs if d.status == DiffStatus.NEW)
        mod = sum(1 for d in self.diffs if d.status == DiffStatus.MODIFIED)
        deleted = sum(1 for d in self.diffs if d.status == DiffStatus.DELETED)
        self._stats_label.setText(f"共 {total} 个文件 (新增:{new} 修改:{mod} 删除:{deleted})")

    def _on_item_changed(self, item: QtWidgets.QTreeWidgetItem, column: int):
        if column != 0:
            return
        path = item.data(0, QtCore.Qt.UserRole)
        for d in self.diffs:
            if d.relative_path == path:
                d.selected = (item.checkState(0) == QtCore.Qt.Checked)
                break

    def _select_all(self):
        for i in range(self._tree.topLevelItemCount()):
            self._tree.topLevelItem(i).setCheckState(0, QtCore.Qt.Checked)

    def _select_none(self):
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            item.setCheckState(0, QtCore.Qt.Unchecked if item.checkState(0) == QtCore.Qt.Checked else QtCore.Qt.Checked)

    @staticmethod
    def _status_info(status: DiffStatus) -> tuple[str, str]:
        if status == DiffStatus.NEW:
            return "新增", "#a6e3a1"
        elif status == DiffStatus.MODIFIED:
            return "修改", "#f9e2af"
        elif status == DiffStatus.DELETED:
            return "删除", "#f38ba8"
        return "不变", ""

    @staticmethod
    def _format_size(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
