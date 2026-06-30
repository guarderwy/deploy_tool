"""QApplication 单例，启动引导"""
import sys

from PyQt5 import QtWidgets

from .config.store import ConfigStore
from .config.paths import logs_dir
from .core.ssh.pool import ConnectionPool
from .ui.theme import apply_theme
from .ui.main_window import MainWindow


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("部署工具")
    app.setOrganizationName("deploy_tool")

    # 配置存储
    store = ConfigStore()
    if not store.is_initialized():
        # 首次启动——初始化 DPAPI + AES 密钥
        store.init_first_run()
    else:
        store.load()

    # 主题
    apply_theme(app, store.config.theme)

    # 日志配置
    from .utils.logger import setup_logger
    setup_logger(store.config.log_level)

    # 连接池
    pool = ConnectionPool(store)

    # 主窗口
    window = MainWindow(store, pool)
    window.show()

    sys.exit(app.exec_())
