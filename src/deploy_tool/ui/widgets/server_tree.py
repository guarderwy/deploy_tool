"""服务器/项目树 — 左侧导航"""
from PyQt5 import QtWidgets, QtCore, QtGui

from ...config.store import ConfigStore


class ServerTreeWidget(QtWidgets.QTreeWidget):
    """左侧服务器/项目树形导航"""

    # 信号
    server_selected = QtCore.pyqtSignal(str)
    project_selected = QtCore.pyqtSignal(str)
    server_add_requested = QtCore.pyqtSignal()
    project_add_requested = QtCore.pyqtSignal(str)  # server_id
    server_edit_requested = QtCore.pyqtSignal(str)  # server_id
    project_edit_requested = QtCore.pyqtSignal(str)  # project_id
    server_delete_requested = QtCore.pyqtSignal(str)
    project_delete_requested = QtCore.pyqtSignal(str)

    ROLE_SERVER_ID = QtCore.Qt.UserRole
    ROLE_PROJECT_ID = QtCore.Qt.UserRole + 1
    ROLE_TYPE = QtCore.Qt.UserRole + 2  # "server" | "project"

    def __init__(self, store: ConfigStore, parent=None):
        super().__init__(parent)
        self.store = store
        self._init_ui()

    def _init_ui(self):
        self.setHeaderLabels(["服务器 / 项目"])
        self.setHeaderHidden(True)
        self.setIndentation(16)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)
        self.itemClicked.connect(self._on_item_clicked)

    def refresh(self):
        """刷新树内容"""
        self.clear()
        for server in self.store.config.servers:
            server_item = QtWidgets.QTreeWidgetItem([server.name or server.host])
            server_item.setData(0, self.ROLE_SERVER_ID, server.id)
            server_item.setData(0, self.ROLE_TYPE, "server")
            server_item.setIcon(0, self.style().standardIcon(
                QtWidgets.QStyle.SP_ComputerIcon))
            self.addTopLevelItem(server_item)

            for proj in self.store.get_projects_for_server(server.id):
                proj_item = QtWidgets.QTreeWidgetItem([proj.name])
                proj_item.setData(0, self.ROLE_PROJECT_ID, proj.id)
                proj_item.setData(0, self.ROLE_TYPE, "project")
                proj_item.setIcon(0, self.style().standardIcon(
                    QtWidgets.QStyle.SP_DirIcon))
                server_item.addChild(proj_item)
            server_item.setExpanded(True)

    def _on_item_clicked(self, item: QtWidgets.QTreeWidgetItem, column: int):
        typ = item.data(0, self.ROLE_TYPE)
        if typ == "server":
            sid = item.data(0, self.ROLE_SERVER_ID)
            self.server_selected.emit(sid)
        elif typ == "project":
            pid = item.data(0, self.ROLE_PROJECT_ID)
            self.project_selected.emit(pid)

    def _on_context_menu(self, pos):
        item = self.itemAt(pos)
        menu = QtWidgets.QMenu(self)

        if item is None:
            # 空白处右键 — 添加服务器
            act = menu.addAction("添加服务器")
            act.triggered.connect(lambda: self.server_add_requested.emit())
        else:
            typ = item.data(0, self.ROLE_TYPE)
            if typ == "server":
                sid = item.data(0, self.ROLE_SERVER_ID)
                act1 = menu.addAction("添加项目")
                act1.triggered.connect(lambda: self.project_add_requested.emit(sid))
                menu.addSeparator()
                act2 = menu.addAction("编辑服务器")
                act2.triggered.connect(lambda: self.server_edit_requested.emit(sid))
                menu.addSeparator()
                act3 = menu.addAction("删除服务器")
                act3.triggered.connect(lambda: self.server_delete_requested.emit(sid))
            elif typ == "project":
                pid = item.data(0, self.ROLE_PROJECT_ID)
                act1 = menu.addAction("编辑项目")
                act1.triggered.connect(lambda: self.project_edit_requested.emit(pid))
                menu.addSeparator()
                act2 = menu.addAction("删除项目")
                act2.triggered.connect(lambda: self.project_delete_requested.emit(pid))

        menu.exec_(self.mapToGlobal(pos))
