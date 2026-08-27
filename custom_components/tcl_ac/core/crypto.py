"""TCL Plus 登录加密工具"""
import base64
import hashlib
import json
import random
import urllib.parse

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

# LoginSDK 1024位 RSA 公钥
PUBLIC_KEY_LOGIN_SDK = (
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDLuCAxtV1Omu216OFdY0p2ypPR"
    "LptloLgMqvpmgkXD/SaB5RPx5oTzo5fdWjeYAx8N6YAe0DDJD5LsmNGhvVIiKOz2"
    "wYI17DQRK6aymvBuxioQzeAd5vI8RItTS7QpNh/ABH/B/3XhhVwnXn40MdDQxA3E"
    "2yfEk327Kqy4TqtscwIDAQAB"
)

_PUBLIC_KEY = serialization.load_der_public_key(base64.b64decode(PUBLIC_KEY_LOGIN_SDK))
_KEY_SIZE = 128  # 1024 bit
_BLOCK_SIZE = _KEY_SIZE - 11  # PKCS1 v1.5: max 117 bytes/block


def md5_hash(text: str) -> str:
    """MD5, 32位小写hex"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def _rsa_encrypt(plaintext: bytes) -> bytes:
    """RSA PKCS1 v1.5 分块加密"""
    result = b''
    offset = 0
    while offset < len(plaintext):
        block = plaintext[offset:offset + _BLOCK_SIZE]
        result += _PUBLIC_KEY.encrypt(block, padding.PKCS1v15())
        offset += _BLOCK_SIZE
    return result


def encrypt_url_params(params: dict) -> str:
    """URL参数逐个RSA加密 -> Base64 -> URL编码"""
    parts = []
    for k, v in params.items():
        encrypted = _rsa_encrypt(str(v).encode('utf-8'))
        b64 = base64.b64encode(encrypted).decode('ascii')
        parts.append(f"{k}={urllib.parse.quote(b64, safe='')}")
    return "&".join(parts)


def encrypt_body(params: dict) -> bytes:
    """请求体JSON整体RSA加密 -> Base64"""
    json_bytes = json.dumps(params, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return base64.b64encode(_rsa_encrypt(json_bytes))


def generate_sign(params: dict) -> str:
    """签名: sorted(keys) -> key=value& -> 追加公钥 -> MD5"""
    sign_str = "&".join(f"{k}={params[k]}" for k in sorted(params.keys()))
    sign_str += PUBLIC_KEY_LOGIN_SDK
    return md5_hash(sign_str)


def generate_nonce() -> str:
    """nonce: '02' + random % 0x98967F"""
    return "02" + str(random.randint(0, 0x98967F))
