"""部署编排器 — 串联所有部署步骤"""
import time
from typing import List, Callable

from ..config.models import (
    Project, FileDiff, DeployRecord, DiffStatus,
)
from .ssh.pool import ConnectionPool
from .sync.engine import SyncEngine
from .backup import BackupManager
from .commands import CommandRunner
from .safety import assert_command_safe, validate_remote_path, SafetyError


class DeployResult:
    """部署结果"""

    def __init__(self):
        self.record = DeployRecord()
        self.error: Exception | None = None


class Deployer:
    """部署编排器"""

    def __init__(self, project: Project, pool: ConnectionPool, store):
        self.project = project
        self.pool = pool
        self.store = store

    def deploy(
        self,
        selected_diffs: List[FileDiff],
        progress_cb: Callable = None,
        log_cb: Callable = None,
    ) -> DeployResult:
        """执行部署流程"""
        result = DeployResult()
        rec = result.record
        rec.project_id = self.project.id
        rec.server_id = self.project.server_id
        rec.started_at = time.strftime("%Y-%m-%d %H:%M:%S")

        def _log(msg: str):
            if log_cb:
                log_cb(msg)

        try:
            ssh = self.pool.get(self.project.server_id)

            # 1. 安全校验
            _log("安全检查...")
            validate_remote_path(self.project.remote_path, self.project.remote_path)
            check_cmds = []
            if self.project.enable_pre_commands:
                check_cmds += self.project.pre_deploy_commands
            if self.project.enable_post_commands:
                check_cmds += self.project.post_deploy_commands
            for cmd in check_cmds:
                assert_command_safe(cmd)

            # 2. 备份
            if self.project.enable_backup:
                _log("创建远程备份...")
                bm = BackupManager(self.project, ssh, self.store)
                backup = bm.create_backup(rec.id)
                rec.backup_id = backup.id

            # 3. 前置命令
            if self.project.enable_pre_commands:
                cmd_runner = CommandRunner(ssh)
                for cmd in self.project.pre_deploy_commands:
                    # 自动切换到项目目录执行命令
                    full_cmd = f"cd {self.project.remote_path} && {cmd}"
                    _log(f"前置命令: {cmd}")
                    output = cmd_runner.run_checked(full_cmd)
                    if output.strip():
                        _log(f"命令输出:\n{output}")

            # 4. 上传 + 删除
            engine = SyncEngine(self.project, ssh)
            for d in selected_diffs:
                if not d.selected:
                    rec.files_skipped += 1
                    continue
                if d.status in (DiffStatus.NEW, DiffStatus.MODIFIED):
                    _log(f"上传 {d.relative_path}")
                    n = engine.upload_file(d.relative_path)
                    rec.files_uploaded += 1
                    rec.bytes_transferred += n
                    if progress_cb:
                        progress_cb()
                elif d.status == DiffStatus.DELETED:
                    _log(f"删除 {d.relative_path}")
                    engine.delete_remote(d.relative_path)
                    rec.files_deleted += 1

            # 5. 后置命令
            if self.project.enable_post_commands:
                cmd_runner = CommandRunner(ssh)
                for cmd in self.project.post_deploy_commands:
                    # 自动切换到项目目录执行命令
                    full_cmd = f"cd {self.project.remote_path} && {cmd}"
                    _log(f"后置命令: {cmd}")
                    output = cmd_runner.run_checked(full_cmd)
                    if output.strip():
                        _log(f"命令输出:\n{output}")

            rec.status = "success"
        except SafetyError as e:
            rec.status = "failed"
            rec.error = f"安全拦截: {e}"
            result.error = e
        except Exception as e:
            rec.status = "failed"
            rec.error = str(e)
            result.error = e
        finally:
            rec.finished_at = time.strftime("%Y-%m-%d %H:%M:%S")
            self.store.add_deploy_record(rec)

        return result
