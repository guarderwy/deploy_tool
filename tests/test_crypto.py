"""加密模块测试"""
import unittest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deploy_tool.config.crypto import (
    generate_aes_key,
    dpapi_protect,
    dpapi_unprotect,
    encrypt_bytes,
    decrypt_bytes,
    encrypt_str,
    decrypt_str,
    encrypt_json,
    decrypt_json,
)


class TestCrypto(unittest.TestCase):

    def test_key_generation(self):
        key = generate_aes_key()
        self.assertEqual(len(key), 32)

    def test_dpapi_roundtrip(self):
        data = b"hello dpapi test data 123456"
        blob = dpapi_protect(data)
        result = dpapi_unprotect(blob)
        self.assertEqual(data, result)

    def test_aes_gcm_roundtrip(self):
        key = generate_aes_key()
        data = b"secret message" * 10
        encrypted = encrypt_bytes(data, key)
        decrypted = decrypt_bytes(encrypted, key)
        self.assertEqual(data, decrypted)

    def test_aes_gcm_tamper_detection(self):
        key = generate_aes_key()
        data = b"tamper test"
        encrypted = encrypt_bytes(data, key)
        # 修改密文
        tampered = bytearray(encrypted)
        tampered[15] ^= 0x01
        with self.assertRaises(Exception):
            decrypt_bytes(bytes(tampered), key)

    def test_str_encryption(self):
        key = generate_aes_key()
        text = "my_password_123"
        token = encrypt_str(text, key)
        self.assertNotEqual(token, text)
        self.assertEqual(decrypt_str(token, key), text)

    def test_empty_str(self):
        key = generate_aes_key()
        self.assertEqual(encrypt_str("", key), "")
        self.assertEqual(decrypt_str("", key), "")

    def test_json_encryption(self):
        key = generate_aes_key()
        data = {"servers": [{"name": "prod", "host": "1.2.3.4"}], "count": 42}
        blob = encrypt_json(data, key)
        result = decrypt_json(blob, key)
        self.assertEqual(data, result)


if __name__ == "__main__":
    unittest.main()
