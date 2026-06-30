"""同步引擎 — 上传 / 删除文件"""
import os
from typing import Callable

from ...config.models import Project
from ..ssh.client import SSHClient


class SyncEngine:
    """文件同步执行器"""

    def __init__(self, project: Project, ssh: SSHClient):
        self.project = project
        self.ssh = ssh

    def upload_file(self, rel_path: str, progress_cb: Callable = None) -> int:
        """上传单个文件到远程，返回文件大小"""
        local = os.path.join(
            self.project.local_path, rel_path.replace("/", os.sep)
        )
        remote = f"{self.project.remote_path}/{rel_path}"
        self._ensure_remote_dir(os.path.dirname(remote))
        sftp = self.ssh.sftp()
        size = os.path.getsize(local)
        sftp.put(local, remote, callback=progress_cb)
        return size

    def delete_remote(self, rel_path: str):
        """删除远程文件"""
        remote = f"{self.project.remote_path}/{rel_path}"
        sftp = self.ssh.sftp()
        try:
            sftp.remove(remote)
        except IOError:
            pass

    def _ensure_remote_dir(self, remote_dir: str):
        """确保远程目录存在（mkdir -p 行为）"""
        sftp = self.ssh.sftp()
        parts = remote_dir.strip("/").split("/")
        cur = ""
        for p in parts:
            cur += "/" + p
            try:
                sftp.stat(cur)
            except IOError:
                try:
                    sftp.mkdir(cur)
                except IOError:
                    pass
