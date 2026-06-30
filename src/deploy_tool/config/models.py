"""数据模型 — 全部使用 dataclass"""
from dataclasses import dataclass, field
from typing import Optional, List, Any
from enum import Enum
import uuid
import dataclasses


class AuthMethod(Enum):
    PASSWORD = "password"
    KEY = "key"


class ProxyType(Enum):
    NONE = "none"
    PROXYJUMP = "proxyjump"
    SOCKS5 = "socks5"
    HTTP = "http"


class DiffStatus(Enum):
    NEW = "new"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNCHANGED = "unchanged"


@dataclass
class ProxyConfig:
    type: ProxyType = ProxyType.NONE
    host: str = ""
    port: int = 1080
    username: str = ""
    password: str = ""          # AES 密文 (base64)
    # ProxyJump 专用
    jump_host: str = ""
    jump_port: int = 22
    jump_username: str = ""
    jump_auth_method: AuthMethod = AuthMethod.PASSWORD
    jump_password: str = ""     # AES 密文
    jump_key_path: str = ""


@dataclass
class Server:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    host: str = ""
    port: int = 22
    username: str = "root"
    auth_method: AuthMethod = AuthMethod.PASSWORD
    password: str = ""          # AES 密文
    key_path: str = ""          # 本地私钥路径
    key_passphrase: str = ""    # AES 密文
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    created_at: str = ""
    last_connected: str = ""


@dataclass
class Project:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    server_id: str = ""
    project_type: str = "generic"
    local_path: str = ""
    remote_path: str = ""
    exclude_patterns: List[str] = field(
        default_factory=lambda: [".git/", "node_modules/", "*.pyc", "__pycache__/", "*.log"])
    pre_deploy_commands: List[str] = field(default_factory=list)
    post_deploy_commands: List[str] = field(default_factory=list)
    enable_backup: bool = True
    max_backups: int = 5
    sync_mode: str = "size_mtime"   # "size_mtime" | "hash"
    created_at: str = ""
    # GitHub 集成字段
    github_repo: str = ""            # "owner/repo"
    github_branch: str = "main"
    github_token: str = ""           # AES 密文


@dataclass
class FileDiff:
    relative_path: str
    status: DiffStatus
    local_size: int = 0
    remote_size: int = 0
    local_mtime: float = 0.0
    remote_mtime: float = 0.0
    selected: bool = True


@dataclass
class DeployRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    server_id: str = ""
    started_at: str = ""
    finished_at: str = ""
    status: str = ""
    files_uploaded: int = 0
    files_deleted: int = 0
    files_skipped: int = 0
    bytes_transferred: int = 0
    backup_id: Optional[str] = None
    error: str = ""


@dataclass
class BackupInfo:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    server_id: str = ""
    created_at: str = ""
    remote_tar_path: str = ""
    file_count: int = 0
    size_bytes: int = 0
    deploy_record_id: str = ""


@dataclass
class AppConfig:
    servers: List[Server] = field(default_factory=list)
    projects: List[Project] = field(default_factory=list)
    deploy_records: List[DeployRecord] = field(default_factory=list)
    backups: List[BackupInfo] = field(default_factory=list)
    log_level: str = "INFO"
    max_log_files: int = 30
    theme: str = "auto"
    max_backups_per_project: int = 5

    def to_dict(self) -> dict:
        return _dataclass_to_dict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "AppConfig":
        return _dict_to_dataclass(cls, d)


def _dataclass_to_dict(obj: Any) -> Any:
    """递归序列化 dataclass（含 Enum → value）"""
    if isinstance(obj, Enum):
        return obj.value
    if dataclasses.is_dataclass(obj):
        result = {}
        for f in dataclasses.fields(obj):
            value = getattr(obj, f.name)
            result[f.name] = _dataclass_to_dict(value)
        return result
    if isinstance(obj, list):
        return [_dataclass_to_dict(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    return obj


def _dict_to_dataclass(cls: type, d: dict) -> Any:
    """递归反序列化 dict → dataclass（支持 Enum 自动转换）"""
    if not dataclasses.is_dataclass(cls):
        return d
    field_types = {f.name: f.type for f in dataclasses.fields(cls)}
    kwargs = {}
    for key, value in d.items():
        if key not in field_types:
            continue
        ftype = field_types[key]
        kwargs[key] = _convert_value(ftype, value)
    return cls(**kwargs)


def _convert_value(ftype: type, value: Any) -> Any:
    """根据声明类型转换值"""
    origin = getattr(ftype, "__origin__", None)

    # Optional[X] → Union[X, None]
    if origin is not None:
        args = ftype.__args__
        if type(None) in args:
            non_none = [a for a in args if a is not type(None)][0]
            if value is None:
                return None
            return _convert_value(non_none, value)
        # List[X]
        if origin is list:
            elem_type = args[0] if args else str
            return [_convert_value(elem_type, v) for v in value]

    # Enum
    if isinstance(ftype, type) and issubclass(ftype, Enum):
        return ftype(value)

    # 内嵌 dataclass
    if dataclasses.is_dataclass(ftype):
        return _dict_to_dataclass(ftype, value)

    return value
