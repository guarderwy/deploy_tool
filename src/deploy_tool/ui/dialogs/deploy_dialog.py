"""部署预览对话框"""
from PyQt5 import QtWidgets, QtCore

from ...config.models import FileDiff, Project, DiffStatus


class DeployDialog(QtWidgets.QDialog):
    """部署预览 + 文件勾选确认"""

    deploy_confirmed = QtCore.pyqtSignal(list)

    def __init__(self, diffs: list[FileDiff], project: Project, parent=None):
        super().__init__(parent)
        self.diffs = diffs
        self.project = project
        self.setWindowTitle("部署预览")
        self.resize(700, 550)
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # 摘要
        total = len(self.diffs)
        new_count = sum(1 for d in self.diffs if d.status == DiffStatus.NEW)
        mod_count = sum(1 for d in self.diffs if d.status == DiffStatus.MODIFIED)
        del_count = sum(1 for d in self.diffs if d.status == DiffStatus.DELETED)

        summary = QtWidgets.QLabel(
            f"<b>项目:</b> {self.project.name} &nbsp;&nbsp; "
            f"<b>远程路径:</b> {self.project.remote_path}<br><br>"
            f"共 <b style='color:#a6e3a1'>{total}</b> 个文件有变化 "
            f"(新增: <span style='color:#a6e3a1'>{new_count}</span>, "
            f"修改: <span style='color:#f9e2af'>{mod_count}</span>, "
            f"删除: <span style='color:#f38ba8'>{del_count}</span>)"
        )
        layout.addWidget(summary)

        # 命令提示
        if self.project.pre_deploy_commands or self.project.post_deploy_commands:
            cmd_text = ""
            if self.project.pre_deploy_commands:
                cmd_text += "前置命令:\n" + "\n".join(self.project.pre_deploy_commands)
            if self.project.post_deploy_commands:
                if cmd_text:
                    cmd_text += "\n\n"
                cmd_text += "后置命令:\n" + "\n".join(self.project.post_deploy_commands)
            cmd_label = QtWidgets.QLabel(cmd_text)
            cmd_label.setStyleSheet("color: #89b4fa;")
            layout.addWidget(cmd_label)

        # 备份提示
        if self.project.enable_backup:
            backup_label = QtWidgets.QLabel("备份: 部署前将自动创建远程备份")
            backup_label.setStyleSheet("color: #a6e3a1; font-weight: bold;")
            layout.addWidget(backup_label)

        # 工具栏
        toolbar = QtWidgets.QHBoxLayout()
        all_btn = QtWidgets.QPushButton("全选")
        all_btn.clicked.connect(self._select_all)
        none_btn = QtWidgets.QPushButton("反选")
        none_btn.clicked.connect(self._select_none)
        toolbar.addWidget(all_btn)
        toolbar.addWidget(none_btn)

        self.status_filter = QtWidgets.QComboBox()
        self.status_filter.addItems(["全部", "新增", "修改", "删除"])
        self.status_filter.currentIndexChanged.connect(self._refresh)
        toolbar.addWidget(self.status_filter)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 文件列表
        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderLabels(["", "文件路径", "状态", "大小"])
        self._tree.setColumnWidth(0, 30)
        self._tree.setColumnWidth(1, 420)
        self._tree.setColumnWidth(2, 60)
        self._tree.setColumnWidth(3, 90)
        self._tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._tree)

        # 统计
        self.stats_label = QtWidgets.QLabel()
        layout.addWidget(self.stats_label)

        # 按钮
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        deploy_btn = QtWidgets.QPushButton("确认部署")
        deploy_btn.setObjectName("primaryBtn")
        deploy_btn.clicked.connect(self._confirm)
        btn_layout.addWidget(deploy_btn)
        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self._refresh()

    def _refresh(self):
        self._tree.clear()
        filter_map = {0: None, 1: DiffStatus.NEW, 2: DiffStatus.MODIFIED, 3: DiffStatus.DELETED}
        target = filter_map[self.status_filter.currentIndex()]

        for d in self.diffs:
            if target and d.status != target:
                continue
            item = QtWidgets.QTreeWidgetItem()
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(0, QtCore.Qt.Checked if d.selected else QtCore.Qt.Unchecked)
            item.setData(0, QtCore.Qt.UserRole, d.relative_path)
            item.setText(1, d.relative_path)

            status_map = {DiffStatus.NEW: ("新增", "#a6e3a1"),
                          DiffStatus.MODIFIED: ("修改", "#f9e2af"),
                          DiffStatus.DELETED: ("删除", "#f38ba8")}
            st = status_map.get(d.status, ("", ""))
            item.setText(2, st[0])
            from PyQt5.QtGui import QColor
            item.setForeground(2, QColor(st[1]))

            size = d.local_size or d.remote_size
            item.setText(3, self._fmt_size(size) if size > 0 else "")
            item.setToolTip(3, f"{size} 字节" if size > 0 else "")

            self._tree.addTopLevelItem(item)

        selected = sum(1 for d in self.diffs if d.selected)
        total_bytes = sum(
            d.local_size or d.remote_size for d in self.diffs if d.selected)
        self.stats_label.setText(
            f"已选 {selected}/{len(self.diffs)} 个文件，"
            f"共 {self._fmt_size(total_bytes)}"
        )

    def _select_all(self):
        for i in range(self._tree.topLevelItemCount()):
            self._tree.topLevelItem(i).setCheckState(0, QtCore.Qt.Checked)

    def _select_none(self):
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            state = item.checkState(0)
            item.setCheckState(0, QtCore.Qt.Unchecked if state == QtCore.Qt.Checked else QtCore.Qt.Checked)

    def _on_item_changed(self, item, col):
        if col != 0:
            return
        path = item.data(0, QtCore.Qt.UserRole)
        for d in self.diffs:
            if d.relative_path == path:
                d.selected = item.checkState(0) == QtCore.Qt.Checked
                break
        self._refresh()

    def _confirm(self):
        selected = [d for d in self.diffs if d.selected]
        if not selected:
            QtWidgets.QMessageBox.warning(self, "提示", "请选择要部署的文件")
            return
        self.deploy_confirmed.emit(selected)
        self.accept()

    @staticmethod
    def _fmt_size(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.1f} MB"
