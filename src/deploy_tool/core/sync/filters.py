"""排除规则 — gitignore 风格"""
import fnmatch


class ExcludeFilter:
    """gitignore 风格的排除规则：支持目录后缀 /、通配符 *"""

    def __init__(self, patterns: list[str]):
        self.dir_patterns: list[str] = []
        self.file_patterns: list[str] = []
        for p in patterns:
            p = p.strip()
            if not p:
                continue
            if p.endswith("/"):
                self.dir_patterns.append(p[:-1])
            else:
                self.file_patterns.append(p)

    def is_excluded(self, rel_path: str) -> bool:
        """判断相对路径是否被排除"""
        parts = rel_path.split("/")
        # 目录匹配：任一路径段命中目录模式
        for i in range(len(parts) - 1):
            for dp in self.dir_patterns:
                if fnmatch.fnmatch(parts[i], dp):
                    return True
        # 文件/全路径匹配
        fname = parts[-1]
        for fp in self.file_patterns:
            if fnmatch.fnmatch(fname, fp) or fnmatch.fnmatch(rel_path, fp):
                return True
        return False
