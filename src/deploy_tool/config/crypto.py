"""Windows DPAPI + AES-GCM 加密模块"""
import os
import base64
import json

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import win32crypt


def generate_aes_key() -> bytes:
    """生成随机 32 字节 AES-256 密钥"""
    return os.urandom(32)


def dpapi_protect(plaintext: bytes) -> bytes:
    """用 Windows DPAPI 加密（绑定当前用户账户）"""
    blob = win32crypt.CryptProtectData(plaintext, None, None, None, None, 0)
    return blob


def dpapi_unprotect(ciphertext: bytes) -> bytes:
    """用 Windows DPAPI 解密（仅当前用户账户可解）"""
    _, plaintext = win32crypt.CryptUnprotectData(ciphertext, None, None, None, 0)
    return plaintext


def encrypt_bytes(plaintext: bytes, key: bytes) -> bytes:
    """AES-GCM，返回 nonce(12B) + 密文+tag"""
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext, None)
    return nonce + ct


def decrypt_bytes(blob: bytes, key: bytes) -> bytes:
    nonce, ct = blob[:12], blob[12:]
    return AESGCM(key).decrypt(nonce, ct, None)


def encrypt_str(text: str, key: bytes) -> str:
    """加密字符串（如密码），返回 base64"""
    if not text:
        return ""
    return base64.b64encode(encrypt_bytes(text.encode("utf-8"), key)).decode()


def decrypt_str(token: str, key: bytes) -> str:
    """解密字符串"""
    if not token:
        return ""
    return decrypt_bytes(base64.b64decode(token), key).decode("utf-8")


def encrypt_json(obj: dict, key: bytes) -> bytes:
    """加密整个配置 JSON"""
    return encrypt_bytes(json.dumps(obj, ensure_ascii=False).encode("utf-8"), key)


def decrypt_json(blob: bytes, key: bytes) -> dict:
    return json.loads(decrypt_bytes(blob, key).decode("utf-8"))
