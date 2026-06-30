"""配置存储 — DPAPI 保护主密钥，AES-GCM 加密配置"""
import os
import json

from .paths import app_data_dir
from .crypto import (
    generate_aes_key, dpapi_protect, dpapi_unprotect,
    encrypt_json, decrypt_json, encrypt_str, decrypt_str,
)
from .models import AppConfig

CONFIG_FILE = "config.enc"
MASTER_KEY_FILE = "master.key.enc"


class ConfigStore:
    """配置存储管理器"""

    def __init__(self):
        self.data_dir = app_data_dir()
        self.config_path = os.path.join(self.data_dir, CONFIG_FILE)
        self.key_path = os.path.join(self.data_dir, MASTER_KEY_FILE)
        self._key: bytes | None = None
        self.config: AppConfig = AppConfig()

    # ---- 初始化 / 加载 ----

    def is_initialized(self) -> bool:
        return os.path.exists(self.key_path)

    def init_first_run(self):
        """首次启动：生成 AES 密钥，DPAPI 加密存储"""
        os.makedirs(self.data_dir, exist_ok=True)
        self._key = generate_aes_key()
        blob = dpapi_protect(self._key)
        with open(self.key_path, "wb") as f:
            f.write(blob)
        self.save()

    def load(self) -> bool:
        """启动时加载配置"""
        if not os.path.exists(self.key_path):
            return False
        with open(self.key_path, "rb") as f:
            blob = f.read()
        self._key = dpapi_unprotect(blob)
        if os.path.exists(self.config_path):
            with open(self.config_path, "rb") as f:
                data = decrypt_json(f.read(), self._key)
            self.config = AppConfig.from_dict(data)
        return True

    def save(self):
        """保存配置到磁盘"""
        if self._key is None:
            raise RuntimeError("配置未初始化，无法保存")
        os.makedirs(self.data_dir, exist_ok=True)
        blob = encrypt_json(self.config.to_dict(), self._key)
        with open(self.config_path, "wb") as f:
            f.write(blob)

    # ---- 凭据加解密 ----

    def encrypt_credential(self, text: str) -> str:
        if self._key is None:
            raise RuntimeError("密钥未加载")
        return encrypt_str(text, self._key)

    def decrypt_credential(self, token: str) -> str:
        if self._key is None:
            raise RuntimeError("密钥未加载")
        return decrypt_str(token, self._key)

    # ---- 查找 ----

    def find_server(self, server_id: str):
        for s in self.config.servers:
            if s.id == server_id:
                return s
        return None

    def find_project(self, project_id: str):
        for p in self.config.projects:
            if p.id == project_id:
                return p
        return None

    def get_projects_for_server(self, server_id: str) -> list:
        return [p for p in self.config.projects if p.server_id == server_id]

    def get_backups_for_project(self, project_id: str) -> list:
        return [b for b in self.config.backups if b.project_id == project_id]

    # ---- 增删 ----

    def add_server(self, server) -> str:
        self.config.servers.append(server)
        self.save()
        return server.id

    def remove_server(self, server_id: str):
        self.config.servers = [s for s in self.config.servers if s.id != server_id]
        # 同时删除关联项目
        self.config.projects = [p for p in self.config.projects if p.server_id != server_id]
        self.save()

    def add_project(self, project) -> str:
        self.config.projects.append(project)
        self.save()
        return project.id

    def update_server(self, server) -> None:
        for i, s in enumerate(self.config.servers):
            if s.id == server.id:
                self.config.servers[i] = server
                self.save()
                return

    def update_project(self, project) -> None:
        for i, p in enumerate(self.config.projects):
            if p.id == project.id:
                self.config.projects[i] = project
                self.save()
                return

    def remove_project(self, project_id: str):
        self.config.projects = [p for p in self.config.projects if p.id != project_id]
        self.save()

    def add_backup(self, backup_info):
        self.config.backups.append(backup_info)
        self.save()

    def add_deploy_record(self, record):
        self.config.deploy_records.append(record)
        self.save()
