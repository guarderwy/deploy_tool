"""远程命令执行器"""
from .ssh.client import SSHClient
from .safety import assert_command_safe


class CommandRunner:
    """带安全检查的远程命令执行器"""

    def __init__(self, ssh: SSHClient):
        self.ssh = ssh

    def run_checked(self, cmd: str, timeout: int = 120) -> str:
        """执行命令（通过安全检查后），返回 stdout"""
        assert_command_safe(cmd)
        code, out, err = self.ssh.exec(cmd, timeout=timeout)
        if code != 0:
            raise RuntimeError(
                f"命令执行失败(code={code}): {cmd}\nstdout: {out}\nstderr: {err}"
            )
        return out

    def run_raw(self, cmd: str, timeout: int = 120) -> tuple[int, str, str]:
        """执行命令不经过安全检查（内部操作使用）"""
        return self.ssh.exec(cmd, timeout=timeout)
