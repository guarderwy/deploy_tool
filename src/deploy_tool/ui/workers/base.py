"""Worker 基类 + 所有后台任务线程"""
from PyQt5 import QtCore

from ...config.store import ConfigStore
from ...core.ssh.pool import ConnectionPool
from ...core.sync.differ import Differ
from ...core.sync.git_differ import GitDiffer
from ...core.deployer import Deployer
from ...core.backup import BackupManager
from ...core.safety import validate_remote_path
from ...config.models import Project, FileDiff, BackupInfo


class BaseWorker(QtCore.QThread):
    """Worker 基类"""
    log = QtCore.pyqtSignal(str)
    progress = QtCore.pyqtSignal(int, int)  # current, total
    finished_ok = QtCore.pyqtSignal(object)  # result
    failed = QtCore.pyqtSignal(str)

    def __init__(self, store: ConfigStore, pool: ConnectionPool):
        super().__init__()
        self.store = store
        self.pool = pool


class TestConnectionWorker(BaseWorker):
    """测试服务器连接"""

    def __init__(self, store, pool, server_id: str):
        super().__init__(store, pool)
        self.server_id = server_id

    def run(self):
        try:
            self.log.emit(f"正在连接...")
            ssh = self.pool.get(self.server_id)
            code, out, err = ssh.exec("echo 'OK' && uname -a")
            self.log.emit(f"连接成功: {out.strip()}")
            self.finished_ok.emit(out.strip())
        except Exception as e:
            self.failed.emit(str(e))


class DiffWorker(BaseWorker):
    """计算文件差异"""

    def __init__(self, store, pool, project: Project):
        super().__init__(store, pool)
        self.project = project

    def run(self):
        try:
            use_hash = self.project.sync_mode == "hash"

            if self.project.project_type == "git":
                self.log.emit("正在从 GitHub 获取文件列表...")
                differ = GitDiffer(self.project, self.store.decrypt_credential)

                def on_progress(current, total):
                    self.progress.emit(current, total)

                self.log.emit("正在对比本地与 GitHub 仓库差异...")
                diffs = differ.compute(progress_cb=on_progress)
                self.log.emit(f"差异分析完成，共 {len(diffs)} 个文件有变化")
                self.finished_ok.emit(diffs)
                return

            # Git 版本对比 — 通过本地 git diff，无需 SSH
            if self.project.sync_mode == "git_diff":
                self.log.emit("正在执行本地 Git 差异分析...")
                diffs = Differ.compute_git_diff(self.project, progress_cb=lambda c, t: self.progress.emit(c, t))
                self.log.emit(f"Git 差异分析完成，共 {len(diffs)} 个文件有变化")
                self.finished_ok.emit(diffs)
                return

            self.log.emit("正在连接服务器...")
            ssh = self.pool.get(self.project.server_id)
            self.log.emit("正在扫描本地文件...")
            differ = Differ(self.project, ssh)
            self.log.emit("正在对比文件差异..." + ("(SHA256 严格模式)" if use_hash else ""))

            def on_progress(current, total):
                self.progress.emit(current, total)

            diffs = differ.compute(use_hash=use_hash, progress_cb=on_progress)
            self.log.emit(f"差异分析完成，共 {len(diffs)} 个文件有变化")
            self.finished_ok.emit(diffs)
        except Exception as e:
            self.failed.emit(str(e))


class DeployWorker(BaseWorker):
    """执行部署"""

    def __init__(self, store, pool, project: Project, selected_diffs: list[FileDiff]):
        super().__init__(store, pool)
        self.project = project
        self.selected = selected_diffs

    def run(self):
        try:
            deployer = Deployer(self.project, self.pool, self.store)
            total = len([d for d in self.selected if d.selected])

            def prog():
                nonlocal done
                done[0] += 1
                self.progress.emit(done[0], total)

            done = [0]

            def log(msg: str):
                self.log.emit(msg)

            result = deployer.deploy(self.selected, prog, log)
            if result.error:
                self.failed.emit(f"{result.record.error}")
            else:
                self.log.emit(
                    f"部署完成! 上传 {result.record.files_uploaded} 个文件, "
                    f"共 {result.record.bytes_transferred:,} 字节"
                )
                self.finished_ok.emit(result)
        except Exception as e:
            self.failed.emit(str(e))


class RollbackWorker(BaseWorker):
    """执行回滚"""

    def __init__(self, store, pool, project: Project, backup: BackupInfo):
        super().__init__(store, pool)
        self.project = project
        self.backup = backup

    def run(self):
        try:
            self.log.emit("正在连接服务器...")
            ssh = self.pool.get(self.project.server_id)
            # 回滚前安全校验
            validate_remote_path(self.project.remote_path, self.project.remote_path)
            self.log.emit("正在执行回滚...")
            bm = BackupManager(self.project, ssh, self.store)
            bm.rollback(self.backup)
            self.log.emit("回滚完成!")
            self.finished_ok.emit(None)
        except Exception as e:
            self.failed.emit(str(e))
