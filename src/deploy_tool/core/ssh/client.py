"""SSH 客户端 — paramiko 封装，支持代理/双认证"""
import paramiko
from typing import Optional, Callable, Tuple

from ...config.models import Server, AuthMethod, ProxyType
from .proxy import make_socks5_socket, make_http_connect_socket, make_proxyjump_channel


class SSHClient:
    """封装 paramiko，支持 ProxyJump/SOCKS5/HTTP 代理和密码/密钥双认证"""

    def __init__(self, server: Server, decrypt_fn: Callable[[str], str]):
        self.server = server
        self._decrypt = decrypt_fn
        self._client: Optional[paramiko.SSHClient] = None
        self._jump: Optional[paramiko.SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None

    def connect(self, timeout: int = 30):
        """建立 SSH 连接"""
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        sock = self._build_socket(timeout)
        kwargs = self._auth_kwargs()
        if sock is not None:
            kwargs["sock"] = sock
        self._client.connect(
            self.server.host,
            port=self.server.port,
            timeout=timeout,
            **kwargs,
        )
        self._client.get_transport().set_keepalive(30)

    def _build_socket(self, timeout: int):
        """根据代理类型构建 socket"""
        p = self.server.proxy
        if p.type == ProxyType.SOCKS5:
            return make_socks5_socket(
                p.host, p.port,
                self.server.host, self.server.port,
                p.username or None,
                self._decrypt(p.password) if p.password else None,
                timeout,
            )
        if p.type == ProxyType.HTTP:
            return make_http_connect_socket(
                p.host, p.port,
                self.server.host, self.server.port,
                p.username or None,
                self._decrypt(p.password) if p.password else None,
                timeout,
            )
        if p.type == ProxyType.PROXYJUMP:
            self._jump = paramiko.SSHClient()
            self._jump.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._jump.connect(
                p.jump_host,
                port=p.jump_port,
                username=p.jump_username,
                **_jump_auth_kwargs(p, self._decrypt),
                timeout=timeout,
            )
            self._jump.get_transport().set_keepalive(30)
            return make_proxyjump_channel(
                self._jump, self.server.host, self.server.port, timeout
            )
        return None

    def _auth_kwargs(self) -> dict:
        """构建认证参数"""
        base = {
            "username": self.server.username,
            "look_for_keys": False,
            "allow_agent": False,
        }
        if self.server.auth_method == AuthMethod.PASSWORD:
            base["password"] = self._decrypt(self.server.password)
        else:
            base["key_filename"] = self.server.key_path
            passphrase = self._decrypt(self.server.key_passphrase)
            if passphrase:
                base["passphrase"] = passphrase
        return base

    # ---- SFTP ----

    def sftp(self) -> paramiko.SFTPClient:
        """获取 SFTP 客户端（惰性创建）"""
        if self._sftp is None:
            self._sftp = self._client.open_sftp()
        return self._sftp

    # ---- 命令执行 ----

    def exec(self, cmd: str, timeout: int = 60) -> Tuple[int, str, str]:
        """执行远程命令，返回 (exit_code, stdout, stderr)"""
        stdin, stdout, stderr = self._client.exec_command(cmd, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        return (
            exit_code,
            stdout.read().decode("utf-8", "replace"),
            stderr.read().decode("utf-8", "replace"),
        )

    # ---- 状态 ----

    @property
    def is_connected(self) -> bool:
        if self._client is None:
            return False
        transport = self._client.get_transport()
        return transport is not None and transport.is_active()

    def close(self):
        if self._sftp:
            self._sftp.close()
            self._sftp = None
        if self._client:
            self._client.close()
            self._client = None
        if self._jump:
            self._jump.close()
            self._jump = None


def _jump_auth_kwargs(proxy, decrypt_fn) -> dict:
    """跳板机认证参数"""
    base = {"look_for_keys": False, "allow_agent": False}
    if proxy.jump_auth_method == AuthMethod.PASSWORD:
        base["password"] = decrypt_fn(proxy.jump_password)
    else:
        base["key_filename"] = proxy.jump_key_path
    return base
