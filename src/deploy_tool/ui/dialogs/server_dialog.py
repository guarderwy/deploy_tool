"""服务器配置对话框"""
import time

from PyQt5 import QtWidgets, QtCore, QtGui

from ...config.models import Server, AuthMethod, ProxyType, ProxyConfig
from ...config.store import ConfigStore


class ServerDialog(QtWidgets.QDialog):
    """服务器配置对话框 — 添加 / 编辑"""

    def __init__(self, store: ConfigStore, server: Server = None, parent=None):
        super().__init__(parent)
        self.store = store
        self.server = server or Server()
        self._is_edit = server is not None
        self.setWindowTitle("编辑服务器" if self._is_edit else "添加服务器")
        self.resize(520, 600)
        self._init_ui()
        if self._is_edit:
            self._load_data()

    def _init_ui(self):
        main = QtWidgets.QVBoxLayout(self)

        # 基本信息
        g1 = QtWidgets.QGroupBox("基本信息")
        f1 = QtWidgets.QFormLayout(g1)

        self.name_edit = QtWidgets.QLineEdit()
        f1.addRow("名称:", self.name_edit)

        self.host_edit = QtWidgets.QLineEdit()
        f1.addRow("主机:", self.host_edit)

        self.port_spin = QtWidgets.QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)
        f1.addRow("端口:", self.port_spin)

        self.user_edit = QtWidgets.QLineEdit("root")
        f1.addRow("用户名:", self.user_edit)

        main.addWidget(g1)

        # 认证
        g2 = QtWidgets.QGroupBox("认证方式")
        f2 = QtWidgets.QFormLayout(g2)

        self.auth_combo = QtWidgets.QComboBox()
        self.auth_combo.addItems(["密码", "密钥文件"])
        self.auth_combo.currentIndexChanged.connect(self._on_auth_changed)
        f2.addRow("认证:", self.auth_combo)

        self.password_edit = QtWidgets.QLineEdit()
        self.password_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        f2.addRow("密码:", self.password_edit)

        self.key_path_edit = QtWidgets.QLineEdit()
        self.key_path_layout = QtWidgets.QHBoxLayout()
        self.key_path_layout.addWidget(self.key_path_edit)
        browse_btn = QtWidgets.QPushButton("浏览...")
        browse_btn.setFixedWidth(70)
        browse_btn.clicked.connect(self._browse_key)
        self.key_path_layout.addWidget(browse_btn)
        f2.addRow("私钥:", self.key_path_layout)

        self.key_pass_edit = QtWidgets.QLineEdit()
        self.key_pass_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        f2.addRow("口令:", self.key_pass_edit)

        main.addWidget(g2)

        # 代理
        g3 = QtWidgets.QGroupBox("代理设置 (境外服务器)")
        self._proxy_group = g3
        f3 = QtWidgets.QFormLayout(g3)

        self.proxy_combo = QtWidgets.QComboBox()
        self.proxy_combo.addItems(["无代理", "SSH 跳板 (ProxyJump)", "SOCKS5", "HTTP"])
        self.proxy_combo.currentIndexChanged.connect(self._on_proxy_changed)
        f3.addRow("代理类型:", self.proxy_combo)

        # SOCKS5/HTTP 字段
        self.proxy_host = QtWidgets.QLineEdit()
        self.proxy_port = QtWidgets.QSpinBox()
        self.proxy_port.setRange(1, 65535)
        self.proxy_port.setValue(1080)
        self.proxy_user = QtWidgets.QLineEdit()
        self.proxy_password = QtWidgets.QLineEdit()
        self.proxy_password.setEchoMode(QtWidgets.QLineEdit.Password)

        hl = QtWidgets.QHBoxLayout()
        hl.addWidget(self.proxy_host)
        hl.addWidget(QtWidgets.QLabel(":"))
        hl.addWidget(self.proxy_port)
        f3.addRow("代理地址:", hl)
        self._proxy_host_row = f3.rowCount() - 1

        f3.addRow("代理用户:", self.proxy_user)
        self._proxy_user_row = f3.rowCount() - 1
        f3.addRow("代理密码:", self.proxy_password)
        self._proxy_pass_row = f3.rowCount() - 1

        # ProxyJump 字段
        self.jump_host = QtWidgets.QLineEdit()
        self.jump_port = QtWidgets.QSpinBox()
        self.jump_port.setRange(1, 65535)
        self.jump_port.setValue(22)
        self.jump_user = QtWidgets.QLineEdit("root")
        self.jump_password = QtWidgets.QLineEdit()
        self.jump_password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.jump_key_edit = QtWidgets.QLineEdit()
        self.jump_auth_combo = QtWidgets.QComboBox()
        self.jump_auth_combo.addItems(["密码", "密钥文件"])

        jl = QtWidgets.QHBoxLayout()
        jl.addWidget(self.jump_host)
        jl.addWidget(QtWidgets.QLabel(":"))
        jl.addWidget(self.jump_port)
        f3.addRow("跳板主机:", jl)
        self._jump_host_row = f3.rowCount() - 1
        f3.addRow("跳板用户:", self.jump_user)
        self._jump_user_row = f3.rowCount() - 1
        f3.addRow("跳板认证:", self.jump_auth_combo)
        self._jump_auth_row = f3.rowCount() - 1
        f3.addRow("跳板密码:", self.jump_password)
        self._jump_pass_row = f3.rowCount() - 1
        f3.addRow("跳板密钥:", self.jump_key_edit)
        self._jump_key_row = f3.rowCount() - 1

        main.addWidget(g3)

        # 按钮
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        self.test_btn = QtWidgets.QPushButton("测试连接")
        self.test_btn.clicked.connect(self._test_connection)
        btn_layout.addWidget(self.test_btn)
        save_btn = QtWidgets.QPushButton("保存")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        main.addLayout(btn_layout)

        self._on_auth_changed()
        self._on_proxy_changed()

    def _on_auth_changed(self):
        is_key = self.auth_combo.currentIndex() == 1
        self.password_edit.setVisible(not is_key)
        self.key_path_edit.setVisible(is_key)
        self.key_pass_edit.setVisible(is_key)

    def _on_proxy_changed(self):
        idx = self.proxy_combo.currentIndex()
        is_socks_http = idx in (2, 3)  # SOCKS5 or HTTP
        is_jump = idx == 1

        for row in (self._proxy_host_row, self._proxy_user_row, self._proxy_pass_row):
            self._set_row_visible(row, is_socks_http)
        for row in (self._jump_host_row, self._jump_user_row, self._jump_auth_row,
                     self._jump_pass_row, self._jump_key_row):
            self._set_row_visible(row, is_jump)

    def _set_row_visible(self, row: int, visible: bool):
        layout = self._proxy_group.layout()
        item = layout.itemAt(row, QtWidgets.QFormLayout.FieldRole)
        if item is None:
            return
        w = item.widget()
        if w is not None:
            w.setVisible(visible)
        elif item.layout() is not None:
            for i in range(item.layout().count()):
                child = item.layout().itemAt(i).widget()
                if child is not None:
                    child.setVisible(visible)

    def _browse_key(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "选择私钥文件", "", "所有文件 (*.*)")
        if path:
            self.key_path_edit.setText(path)

    def _test_connection(self):
        self.test_btn.setEnabled(False)
        self.test_btn.setText("连接中...")
        QtCore.QTimer.singleShot(100, self._do_test)

    def _do_test(self):
        try:
            from ...core.ssh.client import SSHClient
            srv = self._build_server()
            client = SSHClient(srv, self.store.decrypt_credential)
            client.connect(timeout=10)
            code, out, err = client.exec("echo OK && uname -a")
            client.close()
            QtWidgets.QMessageBox.information(
                self, "测试成功", f"连接成功!\n{out.strip()}")
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self, "测试失败", f"连接失败:\n{e}")
        finally:
            self.test_btn.setEnabled(True)
            self.test_btn.setText("测试连接")

    def _build_server(self) -> Server:
        srv = Server(
            id=self.server.id,
            name=self.name_edit.text().strip(),
            host=self.host_edit.text().strip(),
            port=self.port_spin.value(),
            username=self.user_edit.text().strip(),
            auth_method=AuthMethod.KEY if self.auth_combo.currentIndex() == 1 else AuthMethod.PASSWORD,
            created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        )
        if srv.auth_method == AuthMethod.PASSWORD:
            plain = self.password_edit.text()
            if plain:
                srv.password = self.store.encrypt_credential(plain)
            elif self._is_edit and self.server.password:
                srv.password = self.server.password
        else:
            srv.key_path = self.key_path_edit.text().strip()
            plain = self.key_pass_edit.text()
            if plain:
                srv.key_passphrase = self.store.encrypt_credential(plain)
            elif self._is_edit and self.server.key_passphrase:
                srv.key_passphrase = self.server.key_passphrase

        # 代理
        proxy_type_map = {0: ProxyType.NONE, 1: ProxyType.PROXYJUMP, 2: ProxyType.SOCKS5, 3: ProxyType.HTTP}
        ptype = proxy_type_map[self.proxy_combo.currentIndex()]
        proxy = ProxyConfig(type=ptype)
        if ptype in (ProxyType.SOCKS5, ProxyType.HTTP):
            proxy.host = self.proxy_host.text().strip()
            proxy.port = self.proxy_port.value()
            proxy.username = self.proxy_user.text().strip()
            pp = self.proxy_password.text()
            if pp:
                proxy.password = self.store.encrypt_credential(pp)
        elif ptype == ProxyType.PROXYJUMP:
            proxy.jump_host = self.jump_host.text().strip()
            proxy.jump_port = self.jump_port.value()
            proxy.jump_username = self.jump_user.text().strip()
            proxy.jump_auth_method = AuthMethod.KEY if self.jump_auth_combo.currentIndex() == 1 else AuthMethod.PASSWORD
            jp = self.jump_password.text()
            if jp:
                proxy.jump_password = self.store.encrypt_credential(jp)
            proxy.jump_key_path = self.jump_key_edit.text().strip()
        srv.proxy = proxy
        return srv

    def _save(self):
        self.server = self._build_server()
        self.accept()

    def _load_data(self):
        s = self.server
        self.name_edit.setText(s.name)
        self.host_edit.setText(s.host)
        self.port_spin.setValue(s.port)
        self.user_edit.setText(s.username)
        self.auth_combo.setCurrentIndex(0 if s.auth_method == AuthMethod.PASSWORD else 1)
        self.key_path_edit.setText(s.key_path)
        # 密码不反填（加密存储）
        ptype_map = {ProxyType.NONE: 0, ProxyType.PROXYJUMP: 1, ProxyType.SOCKS5: 2, ProxyType.HTTP: 3}
        self.proxy_combo.setCurrentIndex(ptype_map.get(s.proxy.type, 0))
        self.proxy_host.setText(s.proxy.host)
        self.proxy_port.setValue(s.proxy.port)
        self.proxy_user.setText(s.proxy.username)
        self.jump_host.setText(s.proxy.jump_host)
        self.jump_port.setValue(s.proxy.jump_port)
        self.jump_user.setText(s.proxy.jump_username)
