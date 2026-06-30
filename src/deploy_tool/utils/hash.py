"""文件哈希工具"""
import hashlib


def file_sha256(filepath: str, chunk_size: int = 65536) -> str:
    """计算文件的 SHA256"""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()
