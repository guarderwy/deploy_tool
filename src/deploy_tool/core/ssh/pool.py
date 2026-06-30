"""SSH 连接池 — 按 server_id 复用连接"""
import time
from typing import Dict

from .client import SSHClient


class ConnectionPool:
    """按 server_id 复用 SSH 连接，空闲超时自动关闭"""

    IDLE_TIMEOUT = 600  # 10 分钟

    def __init__(self, store):
        self.store = store
        self._conns: Dict[str, SSHClient] = {}
        self._last_used: Dict[str, float] = {}

    def get(self, server_id: str) -> SSHClient:
        """获取或创建连接"""
        self._cleanup()
        if server_id not in self._conns:
            server = self.store.find_server(server_id)
            if server is None:
                raise ValueError(f"服务器不存在: {server_id}")
            client = SSHClient(server, self.store.decrypt_credential)
            client.connect()
            self._conns[server_id] = client
        self._last_used[server_id] = time.time()
        return self._conns[server_id]

    def close(self, server_id: str):
        """关闭并移除连接"""
        c = self._conns.pop(server_id, None)
        if c:
            c.close()
        self._last_used.pop(server_id, None)

    def close_all(self):
        """关闭所有连接"""
        for c in self._conns.values():
            c.close()
        self._conns.clear()
        self._last_used.clear()

    def _cleanup(self):
        """清理空闲超时的连接"""
        now = time.time()
        for sid in list(self._last_used.keys()):
            if now - self._last_used[sid] > self.IDLE_TIMEOUT:
                self.close(sid)
