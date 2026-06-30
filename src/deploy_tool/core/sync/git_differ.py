"""Git 差异对比引擎 — 通过 GitHub API 对比本地与仓库文件"""
import os
import json
import hashlib
import urllib.request
import urllib.error
import base64
from typing import List, Dict, Any, Optional

from ...config.models import Project, FileDiff, DiffStatus
from ...utils.hash import file_sha256
from .filters import ExcludeFilter


class GitDiffer:
    """通过 GitHub API 对比本地文件与远程仓库差异"""

    def __init__(self, project: Project, decrypt_fn=None):
        self.project = project
        self._decrypt = decrypt_fn
        self.filter = ExcludeFilter(project.exclude_patterns)
        self._token = None
        if project.github_token and decrypt_fn:
            self._token = decrypt_fn(project.github_token)

    def _api_get(self, url: str) -> Optional[dict]:
        """调用 GitHub API"""
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github.v3+json")
        if self._token:
            req.add_header("Authorization", f"token {self._token}")
        req.add_header("User-Agent", "deploy-tool/1.0")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
        except urllib.error.URLError as e:
            raise ConnectionError(f"GitHub API 连接失败: {e.reason}")

    def compute(self, progress_cb=None) -> List[FileDiff]:
        """对比本地与 GitHub 仓库的文件差异"""
        if progress_cb:
            progress_cb(0, 100)

        repo = self.project.github_repo
        branch = self.project.github_branch
        if not repo:
            raise ValueError("未配置 GitHub 仓库地址")

        # 1. 获取 GitHub 文件树
        tree_url = f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
        data = self._api_get(tree_url)
        if data is None:
            raise ValueError(f"仓库 {repo} 或分支 {branch} 不存在")

        if progress_cb:
            progress_cb(30, 100)

        # 构建远程文件字典 {path: {sha, size}}
        remote_files: Dict[str, dict] = {}
        for item in data.get("tree", []):
            if item["type"] == "blob":  # 只处理文件
                rel = item["path"]
                if self.filter.is_excluded(rel):
                    continue
                remote_files[rel] = {
                    "sha": item["sha"],
                    "size": item.get("size", 0),
                }

        if progress_cb:
            progress_cb(50, 100)

        # 2. 扫描本地文件
        local_files = self._scan_local()

        if progress_cb:
            progress_cb(70, 100)

        # 3. 逐文件对比
        diffs: List[FileDiff] = []
        all_paths = set(local_files.keys()) | set(remote_files.keys())
        total = len(all_paths)

        for i, rel in enumerate(sorted(all_paths)):
            lf = local_files.get(rel)
            rf = remote_files.get(rel)

            if lf and not rf:
                diffs.append(FileDiff(
                    rel, DiffStatus.NEW,
                    local_size=lf["size"], local_mtime=lf["mtime"],
                ))
            elif rf and not lf:
                diffs.append(FileDiff(
                    rel, DiffStatus.DELETED,
                    remote_size=rf["size"],
                ))
            elif lf and rf:
                if lf["size"] != rf["size"]:
                    diffs.append(FileDiff(
                        rel, DiffStatus.MODIFIED,
                        local_size=lf["size"], remote_size=rf["size"],
                        local_mtime=lf["mtime"],
                    ))
                else:
                    # 大小相同 — 计算本地 git blob SHA1 与 GitHub 的 SHA 对比
                    local_git_sha = self._local_git_blob_sha(lf["os_path"])
                    if local_git_sha != rf["sha"]:
                        diffs.append(FileDiff(
                            rel, DiffStatus.MODIFIED,
                            local_size=lf["size"], remote_size=rf["size"],
                            local_mtime=lf["mtime"],
                        ))

            if progress_cb and total > 0:
                progress_cb(70 + int(30 * (i + 1) / total), 100)

        diffs.sort(key=lambda d: d.relative_path)
        if progress_cb:
            progress_cb(100, 100)
        return diffs

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

    @staticmethod
    def _local_git_blob_sha(filepath: str) -> str:
        """计算本地文件的 Git blob SHA1 (sha1('blob ' + size + '\\0' + content))"""
        with open(filepath, "rb") as f:
            content = f.read()
        blob_header = f"blob {len(content)}\0".encode()
        return hashlib.sha1(blob_header + content).hexdigest()

    def get_file_content(self, path: str) -> Optional[str]:
        """从 GitHub 获取单个文件内容（供部署用时下载）"""
        repo = self.project.github_repo
        branch = self.project.github_branch
        url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
        data = self._api_get(url)
        if data and "content" in data:
            return base64.b64decode(data["content"]).decode("utf-8", "replace")
        return None
