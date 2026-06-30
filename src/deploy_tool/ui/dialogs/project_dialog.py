"""项目配置对话框"""
import time
import os

from PyQt5 import QtWidgets, QtCore, QtGui

from ...config.models import Project
from ...config.store import ConfigStore
from ...config.presets import apply_preset, get_preset_list, PROJECT_PRESETS


class RemoteBrowserDialog(QtWidgets.QDialog):
    """远程目录浏览对话框 — 通过 SSH 浏览服务器目录"""

    selected_path = ""

    def __init__(self, store: ConfigStore, server_id: str, parent=None):
        super().__init__(parent)
        self.store = store
        self.server_id = server_id
        self.setWindowTitle("浏览远程目录")
        self.resize(500, 450)
        self._client = None
        self._current_path = "/"
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # 地址栏
        addr_layout = QtWidgets.QHBoxLayout()
        self._path_combo = QtWidgets.QComboBox()
        self._path_combo.setEditable(True)
        self._path_combo.setCurrentText("/")
        self._path_combo.activated.connect(self._on_path_selected)
        addr_layout.addWidget(self._path_combo)

        self._go_btn = QtWidgets.QPushButton("转到")
        self._go_btn.clicked.connect(self._go_to_path)
        addr_layout.addWidget(self._go_btn)
        layout.addLayout(addr_layout)

        # 目录树
        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderLabels(["目录"])
        self._tree.setHeaderHidden(True)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._tree)

        # 按钮
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        self._select_btn = QtWidgets.QPushButton("选择当前目录")
        self._select_btn.setObjectName("primaryBtn")
        self._select_btn.clicked.connect(self._select_current)
        btn_layout.addWidget(self._select_btn)
        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self._connect_and_list()

    def _connect_and_list(self, path: str = "/"):
        """SSH 连接并列出目录内容"""
        try:
            server = self.store.find_server(self.server_id)
            if not server:
                QtWidgets.QMessageBox.warning(self, "错误", "未找到服务器配置")
                return

            from ...core.ssh.client import SSHClient
            self._client = SSHClient(server, self.store.decrypt_credential)
            self._client.connect(timeout=10)
            self._list_dir(path)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "连接失败", f"无法连接到服务器:\n{e}")

    def _list_dir(self, path: str):
        """列出远程目录"""
        path = path.rstrip("/") or "/"
        self._current_path = path
        self._path_combo.setCurrentText(path)
        self._tree.clear()

        try:
            # 避免根目录时产生 // 前缀
            pattern = "/*/ /.*/" if path == "/" else f"{path}/*/ {path}/.*/"
            code, out, err = self._client.exec(
                f"ls -1d {pattern} 2>/dev/null"
            )
            dirs = out.strip().splitlines()
            dirs = [d.rstrip("/") for d in dirs if d.strip()]

            # 添加入口
            if path != "/":
                parent_item = QtWidgets.QTreeWidgetItem([".."])
                parent_item.setData(0, QtCore.Qt.UserRole, self._parent_path(path))
                parent_item.setIcon(0, self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogBack))
                self._tree.addTopLevelItem(parent_item)

            for d in sorted(dirs):
                name = d.rsplit("/", 1)[-1]
                item = QtWidgets.QTreeWidgetItem([name])
                item.setData(0, QtCore.Qt.UserRole, d)
                item.setIcon(0, self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
                self._tree.addTopLevelItem(item)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "错误", f"列出目录失败:\n{e}")

    def _parent_path(self, path: str) -> str:
        path = path.rstrip("/")
        if "/" not in path:
            return "/"
        return path.rsplit("/", 1)[0] or "/"

    def _on_item_double_clicked(self, item: QtWidgets.QTreeWidgetItem, column: int):
        path = item.data(0, QtCore.Qt.UserRole)
        if path:
            self._list_dir(path)

    def _on_path_selected(self, index: int):
        path = self._path_combo.currentText()
        if path:
            self._list_dir(path)

    def _go_to_path(self):
        path = self._path_combo.currentText().strip()
        if path:
            self._list_dir(path)

    def _select_current(self):
        self.selected_path = self._current_path
        self.accept()

    def closeEvent(self, event):
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
        event.accept()


class ProjectDialog(QtWidgets.QDialog):
    """项目配置对话框 — 添加 / 编辑"""

    def __init__(self, store: ConfigStore, server_id: str = "",
                 project: Project = None, parent=None):
        super().__init__(parent)
        self.store = store
        self.server_id = server_id
        self.project = project or Project()
        self._is_edit = project is not None
        if server_id:
            self.project.server_id = server_id

        self.setWindowTitle("编辑项目" if self._is_edit else "添加项目")
        self.resize(580, 720)
        self._init_ui()
        if self._is_edit:
            self._load_data()

    def _init_ui(self):
        main = QtWidgets.QVBoxLayout(self)

        # 基本信息
        g1 = QtWidgets.QGroupBox("基本信息")
        f1 = QtWidgets.QFormLayout(g1)

        self.name_edit = QtWidgets.QLineEdit()
        f1.addRow("项目名称:", self.name_edit)

        self.server_combo = QtWidgets.QComboBox()
        self._refresh_servers()
        if self.server_id:
            idx = self.server_combo.findData(self.server_id)
            if idx >= 0:
                self.server_combo.setCurrentIndex(idx)
        f1.addRow("关联服务器:", self.server_combo)

        self.type_combo = QtWidgets.QComboBox()
        presets = get_preset_list()
        for p in presets:
            self.type_combo.addItem(p["label"], p["id"])
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        f1.addRow("项目类型:", self.type_combo)

        main.addWidget(g1)

        # 路径
        g2 = QtWidgets.QGroupBox("路径设置")
        f2 = QtWidgets.QFormLayout(g2)

        self.local_edit = QtWidgets.QLineEdit()
        local_hl = QtWidgets.QHBoxLayout()
        local_hl.addWidget(self.local_edit)
        browse_local = QtWidgets.QPushButton("浏览...")
        browse_local.setFixedWidth(70)
        browse_local.clicked.connect(self._browse_local)
        local_hl.addWidget(browse_local)
        f2.addRow("本地路径:", local_hl)

        self.remote_edit = QtWidgets.QLineEdit()
        remote_hl = QtWidgets.QHBoxLayout()
        remote_hl.addWidget(self.remote_edit)
        browse_remote = QtWidgets.QPushButton("浏览...")
        browse_remote.setFixedWidth(70)
        browse_remote.clicked.connect(self._browse_remote)
        remote_hl.addWidget(browse_remote)
        f2.addRow("远程路径:", remote_hl)
        main.addWidget(g2)

        # GitHub 配置（仅 Git 类型可见）
        self._github_group = QtWidgets.QGroupBox("GitHub 配置")
        gf = QtWidgets.QFormLayout(self._github_group)

        self.github_repo_edit = QtWidgets.QLineEdit()
        self.github_repo_edit.setPlaceholderText("owner/repo (如: user/my-project)")
        gf.addRow("仓库地址:", self.github_repo_edit)

        self.github_branch_edit = QtWidgets.QLineEdit("main")
        gf.addRow("分支:", self.github_branch_edit)

        self.github_token_edit = QtWidgets.QLineEdit()
        self.github_token_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.github_token_edit.setPlaceholderText("Personal Access Token (可选)")
        gf.addRow("Token:", self.github_token_edit)

        self._github_group.setVisible(False)
        main.addWidget(self._github_group)

        # 排除规则
        g3 = QtWidgets.QGroupBox("排除规则 (gitignore 风格)")
        f3 = QtWidgets.QVBoxLayout(g3)
        self.exclude_edit = QtWidgets.QPlainTextEdit()
        self.exclude_edit.setPlaceholderText("每行一个规则，如:\n.git/\nnode_modules/\n*.log")
        f3.addWidget(self.exclude_edit)
        main.addWidget(g3)

        # 命令
        g4 = QtWidgets.QGroupBox("前置 / 后置命令 (部署前 / 后在服务器上执行)")
        f4 = QtWidgets.QFormLayout(g4)

        pre_vbox = QtWidgets.QVBoxLayout()
        self.pre_enable_check = QtWidgets.QCheckBox("启用前置命令")
        self.pre_enable_check.setChecked(False)
        pre_vbox.addWidget(self.pre_enable_check)
        self.pre_cmd_edit = QtWidgets.QPlainTextEdit()
        self.pre_cmd_edit.setPlaceholderText("每行一条命令，如:\ncd /var/www/project")
        self.pre_cmd_edit.setFixedHeight(60)
        pre_vbox.addWidget(self.pre_cmd_edit)
        f4.addRow("前置命令:", pre_vbox)

        post_vbox = QtWidgets.QVBoxLayout()
        self.post_enable_check = QtWidgets.QCheckBox("启用后置命令")
        self.post_enable_check.setChecked(False)
        post_vbox.addWidget(self.post_enable_check)
        self.post_cmd_edit = QtWidgets.QPlainTextEdit()
        self.post_cmd_edit.setPlaceholderText("每行一条命令，如:\npm2 restart app")
        self.post_cmd_edit.setFixedHeight(60)
        post_vbox.addWidget(self.post_cmd_edit)
        f4.addRow("后置命令:", post_vbox)

        main.addWidget(g4)

        # 备份
        g5 = QtWidgets.QGroupBox("备份设置")
        f5 = QtWidgets.QFormLayout(g5)

        self.backup_check = QtWidgets.QCheckBox("启用部署前自动备份")
        self.backup_check.setChecked(True)
        f5.addRow(self.backup_check)

        self.max_backups = QtWidgets.QSpinBox()
        self.max_backups.setRange(1, 50)
        self.max_backups.setValue(5)
        f5.addRow("最大备份数:", self.max_backups)

        self.sync_combo = QtWidgets.QComboBox()
        self.sync_combo.addItems(["大小对比 (快速)", "SHA256 哈希 (精确)", "Git 版本对比"])
        f5.addRow("对比模式:", self.sync_combo)
        main.addWidget(g5)

        # 按钮
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QtWidgets.QPushButton("保存")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        main.addLayout(btn_layout)

        self._on_type_changed()

    def _refresh_servers(self):
        self.server_combo.clear()
        for s in self.store.config.servers:
            self.server_combo.addItem(f"{s.name} ({s.host})", s.id)

    def _on_type_changed(self):
        ptype = self.type_combo.currentData()
        is_git = ptype == "git"
        self._github_group.setVisible(is_git)
        if ptype:
            preset = PROJECT_PRESETS.get(ptype)
            if preset:
                self.exclude_edit.setPlainText(
                    "\n".join(preset.get("exclude_patterns", []))
                )
                self.pre_cmd_edit.setPlainText(
                    "\n".join(preset.get("pre_deploy_commands", []))
                )
                self.post_cmd_edit.setPlainText(
                    "\n".join(preset.get("post_deploy_commands", []))
                )
            self.pre_enable_check.setChecked(False)
            self.post_enable_check.setChecked(False)

    def _browse_local(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "选择本地项目目录")
        if path:
            self.local_edit.setText(path)

    def _browse_remote(self):
        server_id = self.server_combo.currentData()
        if not server_id:
            QtWidgets.QMessageBox.warning(self, "提示", "请先选择关联服务器")
            return
        dialog = RemoteBrowserDialog(self.store, server_id, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted and dialog.selected_path:
            self.remote_edit.setText(dialog.selected_path)

    def _save(self):
        ptype = self.type_combo.currentData()
        self.project = apply_preset(self.project, ptype)
        self.project.name = self.name_edit.text().strip()
        self.project.server_id = self.server_combo.currentData()
        self.project.local_path = self.local_edit.text().strip()
        self.project.remote_path = self.remote_edit.text().strip()
        self.project.exclude_patterns = [
            line.strip() for line in self.exclude_edit.toPlainText().splitlines()
            if line.strip()
        ]
        self.project.pre_deploy_commands = [
            line.strip() for line in self.pre_cmd_edit.toPlainText().splitlines()
            if line.strip()
        ]
        self.project.post_deploy_commands = [
            line.strip() for line in self.post_cmd_edit.toPlainText().splitlines()
            if line.strip()
        ]
        self.project.enable_pre_commands = self.pre_enable_check.isChecked()
        self.project.enable_post_commands = self.post_enable_check.isChecked()
        self.project.enable_backup = self.backup_check.isChecked()
        self.project.max_backups = self.max_backups.value()
        self.project.sync_mode = ["size_mtime", "hash", "git_diff"][self.sync_combo.currentIndex()]
        self.project.github_repo = self.github_repo_edit.text().strip()
        self.project.github_branch = self.github_branch_edit.text().strip()
        token = self.github_token_edit.text()
        if token:
            self.project.github_token = self.store.encrypt_credential(token)
        elif self._is_edit and self.project.github_token:
            pass  # 保留已有 token
        else:
            self.project.github_token = ""
        self.project.created_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self.accept()

    def _load_data(self):
        p = self.project
        self.name_edit.setText(p.name)
        # 阻止信号，避免 setCurrentIndex 触发 _on_type_changed 覆盖已加载的数据
        self.type_combo.blockSignals(True)
        idx = self.type_combo.findData(p.project_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        self.type_combo.blockSignals(False)
        self.local_edit.setText(p.local_path)
        self.remote_edit.setText(p.remote_path)
        self.exclude_edit.setPlainText("\n".join(p.exclude_patterns))
        self.pre_cmd_edit.setPlainText("\n".join(p.pre_deploy_commands))
        self.post_cmd_edit.setPlainText("\n".join(p.post_deploy_commands))
        self.pre_enable_check.setChecked(p.enable_pre_commands)
        self.post_enable_check.setChecked(p.enable_post_commands)
        self.backup_check.setChecked(p.enable_backup)
        self.max_backups.setValue(p.max_backups)
        idx_map = {"size_mtime": 0, "hash": 1, "git_diff": 2}
        self.sync_combo.setCurrentIndex(idx_map.get(p.sync_mode, 0))
        self.github_repo_edit.setText(p.github_repo)
        self.github_branch_edit.setText(p.github_branch)
        # token 不反填（加密存储）
