"""ASCII 独立分组与 CBC；JSON 密文包携带 IV、模式和补零前的长度。"""

import json
import re
import secrets
from dataclasses import dataclass

from .core import decrypt_block, encrypt_block, validate_uint
from .encoding import ascii_to_blocks, blocks_to_bytes

PROFILE = "S-AES-AppendixD-v1"


def generate_iv() -> int:
    return secrets.randbits(16)


def cbc_encrypt(blocks: list[int], key: int, iv: int) -> list[int]:
    validate_uint(key, 16, "密钥")
    validate_uint(iv, 16, "IV")
    result = []
    previous = iv
    for block in blocks:
        validate_uint(block, 16, "明文分组")
        previous = encrypt_block(block ^ previous, key)
        result.append(previous)
    return result


def cbc_decrypt(blocks: list[int], key: int, iv: int) -> list[int]:
    validate_uint(key, 16, "密钥")
    validate_uint(iv, 16, "IV")
    result = []
    previous = iv
    for block in blocks:
        validate_uint(block, 16, "密文分组")
        result.append(decrypt_block(block, key) ^ previous)
        previous = block
    return result


@dataclass(frozen=True)
class CipherPacket:
    mode: str
    blocks: tuple[int, ...]
    original_length: int
    iv: int | None = None

    def __post_init__(self):
        if self.mode not in ("ECB", "CBC"):
            raise ValueError("只支持 ECB 或 CBC 模式")
        if type(self.original_length) is not int or self.original_length < 0:
            raise ValueError("原始字节数必须为非负整数")
        if (self.original_length + 1) // 2 != len(self.blocks):
            raise ValueError("原始字节数与分组数量不匹配")
        for block in self.blocks:
            validate_uint(block, 16, "密文分组")
        if self.mode == "CBC":
            validate_uint(self.iv, 16, "IV")
        elif self.iv is not None:
            raise ValueError("ECB 密文包不使用 IV")

    def to_json(self) -> str:
        return json.dumps({
            "version": 1, "profile": PROFILE, "mode": self.mode,
            "encoding": "ascii", "padding": "zero-with-length",
            "original_length": self.original_length,
            "iv": f"{self.iv:04X}" if self.iv is not None else None,
            "blocks": [f"{b:04X}" for b in self.blocks],
        }, indent=2)

    @classmethod
    def from_json(cls, text: str) -> "CipherPacket":
        try:
            data = json.loads(text)
        except (ValueError, TypeError) as exc:
            raise ValueError("密文包必须是有效 JSON") from exc
        if not isinstance(data, dict):
            raise ValueError("JSON 密文包应为对象")
        if (type(data.get("version")) is not int or data["version"] != 1
                or data.get("profile") != PROFILE or data.get("encoding") != "ascii"
                or data.get("padding") != "zero-with-length"):
            raise ValueError("密文包版本、算法参数或编码不匹配")
        raw_blocks = data.get("blocks")
        if not isinstance(raw_blocks, list) or not all(
                isinstance(b, str) and re.fullmatch(r"[0-9a-fA-F]{4}", b) for b in raw_blocks):
            raise ValueError("blocks 必须是 4 位十六进制字符串数组")
        raw_iv = data.get("iv")
        if raw_iv is not None and not (isinstance(raw_iv, str) and re.fullmatch(r"[0-9a-fA-F]{4}", raw_iv)):
            raise ValueError("IV 必须是 4 位十六进制字符串")
        return cls(data.get("mode"), tuple(int(b, 16) for b in raw_blocks),
                   data.get("original_length"), int(raw_iv, 16) if raw_iv is not None else None)


def encrypt_ascii(text: str, key: int, mode: str = "ECB", iv: int | None = None) -> CipherPacket:
    validate_uint(key, 16, "密钥")
    blocks, length = ascii_to_blocks(text)
    if mode == "CBC":
        iv = generate_iv() if iv is None else iv
        cipher = cbc_encrypt(blocks, key, iv)
    elif mode == "ECB":
        if iv is not None:
            raise ValueError("ECB 不使用 IV")
        cipher = [encrypt_block(b, key) for b in blocks]
    else:
        raise ValueError("只支持 ECB 或 CBC 模式")
    return CipherPacket(mode, tuple(cipher), length, iv)


def decrypt_packet(packet: CipherPacket, key: int) -> bytes:
    """返回原始字节，不用替换字符丢失篡改后的数据；无认证能力。"""
    validate_uint(key, 16, "密钥")
    blocks = (cbc_decrypt(list(packet.blocks), key, packet.iv) if packet.mode == "CBC"
              else [decrypt_block(b, key) for b in packet.blocks])
    return blocks_to_bytes(blocks, packet.original_length)
