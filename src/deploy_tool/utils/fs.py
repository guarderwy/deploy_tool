"""本地文件系统辅助"""
import os
import shutil
from typing import Callable


def count_files(directory: str, exclude_fn: Callable = None) -> int:
    """统计目录下文件数量（可选排除）"""
    count = 0
    for dirpath, dirs, files in os.walk(directory):
        if exclude_fn:
            files = [f for f in files if not exclude_fn(os.path.join(dirpath, f))]
        count += len(files)
    return count


def total_size(directory: str) -> int:
    """计算目录总大小（字节）"""
    total = 0
    for dirpath, dirs, files in os.walk(directory):
        for f in files:
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def ensure_dir(path: str):
    """确保目录存在"""
    os.makedirs(path, exist_ok=True)
