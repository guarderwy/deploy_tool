"""项目类型预设配置

注意：pre_deploy_commands / post_deploy_commands 中的占位符使用
`__XXX__` 双下划线格式（如 `__SERVICE_NAME__`），避免与 shell 语法
（如 `${var}` 或 `{var}`）混淆，并清楚标示"用户必须替换"。
当前版本不会自动替换这些占位符 —— 用户在 UI 中编辑时需替换为实际值。
"""
import logging

from .models import Project, DEFAULT_EXCLUDE_PATTERNS

logger = logging.getLogger(__name__)


# 占位符示例（仅作文档参考，运行时不会自动替换）
#   __SERVICE_NAME__  — systemd / pm2 服务名
#   __REMOTE_PATH__   — 远程部署目录绝对路径
#   __WEB_USER__      — Web 服务器运行用户（如 www-data / nginx / apache）
PLACEHOLDER_HINT = "命令中的 __XXX__ 占位符需手动替换为实际值"


# 通用排除规则：构建缓存、系统/IDE 临时文件
_COMMON_EXCLUDES = [
    ".git/", ".idea/", ".vscode/", ".DS_Store", "Thumbs.db",
    "*.log", "*.tmp", "*.swp", "*.swo",
]
_NODE_EXCLUDES = [
    "node_modules/", ".npm/", ".yarn/", ".pnpm-store/",
    "dist/", "build/", ".next/", ".nuxt/", ".turbo/", ".cache/",
    "coverage/", ".parcel-cache/", ".vite/",
]
_PYTHON_EXCLUDES = [
    "__pycache__/", "*.pyc", "*.pyo", "*.pyd",
    ".venv/", "venv/", "env/", ".env",
    ".pytest_cache/", ".mypy_cache/", ".ruff_cache/",
    "*.egg-info/", "dist/", "build/", ".tox/",
]


PROJECT_PRESETS = {
    "html": {
        "label": "HTML / 静态页面",
        "exclude_patterns": _COMMON_EXCLUDES + ["*.md"],
        "pre_deploy_commands": [],
        "post_deploy_commands": [],
        "description": "纯静态 HTML/CSS/JS 文件，直接上传",
        "local_path_hint": "站点根目录（含 index.html）",
    },
    "vue": {
        "label": "Vue 前端 (打包后)",
        "exclude_patterns": _COMMON_EXCLUDES + _NODE_EXCLUDES + [
            "src/", "*.map", "*.md",
        ],
        "pre_deploy_commands": [],
        "post_deploy_commands": [],
        "description": "上传 npm run build 产出的 dist/ 内容（请在本地先 build）",
        "local_path_hint": "选择 dist/ 目录",
    },
    "php": {
        "label": "PHP 项目",
        "exclude_patterns": _COMMON_EXCLUDES + [
            "vendor/", ".env", "storage/logs/", "storage/framework/cache/",
        ],
        "pre_deploy_commands": [],
        "post_deploy_commands": [
            # 注意：__WEB_USER__ 需替换为实际 Web 用户（www-data / nginx / apache）
            "chown -R __WEB_USER__:__WEB_USER__ {remote_path} 2>/dev/null || true",
        ],
        "description": "上传 PHP 源码，部署后自动修复目录权限（需替换占位符）",
        "local_path_hint": "项目根目录",
    },
    "go": {
        "label": "Go 项目 (编译后)",
        "exclude_patterns": _COMMON_EXCLUDES + [
            "*.go", "go.mod", "go.sum", "vendor/",
            "Makefile", "*.md",
            "*.test", "*.out", "*.prof",
        ],
        "pre_deploy_commands": [],
        "post_deploy_commands": [
            # __SERVICE_NAME__ 需替换为实际服务名
            "systemctl restart __SERVICE_NAME__ 2>/dev/null "
            "|| pm2 restart __SERVICE_NAME__ 2>/dev/null || true",
        ],
        "description": "上传编译后的二进制文件，部署后尝试重启服务（需替换占位符）",
        "local_path_hint": "编译产物目录（含可执行文件）",
    },
    "node": {
        "label": "Node.js 项目",
        "exclude_patterns": _COMMON_EXCLUDES + _NODE_EXCLUDES + [
            "src/", "test/", "tests/", "*.md",
            "tsconfig.json", ".eslintrc*",
        ],
        "pre_deploy_commands": [],
        "post_deploy_commands": [
            "cd {remote_path} && npm install --omit=dev 2>/dev/null || true",
            # __SERVICE_NAME__ 需替换为实际服务名
            "pm2 restart __SERVICE_NAME__ 2>/dev/null "
            "|| systemctl restart __SERVICE_NAME__ 2>/dev/null || true",
        ],
        "description": "上传项目文件，部署后安装生产依赖并尝试重启服务（需替换占位符）",
        "local_path_hint": "项目根目录",
    },
    "python": {
        "label": "Python 项目",
        "exclude_patterns": _COMMON_EXCLUDES + _PYTHON_EXCLUDES + [
            "tests/", ".pytest_cache/", "*.md",
        ],
        "pre_deploy_commands": [],
        "post_deploy_commands": [
            # __SERVICE_NAME__ 需替换为实际服务名
            "systemctl restart __SERVICE_NAME__ 2>/dev/null "
            "|| supervisorctl restart __SERVICE_NAME__ 2>/dev/null || true",
        ],
        "description": "上传 Python 源码，部署后尝试重启服务（需替换占位符）",
        "local_path_hint": "项目根目录",
    },
    "static": {
        "label": "通用静态资源",
        "exclude_patterns": _COMMON_EXCLUDES + [
            "*.map", "*.md", "src/", "tests/",
        ],
        "pre_deploy_commands": [],
        "post_deploy_commands": [],
        "description": "任意静态文件目录，无构建步骤",
        "local_path_hint": "资源根目录",
    },
    "generic": {
        "label": "通用项目",
        "exclude_patterns": list(DEFAULT_EXCLUDE_PATTERNS) + _COMMON_EXCLUDES,
        "pre_deploy_commands": [],
        "post_deploy_commands": [],
        "description": "通用配置，无特殊预设",
    },
    "git": {
        "label": "Git 版本 (GitHub)",
        "exclude_patterns": list(DEFAULT_EXCLUDE_PATTERNS) + [
            ".idea/", ".vscode/", ".DS_Store", "Thumbs.db",
        ],
        "pre_deploy_commands": [],
        "post_deploy_commands": [],
        "description": "与 GitHub 仓库对比差异，支持版本管理",
    },
}


def apply_preset(project: Project, project_type: str) -> Project:
    """将预设应用到项目对象（不覆盖用户已设置的值）"""
    if project_type not in PROJECT_PRESETS:
        logger.warning(
            "未知项目类型 '%s'，回退到 'generic'", project_type
        )
        project_type = "generic"
    preset = PROJECT_PRESETS[project_type]
    project.project_type = project_type

    # 仅在排除规则为默认值时覆盖（避免覆盖用户已自定义的规则）
    if (not project.exclude_patterns
            or project.exclude_patterns == list(DEFAULT_EXCLUDE_PATTERNS)):
        project.exclude_patterns = list(preset.get("exclude_patterns", []))

    if not project.pre_deploy_commands:
        project.pre_deploy_commands = list(preset.get("pre_deploy_commands", []))

    if not project.post_deploy_commands:
        project.post_deploy_commands = list(preset.get("post_deploy_commands", []))

    return project


def get_preset_list() -> list:
    """返回预设类型列表 [{id, label, description, local_path_hint}, ...]"""
    return [
        {
            "id": key,
            "label": val["label"],
            "description": val["description"],
            "local_path_hint": val.get("local_path_hint", ""),
        }
        for key, val in PROJECT_PRESETS.items()
    ]
