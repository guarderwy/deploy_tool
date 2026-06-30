"""远程备份 & 回滚模块"""
import time
from typing import Optional

from ..config.models import Project, BackupInfo
from .ssh.client import SSHClient


class BackupManager:
    """远程备份管理：tar 打包 + 回滚恢复"""

    def __init__(self, project: Project, ssh: SSHClient, store):
        self.project = project
        self.ssh = ssh
        self.store = store

    def create_backup(self, deploy_record_id: str) -> BackupInfo:
        """在远程服务器上创建 tar.gz 备份"""
        rp = self.project.remote_path.rstrip("/")
        parent = rp.rsplit("/", 1)[0] or "/"
        base = rp.rsplit("/", 1)[1]
        ts = time.strftime("%Y%m%d_%H%M%S")
        tar_path = f"/tmp/deploy_tool_backup_{self.project.id[:8]}_{ts}.tar.gz"

        cmd = f"tar czf {tar_path} -C {parent} {base} 2>&1"
        code, out, err = self.ssh.exec(cmd, timeout=120)
        if code != 0:
            raise RuntimeError(f"备份失败: {out}{err}")

        # 获取备份文件大小
        code2, out2, _ = self.ssh.exec(f"stat -c '%s' {tar_path}")
        size = int(out2.strip()) if code2 == 0 else 0

        info = BackupInfo(
            project_id=self.project.id,
            server_id=self.project.server_id,
            created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            remote_tar_path=tar_path,
            file_count=0,
            size_bytes=size,
            deploy_record_id=deploy_record_id,
        )
        self.store.add_backup(info)
        self._prune_old_backups()
        return info

    def rollback(self, backup: BackupInfo) -> None:
        """回滚到指定备份"""
        rp = self.project.remote_path.rstrip("/")
        parent = rp.rsplit("/", 1)[0] or "/"

        # 受控内部命令 — 路径已在调用前经过 validate_remote_path 校验
        cmd = (
            f"rm -rf {rp}/* {rp}/.[!.]* 2>/dev/null; "
            f"tar xzf {backup.remote_tar_path} -C {parent} 2>&1"
        )
        code, out, err = self.ssh.exec(cmd, timeout=120)
        if code != 0:
            raise RuntimeError(f"回滚失败: {out}{err}")

    def list_backups(self) -> list[BackupInfo]:
        """列出该项目的所有备份"""
        return [
            b for b in self.store.config.backups
            if b.project_id == self.project.id
        ]

    def delete_backup(self, backup: BackupInfo):
        """删除远程备份文件 + 本地记录"""
        self.ssh.exec(f"rm -f {backup.remote_tar_path}")
        self.store.config.backups = [
            b for b in self.store.config.backups if b.id != backup.id
        ]
        self.store.save()

    def _prune_old_backups(self):
        """保留最近 max_backups 个备份，删除旧的"""
        project_backups = sorted(
            [b for b in self.store.config.backups if b.project_id == self.project.id],
            key=lambda b: b.created_at,
            reverse=True,
        )
        max_keep = self.project.max_backups or self.store.config.max_backups_per_project
        for old in project_backups[max_keep:]:
            self.delete_backup(old)
