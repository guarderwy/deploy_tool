"""项目类型预设配置"""
from .models import Project

PROJECT_PRESETS = {
    "html": {
        "label": "HTML / 静态页面",
        "exclude_patterns": [".git/", "*.md", ".DS_Store", "Thumbs.db"],
        "pre_deploy_commands": [],
        "post_deploy_commands": [],
        "description": "纯静态 HTML/CSS/JS 文件，直接上传",
    },
    "vue": {
        "label": "Vue 前端 (打包后)",
        "exclude_patterns": [
            ".git/", "node_modules/", "src/", "*.md",
            ".env*", "babel.config.*", "vue.config.*",
            "package*.json", "tsconfig.json",
        ],
        "pre_deploy_commands": [],
        "post_deploy_commands": [],
        "description": "上传 npm run build 产出的 dist/ 目录内容",
        "local_path_hint": "选择 dist/ 目录",
    },
    "php": {
        "label": "PHP 项目",
        "exclude_patterns": [
            ".git/", "node_modules/", ".env", "vendor/",
            "*.log", ".idea/", ".vscode/",
        ],
        "pre_deploy_commands": [],
        "post_deploy_commands": [
            "chown -R www-data:www-data {remote_path} 2>/dev/null || true",
        ],
        "description": "上传 PHP 源码，可选自动修复权限",
    },
    "go": {
        "label": "Go 项目 (编译后)",
        "exclude_patterns": [
            ".git/", "*.go", "go.mod", "go.sum", "vendor/",
            "Makefile", "*.md", ".env*",
        ],
        "pre_deploy_commands": [],
        "post_deploy_commands": [
            "systemctl restart {service_name} 2>/dev/null || pm2 restart {service_name} 2>/dev/null || true",
        ],
        "description": "上传编译后的二进制文件，可选重启服务",
    },
    "node": {
        "label": "Node.js 项目",
        "exclude_patterns": [
            ".git/", "node_modules/", "src/", "test/",
            "*.md", ".env*", "tsconfig.json", "package*.json",
        ],
        "pre_deploy_commands": [],
        "post_deploy_commands": [
            "cd {remote_path} && npm install --production 2>/dev/null || true",
            "pm2 restart {service_name} 2>/dev/null || systemctl restart {service_name} 2>/dev/null || true",
        ],
        "description": "上传项目文件，可选远程安装依赖并重启服务",
    },
    "generic": {
        "label": "通用项目",
        "exclude_patterns": [
            ".git/", "node_modules/", "*.pyc", "__pycache__/", "*.log",
        ],
        "pre_deploy_commands": [],
        "post_deploy_commands": [],
        "description": "通用配置，无特殊预设",
    },
    "git": {
        "label": "Git 版本 (GitHub)",
        "exclude_patterns": [
            ".git/", "node_modules/", "*.pyc", "__pycache__/", "*.log",
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
        project_type = "generic"
    preset = PROJECT_PRESETS[project_type]
    project.project_type = project_type
    # 仅在排除规则为默认值时覆盖
    default = Project().exclude_patterns
    if not project.exclude_patterns or project.exclude_patterns == default:
        project.exclude_patterns = list(preset.get("exclude_patterns", default))
    if not project.pre_deploy_commands:
        project.pre_deploy_commands = list(preset.get("pre_deploy_commands", []))
    if not project.post_deploy_commands:
        project.post_deploy_commands = list(preset.get("post_deploy_commands", []))
    return project


def get_preset_list() -> list:
    """返回预设类型列表 [{id, label, description}, ...]"""
    return [
        {
            "id": key,
            "label": val["label"],
            "description": val["description"],
        }
        for key, val in PROJECT_PRESETS.items()
    ]
