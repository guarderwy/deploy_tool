"""安全检查 — 危险命令拦截 + 路径校验"""
import re
from typing import List

# ---- 危险命令正则黑名单 ----
DANGEROUS_PATTERNS = [
    # rm -rf 关键路径
    re.compile(
        r"\brm\s+(-[a-z]*r[a-z]*f?|-[a-z]*f[a-z]*r?)\s+(/\*|~|\$HOME|\.\.|\s*/\s*$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\brm\s+-[a-z]*r[a-z]*f?\s+/(boot|etc|usr|bin|sbin|var|root|home|proc|sys|dev|lib|lib64)(?=$|\s)",
        re.IGNORECASE,
    ),
    # fork bomb
    re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;"),
    # 磁盘破坏
    re.compile(r"\bdd\b.*\bof=/dev/(sd|nvme|hd|vd|disk)", re.IGNORECASE),
    re.compile(r"\bmkfs(\.\w+)?\b", re.IGNORECASE),
    re.compile(r">\s*/dev/sd", re.IGNORECASE),
    # 关机重启
    re.compile(
        r"\b(shutdown|reboot|halt|poweroff|init\s+0)\b", re.IGNORECASE
    ),
    # 权限灾难
    re.compile(r"\bchmod\s+-R\s+[0-7]+\s+/\s*$", re.IGNORECASE),
    re.compile(r"\bchown\s+-R\s+\S+\s+/\s*$", re.IGNORECASE),
    # 防火墙清空
    re.compile(r"\biptables\s+(-F|--flush)\b", re.IGNORECASE),
    # curl/wget | bash
    re.compile(
        r"\b(curl|wget)\b[^|]*\|\s*(bash|sh|zsh)\b", re.IGNORECASE
    ),
]

# 受保护系统路径
PROTECTED_PATHS: set[str] = {
    "/", "/etc", "/usr", "/bin", "/sbin", "/boot", "/var",
    "/root", "/home", "/proc", "/sys", "/dev", "/lib", "/lib64",
}


class SafetyError(Exception):
    """安全检查异常"""
    pass


def check_command(cmd: str) -> List[str]:
    """检查命令是否危险，返回原因列表（空 = 安全）"""
    reasons = []
    for pat in DANGEROUS_PATTERNS:
        if pat.search(cmd):
            reasons.append(f"匹配危险模式: {pat.pattern[:60]}")
    return reasons


def validate_remote_path(path: str, project_root: str) -> None:
    """校验远程路径在项目根目录内且非系统保护路径"""
    if not path or not path.startswith("/"):
        raise SafetyError(f"远程路径必须是绝对路径: {path}")
    # 精确匹配保护路径
    stripped = path.rstrip("/")
    if not stripped or stripped in PROTECTED_PATHS:
        raise SafetyError(f"禁止操作系统保护路径: {path}")
    # 超越项目根目录
    norm = stripped + "/"
    root_norm = project_root.rstrip("/") + "/"
    if not norm.startswith(root_norm):
        raise SafetyError(f"路径 {path} 超出项目根目录 {project_root}")
    # 目录穿越
    parts = path.split("/")
    if ".." in parts:
        raise SafetyError(f"路径包含 .. 穿越: {path}")


def assert_command_safe(cmd: str) -> None:
    """断言命令安全，否则抛 SafetyError"""
    reasons = check_command(cmd)
    if reasons:
        raise SafetyError("命令被安全策略拦截: " + "; ".join(reasons))
