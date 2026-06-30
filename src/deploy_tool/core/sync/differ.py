"""文件差异对比引擎"""
import os
import shlex
import stat as _stat
import subprocess
from typing import List, Dict, Any

from ...config.models import Project, FileDiff, DiffStatus
from ...utils.hash import file_sha256
from ..ssh.client import SSHClient
from .filters import ExcludeFilter


class Differ:
    """对比本地与远程文件差异"""

    def __init__(self, project: Project, ssh: SSHClient = None):
        self.project = project
        self.ssh = ssh
        self.filter = ExcludeFilter(project.exclude_patterns)

    @staticmethod
    def compute_git_diff(project: Project, progress_cb=None) -> List[FileDiff]:
        """通过本地 git diff 对比工作区与 HEAD 的差异，无需 SSH"""
        if progress_cb:
            progress_cb(0, 100)

        root = project.local_path
        if not os.path.isdir(os.path.join(root, ".git")):
            raise ValueError(f"{root} 不是一个 Git 仓库")

        filter_obj = ExcludeFilter(project.exclude_patterns)
        diffs: List[FileDiff] = []
        seen: set = set()

        def _run(args: list) -> str:
            try:
                r = subprocess.run(
                    ["git", "-C", root] + args,
                    capture_output=True, text=True, timeout=30, check=True,
                )
                return r.stdout
            except subprocess.CalledProcessError as e:
                raise ValueError(f"git {' '.join(args)} 失败: {e.stderr.strip() or e}")
            except FileNotFoundError:
                raise ValueError("未找到 git 命令，请确认 Git 已安装")

        # 1) 已跟踪文件的变化（M / D / A 等）
        try:
            tracked_out = _run(["diff", "--name-status", "HEAD"])
        except ValueError:
            tracked_out = ""

        # 2) 未跟踪的新文件（本地新增但尚未 git add）
        try:
            untracked_out = _run(["ls-files", "--others", "--exclude-standard"])
        except ValueError:
            untracked_out = ""

        if progress_cb:
            progress_cb(30, 100)

        # 处理已跟踪文件的变更
        for line in tracked_out.strip().splitlines():
            if not line.strip():
                continue
            parts = line.split("\t", 1)
            if len(parts) != 2:
                continue
            status_code, rel = parts
            rel = rel.strip()
            if not rel or filter_obj.is_excluded(rel):
                continue

            full_path = os.path.join(root, rel.replace("/", os.sep))

            if status_code == "D":
                try:
                    r = subprocess.run(
                        ["git", "-C", root, "show", f"HEAD:{rel}"],
                        capture_output=True, timeout=10,
                    )
                    remote_size = len(r.stdout)
                except Exception:
                    remote_size = 0
                diffs.append(FileDiff(
                    rel, DiffStatus.DELETED,
                    remote_size=remote_size,
                ))
            elif status_code == "A":
                size = os.path.getsize(full_path) if os.path.isfile(full_path) else 0
                diffs.append(FileDiff(
                    rel, DiffStatus.NEW,
                    local_size=size,
                ))
            else:
                local_size = os.path.getsize(full_path) if os.path.isfile(full_path) else 0
                try:
                    r = subprocess.run(
                        ["git", "-C", root, "show", f"HEAD:{rel}"],
                        capture_output=True, timeout=10,
                    )
                    remote_size = len(r.stdout)
                except Exception:
                    remote_size = 0
                diffs.append(FileDiff(
                    rel, DiffStatus.MODIFIED,
                    local_size=local_size, remote_size=remote_size,
                ))
            seen.add(rel)

        # 处理未跟踪的新文件
        for rel in untracked_out.strip().splitlines():
            rel = rel.strip().replace("\\", "/")
            if not rel or rel in seen or filter_obj.is_excluded(rel):
                continue
            full_path = os.path.join(root, rel.replace("/", os.sep))
            size = os.path.getsize(full_path) if os.path.isfile(full_path) else 0
            diffs.append(FileDiff(
                rel, DiffStatus.NEW,
                local_size=size,
            ))
            seen.add(rel)

        if progress_cb:
            progress_cb(100, 100)
        return diffs

    def compute(self, use_hash: bool = False, progress_cb=None) -> List[FileDiff]:
        """计算文件差异列表
        
        progress_cb: 可选的回调 progress_cb(current, total)，total=100 表示百分比
        """
        if progress_cb:
            progress_cb(0, 100)

        local = self._scan_local()
        if progress_cb:
            progress_cb(20, 100)

        remote = self._scan_remote()
        if progress_cb:
            progress_cb(55, 100)

        diffs: List[FileDiff] = []
        all_paths = set(local.keys()) | set(remote.keys())

        # 收集需要 hash 对比的路径（大小相同）
        hash_paths = []
        if use_hash:
            for rel in all_paths:
                l = local.get(rel)
                r = remote.get(rel)
                if l and r and l["size"] == r["size"]:
                    hash_paths.append(rel)

        # 批量计算远程 hash（一次性 SSH exec），仅在 hash 模式下
        remote_hashes = {}
        if use_hash and hash_paths:
            remote_hashes = self._batch_remote_hashes(hash_paths)

        total = len(all_paths)
        for i, rel in enumerate(sorted(all_paths)):
            l = local.get(rel)
            r = remote.get(rel)
            if l and not r:
                diffs.append(FileDiff(
                    rel, DiffStatus.NEW,
                    local_size=l["size"], local_mtime=l["mtime"],
                ))
            elif r and not l:
                diffs.append(FileDiff(
                    rel, DiffStatus.DELETED,
                    remote_size=r["size"], remote_mtime=r["mtime"],
                ))
            elif self._changed(l, r, use_hash, remote_hashes.get(rel)):
                diffs.append(FileDiff(
                    rel, DiffStatus.MODIFIED,
                    local_size=l["size"], remote_size=r["size"],
                    local_mtime=l["mtime"], remote_mtime=r["mtime"],
                ))
            if progress_cb and total > 0:
                progress_cb(55 + int(45 * (i + 1) / total), 100)

        # 按路径排序
        diffs.sort(key=lambda d: d.relative_path)
        if progress_cb:
            progress_cb(100, 100)
        return diffs

    def _changed(self, l: dict, r: dict, use_hash: bool, remote_hash: str = None) -> bool:
        if l["size"] != r["size"]:
            return True
        if use_hash:
            if remote_hash is None:
                return True
            return self._local_hash(l["os_path"]) != remote_hash
        # 快速模式：大小相同即视为未修改（SFTP 不保留 mtime，远程 mtime 无参考价值）
        return False

    def _batch_remote_hashes(self, rel_paths: list) -> dict:
        """批量远程计算 hash，返回 {rel: hash} 字典"""
        # 按批次构建 sha256sum 命令，每批不超过 500 个文件防止命令过长
        remote_hashes = {}
        root = self.project.remote_path
        batch_size = 500
        for start in range(0, len(rel_paths), batch_size):
            batch = rel_paths[start:start + batch_size]
            cmd_parts = ["sha256sum"]
            for rel in batch:
                cmd_parts.append(shlex.quote(f"{root}/{rel}"))
            cmd_parts.append("2>/dev/null")
            cmd = " ".join(cmd_parts)
            code, out, err = self.ssh.exec(cmd, timeout=300)
            if code == 0 and out:
                for line in out.splitlines():
                    parts = line.strip().split(None, 1)
                    if len(parts) == 2:
                        h = parts[0]
                        filepath = parts[1].lstrip("*")  # sha256sum may print * as binary marker
                        # 从 filepath 反推出 rel
                        for rel in batch:
                            if filepath.endswith(rel):
                                remote_hashes[rel] = h
                                break
            else:
                # sha256sum 不可用，fallback 到每个文件单独取
                for rel in batch:
                    h = self._remote_hash(f"{root}/{rel}")
                    if h:
                        remote_hashes[rel] = h
        return remote_hashes

    def _scan_local(self) -> Dict[str, Dict[str, Any]]:
        """扫描本地目录"""
        result: Dict[str, Dict[str, Any]] = {}
        root = self.project.local_path
        if not os.path.isdir(root):
            return result
        for dirpath, dirs, files in os.walk(root):
            for fn in files:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, root).replace("\\", "/")
                if self.filter.is_excluded(rel):
                    continue
                try:
                    st = os.stat(full)
                    result[rel] = {
                        "os_path": full,
                        "size": st.st_size,
                        "mtime": st.st_mtime,
                    }
                except OSError:
                    continue
        return result

    def _scan_remote(self) -> Dict[str, Dict[str, Any]]:
        """扫描远程目录"""
        result: Dict[str, Dict[str, Any]] = {}
        sftp = self.ssh.sftp()
        root = self.project.remote_path
        try:
            sftp.stat(root)
        except IOError:
            return result
        for entry in self._walk_remote(sftp, root, ""):
            result[entry["rel"]] = entry
        return result

    def _walk_remote(self, sftp, base: str, rel_prefix: str):
        """递归遍历远程目录"""
        for attr in sftp.listdir_attr(base):
            rel = (
                f"{rel_prefix}{attr.filename}"
                if not rel_prefix
                else f"{rel_prefix}/{attr.filename}"
            )
            full = f"{base}/{attr.filename}"
            if _stat.S_ISDIR(attr.st_mode):
                yield from self._walk_remote(sftp, full, rel)
            else:
                if self.filter.is_excluded(rel):
                    continue
                yield {
                    "rel": rel,
                    "remote_path": full,
                    "size": attr.st_size,
                    "mtime": float(attr.st_mtime) if attr.st_mtime else 0,
                }

    def _local_hash(self, path: str) -> str:
        return file_sha256(path)

    def _remote_hash(self, path: str) -> str:
        """用远程 sha256sum 计算哈希，路径用 shlex.quote 防止特殊字符问题"""
        quoted = shlex.quote(path)
        code, out, err = self.ssh.exec(f"sha256sum {quoted} 2>/dev/null", timeout=60)
        if code == 0 and out:
            return out.split()[0]
        # fallback: 若 sha256sum 不可用，尝试 md5sum
        code, out, err = self.ssh.exec(f"md5sum {quoted} 2>/dev/null", timeout=60)
        if code == 0 and out:
            return out.split()[0]
        return ""
