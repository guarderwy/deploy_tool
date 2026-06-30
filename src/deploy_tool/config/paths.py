"""应用数据路径"""
import os


def app_data_dir() -> str:
    """返回配置数据目录 %APPDATA%/deploy_tool"""
    appdata = os.getenv("APPDATA", os.path.expanduser("~"))
    return os.path.join(appdata, "deploy_tool")


def logs_dir() -> str:
    """返回日志目录"""
    p = os.path.join(app_data_dir(), "logs")
    os.makedirs(p, exist_ok=True)
    return p
