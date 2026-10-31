"""多重加密。显式选择位宽，防止 48 bit 密钥前导零引发模式混淆。"""

from .core import decrypt_block, encrypt_block, validate_uint


def split_keys(key: int, bits: int) -> tuple[int, ...]:
    if bits not in (32, 48):
        raise ValueError("多重密钥长度必须为 32 或 48 bit")
    validate_uint(key, bits, "多重密钥")
    return tuple((key >> shift) & 0xFFFF for shift in range(bits - 16, -1, -16))


def double_encrypt(plaintext: int, key: int) -> int:
    k1, k2 = split_keys(key, 32)
    return encrypt_block(encrypt_block(plaintext, k1), k2)


def double_decrypt(ciphertext: int, key: int) -> int:
    k1, k2 = split_keys(key, 32)
    return decrypt_block(decrypt_block(ciphertext, k2), k1)


def triple_encrypt(plaintext: int, key: int, bits: int = 48) -> int:
    keys = split_keys(key, bits)
    k1, k2, k3 = keys if bits == 48 else (keys[0], keys[1], keys[0])
    return encrypt_block(encrypt_block(encrypt_block(plaintext, k1), k2), k3)


def triple_decrypt(ciphertext: int, key: int, bits: int = 48) -> int:
    keys = split_keys(key, bits)
    k1, k2, k3 = keys if bits == 48 else (keys[0], keys[1], keys[0])
    return decrypt_block(decrypt_block(decrypt_block(ciphertext, k3), k2), k1)
