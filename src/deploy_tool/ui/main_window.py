"""主窗口 — 三栏布局 + 部署全流程"""
from PyQt5 import QtWidgets, QtCore

from ..config.store import ConfigStore
from ..config.models import Project, DiffStatus
from ..core.ssh.pool import ConnectionPool
from .theme import apply_theme, detect_system_theme
from .widgets.server_tree import ServerTreeWidget
from .widgets.diff_view import DiffViewWidget
from .widgets.log_panel import LogPanel
from .dialogs.server_dialog import ServerDialog
from .dialogs.project_dialog import ProjectDialog
from .dialogs.deploy_dialog import DeployDialog
from .dialogs.rollback_dialog import RollbackDialog, SettingsDialog
from .workers.base import (
    DiffWorker, DeployWorker, RollbackWorker, TestConnectionWorker,
)


class ProjectInfoCard(QtWidgets.QGroupBox):
    """中栏：项目信息卡片"""

    def __init__(self, parent=None):
        super().__init__("项目信息", parent)
        self._layout = QtWidgets.QFormLayout(self)
        self._name = QtWidgets.QLabel("-")
        self._type = QtWidgets.QLabel("-")
        self._server = QtWidgets.QLabel("-")
        self._local = QtWidgets.QLabel("-")
        self._remote = QtWidgets.QLabel("-")
        self._pre_cmds = QtWidgets.QLabel("-")
        self._post_cmds = QtWidgets.QLabel("-")
        self._excludes = QtWidgets.QLabel("-")
        self._backup = QtWidgets.QLabel("-")
        self._sync = QtWidgets.QLabel("-")

        self._layout.addRow("名称:", self._name)
        self._layout.addRow("类型:", self._type)
        self._layout.addRow("服务器:", self._server)
        self._layout.addRow("本地路径:", self._local)
        self._layout.addRow("远程路径:", self._remote)
        self._layout.addRow("前置命令:", self._pre_cmds)
        self._layout.addRow("后置命令:", self._post_cmds)
        self._layout.addRow("排除规则:", self._excludes)
        self._layout.addRow("备份:", self._backup)
        self._layout.addRow("同步模式:", self._sync)

    def set_project(self, project: Project, store: ConfigStore):
        if project is None:
            self._name.setText("-")
            return
        self._name.setText(project.name)
        self._type.setText(project.project_type)
        server = store.find_server(project.server_id)
        self._server.setText(server.name if server else project.server_id)
        self._local.setText(project.local_path)
        self._remote.setText(project.remote_path)
        self._pre_cmds.setText("、".join(project.pre_deploy_commands) or "无")
        self._post_cmds.setText("、".join(project.post_deploy_commands) or "无")
        self._excludes.setText("、".join(project.exclude_patterns[:5]) + (
            "..." if len(project.exclude_patterns) > 5 else ""))
        self._backup.setText("开启" if project.enable_backup else "关闭")
        self._sync.setText("SHA256" if project.sync_mode == "hash" else "大小+时间")


class DeployHistoryWidget(QtWidgets.QWidget):
    """右栏 Tab：部署历史"""

    def __init__(self, store: ConfigStore, parent=None):
        super().__init__(parent)
        self.store = store
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderLabels(["时间", "状态", "上传", "删除", "大小"])
        self._tree.setColumnWidth(0, 150)
        self._tree.setColumnWidth(1, 60)
        self._tree.setColumnWidth(2, 50)
        self._tree.setColumnWidth(3, 50)
        layout.addWidget(self._tree)

    def refresh(self, project_id: str = None):
        self._tree.clear()
        records = self.store.config.deploy_records
        if project_id:
            records = [r for r in records if r.project_id == project_id]
        records.sort(key=lambda r: r.started_at, reverse=True)
        for r in records[:100]:
            item = QtWidgets.QTreeWidgetItem([
                r.started_at,
                r.status,
                str(r.files_uploaded),
                str(r.files_deleted),
                self._fmt_size(r.bytes_transferred),
            ])
            color = "#a6e3a1" if r.status == "success" else "#f38ba8"
            from PyQt5.QtGui import QColor
            item.setForeground(1, QColor(color))
            self._tree.addTopLevelItem(item)

    @staticmethod
    def _fmt_size(s: int) -> str:
        if s < 1024:
            return f"{s} B"
        return f"{s / 1024:.1f} KB" if s < 1024 * 1024 else f"{s / (1024 * 1024):.1f} MB"


class MainWindow(QtWidgets.QMainWindow):
    """主窗口 — 三栏布局"""

    def __init__(self, store: ConfigStore, pool: ConnectionPool):
        super().__init__()
        self.store = store
        self.pool = pool
        self._current_project: Project | None = None
        self._current_diffs: list = []

        self.setWindowTitle("部署工具")
        self.resize(1280, 800)
        self._build_ui()
        self._connect_signals()
        self._refresh_all()

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        # ---- 菜单栏 ----
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("文件")
        file_menu.addAction("设置", self._open_settings)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close)

        server_menu = menu_bar.addMenu("服务器")
        server_menu.addAction("添加服务器", self._add_server)

        project_menu = menu_bar.addMenu("项目")
        project_menu.addAction("添加项目", self._add_project)

        help_menu = menu_bar.addMenu("帮助")
        help_menu.addAction("关于", self._about)

        # ---- 垂直分割器（上三栏 + 下日志）----
        v_split = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        # 上三栏
        h_split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # 左栏：服务器/项目树
        self.server_tree = ServerTreeWidget(self.store)
        h_split.addWidget(self.server_tree)

        # 中栏
        center = QtWidgets.QWidget()
        center_layout = QtWidgets.QVBoxLayout(center)
        center_layout.setContentsMargins(4, 4, 4, 4)

        # 操作按钮栏
        action_bar = QtWidgets.QHBoxLayout()
        self.deploy_btn = QtWidgets.QPushButton("部署")
        self.deploy_btn.setObjectName("primaryBtn")
        self.deploy_btn.setEnabled(False)
        self.deploy_btn.clicked.connect(self._start_deploy)
        action_bar.addWidget(self.deploy_btn)

        self.diff_btn = QtWidgets.QPushButton("对比差异")
        self.diff_btn.setEnabled(False)
        self.diff_btn.clicked.connect(self._start_diff)
        action_bar.addWidget(self.diff_btn)

        self.rollback_btn = QtWidgets.QPushButton("回滚")
        self.rollback_btn.setEnabled(False)
        self.rollback_btn.clicked.connect(self._start_rollback)
        action_bar.addWidget(self.rollback_btn)

        self.test_conn_btn = QtWidgets.QPushButton("测试连接")
        self.test_conn_btn.setEnabled(False)
        self.test_conn_btn.clicked.connect(self._test_connection)
        action_bar.addWidget(self.test_conn_btn)

        action_bar.addStretch()
        center_layout.addLayout(action_bar)

        # 项目信息
        self.info_card = ProjectInfoCard()
        center_layout.addWidget(self.info_card)
        center_layout.addStretch()

        h_split.addWidget(center)

        # 右栏：Tab（差异预览 / 部署历史）
        self.right_tabs = QtWidgets.QTabWidget()
        self.diff_view = DiffViewWidget()
        self.right_tabs.addTab(self.diff_view, "差异预览")
        self.history_view = DeployHistoryWidget(self.store)
        self.right_tabs.addTab(self.history_view, "部署历史")
        h_split.addWidget(self.right_tabs)

        # 比例
        h_split.setSizes([280, 500, 360])
        v_split.addWidget(h_split)

        # 底部日志
        self.log_panel = LogPanel()
        v_split.addWidget(self.log_panel)
        v_split.setSizes([550, 200])

        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.addWidget(v_split)

        # ---- 状态栏 ----
        self.status_bar = self.statusBar()
        self._status_label = QtWidgets.QLabel("就绪")
        self.status_bar.addWidget(self._status_label)
        self._progress = QtWidgets.QProgressBar()
        self._progress.setFixedWidth(200)
        self._progress.setVisible(False)
        self.status_bar.addPermanentWidget(self._progress)
        self._stats_label = QtWidgets.QLabel("")
        self.status_bar.addPermanentWidget(self._stats_label)

    def _connect_signals(self):
        # 树信号
        self.server_tree.project_selected.connect(self._on_project_selected)
        self.server_tree.server_add_requested.connect(self._add_server)
        self.server_tree.project_add_requested.connect(self._add_project_to_server)
        self.server_tree.server_edit_requested.connect(self._edit_server)
        self.server_tree.project_edit_requested.connect(self._edit_project)
        self.server_tree.server_delete_requested.connect(self._delete_server)
        self.server_tree.project_delete_requested.connect(self._delete_project)

    # ---- 操作 ----

    def _refresh_all(self):
        self.server_tree.refresh()

    def _on_project_selected(self, project_id: str):
        project = self.store.find_project(project_id)
        self._current_project = project
        self.info_card.set_project(project, self.store)
        self.history_view.refresh(project_id)
        has_project = project is not None
        self.deploy_btn.setEnabled(has_project)
        self.diff_btn.setEnabled(has_project)
        self.rollback_btn.setEnabled(has_project)
        self.test_conn_btn.setEnabled(has_project)
        self._status_label.setText(f"已选择: {project.name}" if project else "就绪")

    def _start_diff(self):
        if not self._current_project:
            return
        self.diff_btn.setEnabled(False)
        self.deploy_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self.log_panel.info("开始分析文件差异...")
        self._status_label.setText("正在分析差异...")

        self._diff_worker = DiffWorker(self.store, self.pool, self._current_project)
        self._diff_worker.log.connect(self.log_panel.info)
        self._diff_worker.progress.connect(self._on_progress)
        self._diff_worker.failed.connect(self._on_diff_failed)
        self._diff_worker.finished_ok.connect(self._on_diff_done)
        self._diff_worker.start()

    def _on_diff_done(self, diffs: list):
        self._current_diffs = diffs
        self._progress.setVisible(False)
        self.diff_view.set_diffs(diffs)
        self.right_tabs.setCurrentIndex(0)  # 切换到差异预览 tab
        self.diff_btn.setEnabled(True)
        self.deploy_btn.setEnabled(True)
        stats = f"新增:{sum(1 for d in diffs if d.status == DiffStatus.NEW)} "
        stats += f"修改:{sum(1 for d in diffs if d.status == DiffStatus.MODIFIED)} "
        stats += f"删除:{sum(1 for d in diffs if d.status == DiffStatus.DELETED)}"
        self._stats_label.setText(stats)
        self._status_label.setText(f"差异分析完成，共 {len(diffs)} 个文件有变化")

        if not diffs:
            self.log_panel.info("没有发现文件变化，无需部署")
        else:
            self.log_panel.info(f"发现 {len(diffs)} 个文件变化")

    def _on_diff_failed(self, error: str):
        self._progress.setVisible(False)
        self.log_panel.error(f"差异分析失败: {error}")
        self.diff_btn.setEnabled(True)
        self.deploy_btn.setEnabled(True)
        self._status_label.setText("就绪")

    def _start_deploy(self):
        if not self._current_project:
            return
        if not self._current_diffs:
            # 还没对比，先对比
            self._start_diff()
            return

        # 打开部署预览对话框
        dialog = DeployDialog(self._current_diffs, self._current_project, self)
        dialog.deploy_confirmed.connect(self._do_deploy)
        dialog.exec_()

    def _do_deploy(self, selected_diffs: list):
        """执行部署"""
        self.deploy_btn.setEnabled(False)
        self.diff_btn.setEnabled(False)
        self.rollback_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self.log_panel.info("开始部署...")

        self._deploy_worker = DeployWorker(
            self.store, self.pool, self._current_project, selected_diffs)
        self._deploy_worker.log.connect(self.log_panel.info)
        self._deploy_worker.progress.connect(self._on_progress)
        self._deploy_worker.failed.connect(self._on_deploy_failed)
        self._deploy_worker.finished_ok.connect(self._on_deploy_done)
        self._deploy_worker.start()

    def _on_progress(self, current: int, total: int):
        self._progress.setMaximum(total)
        self._progress.setValue(current)

    def _on_deploy_done(self, result):
        self._progress.setVisible(False)
        self.deploy_btn.setEnabled(True)
        self.diff_btn.setEnabled(True)
        self.rollback_btn.setEnabled(True)
        self.log_panel.info("部署成功!")
        self._status_label.setText("部署完成")
        self.history_view.refresh(self._current_project.id if self._current_project else None)

    def _on_deploy_failed(self, error: str):
        self._progress.setVisible(False)
        self.deploy_btn.setEnabled(True)
        self.diff_btn.setEnabled(True)
        self.rollback_btn.setEnabled(True)
        self.log_panel.error(f"部署失败: {error}")
        self._status_label.setText("部署失败")

    def _start_rollback(self):
        if not self._current_project:
            return
        backups = self.store.get_backups_for_project(self._current_project.id)
        if not backups:
            QtWidgets.QMessageBox.information(self, "回滚", "没有可用的备份")
            return
        dialog = RollbackDialog(backups, self._current_project, self)
        dialog.rollback_requested.connect(self._do_rollback)
        dialog.exec_()

    def _do_rollback(self, backup):
        self.rollback_btn.setEnabled(False)
        self.deploy_btn.setEnabled(False)
        self.log_panel.info("开始回滚...")
        self._status_label.setText("正在回滚...")

        self._rollback_worker = RollbackWorker(
            self.store, self.pool, self._current_project, backup)
        self._rollback_worker.log.connect(self.log_panel.info)
        self._rollback_worker.failed.connect(self._on_rollback_failed)
        self._rollback_worker.finished_ok.connect(self._on_rollback_done)
        self._rollback_worker.start()

    def _on_rollback_done(self, _):
        self.rollback_btn.setEnabled(True)
        self.deploy_btn.setEnabled(True)
        self.log_panel.info("回滚完成!")
        self._status_label.setText("回滚完成")

    def _on_rollback_failed(self, error: str):
        self.rollback_btn.setEnabled(True)
        self.deploy_btn.setEnabled(True)
        self.log_panel.error(f"回滚失败: {error}")
        self._status_label.setText("回滚失败")

    def _test_connection(self):
        if not self._current_project:
            return
        sid = self._current_project.server_id
        self.log_panel.info(f"测试连接到服务器...")
        self._test_worker = TestConnectionWorker(self.store, self.pool, sid)
        self._test_worker.log.connect(self.log_panel.info)
        self._test_worker.failed.connect(lambda e: self.log_panel.error(f"连接测试失败: {e}"))
        self._test_worker.finished_ok.connect(lambda r: self.log_panel.info(f"连接测试成功: {r}"))
        self._test_worker.start()

    # ---- 服务器/项目管理 ----

    def _add_server(self):
        dialog = ServerDialog(self.store, parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.store.add_server(dialog.server)
            self.log_panel.info(f"服务器 {dialog.server.name} 已添加")
            self._refresh_all()

    def _edit_server(self, server_id: str):
        server = self.store.find_server(server_id)
        if not server:
            return
        dialog = ServerDialog(self.store, server=server, parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.store.update_server(dialog.server)
            self.log_panel.info(f"服务器 {dialog.server.name} 已更新")
            self._refresh_all()

    def _add_project(self):
        self._add_project_to_server("")

    def _add_project_to_server(self, server_id: str):
        dialog = ProjectDialog(self.store, server_id=server_id, parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.store.add_project(dialog.project)
            self.log_panel.info(f"项目 {dialog.project.name} 已添加")
            self._refresh_all()

    def _edit_project(self, project_id: str):
        project = self.store.find_project(project_id)
        if not project:
            return
        dialog = ProjectDialog(self.store, project=project, parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.store.update_project(dialog.project)
            self.log_panel.info(f"项目 {dialog.project.name} 已更新")
            self._refresh_all()
            # 重新选中当前项目，刷新中栏信息
            self._on_project_selected(project_id)

    def _delete_server(self, server_id: str):
        server = self.store.find_server(server_id)
        if not server:
            return
        reply = QtWidgets.QMessageBox.question(
            self, "确认删除",
            f"确定要删除服务器 \"{server.name}\" 及其所有关联项目吗？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.store.remove_server(server_id)
            self.log_panel.info(f"服务器 {server.name} 已删除")
            self._refresh_all()

    def _delete_project(self, project_id: str):
        project = self.store.find_project(project_id)
        if not project:
            return
        reply = QtWidgets.QMessageBox.question(
            self, "确认删除",
            f"确定要删除项目 \"{project.name}\" 吗？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.store.remove_project(project_id)
            self.log_panel.info(f"项目 {project.name} 已删除")
            self._refresh_all()

    def _open_settings(self):
        dialog = SettingsDialog(self.store, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            apply_theme(QtWidgets.QApplication.instance(), self.store.config.theme)
            self.log_panel.info("设置已保存")

    def _about(self):
        QtWidgets.QMessageBox.about(
            self, "关于部署工具",
            "<h2>部署工具 v0.1</h2>"
            "<p>基于 PyQt5 的代码部署工具</p>"
            "<p>支持 HTML / Vue / PHP / Go / Node.js 项目一键部署</p>",
        )

    # ---- 生命周期 ----

    def closeEvent(self, event):
        self.pool.close_all()
        event.accept()
