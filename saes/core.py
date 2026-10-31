"""附录 D 核心：16 bit 分组、16 bit 密钥、列优先状态、两轮加密。

参数依据用户提供 PDF 的表 D.1、图 D.2 与 D.3 节；第二轮常量为 0x30。
内部用整数保存状态，四个半字节依次为 n0,n1,n2,n3，矩阵为 [n0 n2; n1 n3]。
"""

from dataclasses import dataclass

SBOX = (0x9, 0x4, 0xA, 0xB, 0xD, 0x1, 0x8, 0x5,
        0x6, 0x2, 0x0, 0x3, 0xC, 0xE, 0xF, 0x7)
INV_SBOX = tuple(SBOX.index(value) for value in range(16))
RCON = (0x80, 0x30)
GF_MODULUS = 0x13


def validate_uint(value: int, bits: int, name: str = "数值") -> int:
    if type(value) is not int or not 0 <= value < (1 << bits):
        raise ValueError(f"{name}必须是 0 到 {(1 << bits) - 1} 之间的 {bits} bit 整数")
    return value


def gf_mul(left: int, right: int) -> int:
    """在模 x^4+x+1 的 GF(2^4) 中相乘，例：4*C=5。"""
    validate_uint(left, 4, "乘数")
    validate_uint(right, 4, "乘数")
    product = 0
    while right:
        if right & 1:
            product ^= left
        left <<= 1
        if left & 0x10:
            left ^= GF_MODULUS
        right >>= 1
    return product


_M4 = tuple(gf_mul(4, n) for n in range(16))
_M9 = tuple(gf_mul(9, n) for n in range(16))
_M2 = tuple(gf_mul(2, n) for n in range(16))


def block_to_state(block: int) -> tuple[tuple[int, int], tuple[int, int]]:
    validate_uint(block, 16, "分组")
    return ((block >> 12, (block >> 4) & 15), ((block >> 8) & 15, block & 15))


def _sub(block: int, box: tuple[int, ...]) -> int:
    return (box[block >> 12] << 12 | box[(block >> 8) & 15] << 8
            | box[(block >> 4) & 15] << 4 | box[block & 15])


def sub_nibbles(block: int, inverse: bool = False) -> int:
    validate_uint(block, 16, "状态")
    return _sub(block, INV_SBOX if inverse else SBOX)


def shift_rows(block: int) -> int:
    validate_uint(block, 16, "状态")
    return (block & 0xF0F0) | ((block & 0x0F00) >> 8) | ((block & 0x000F) << 8)


def mix_columns(block: int, inverse: bool = False) -> int:
    validate_uint(block, 16, "状态")
    a, b, c, d = block >> 12, (block >> 8) & 15, (block >> 4) & 15, block & 15
    if inverse:
        a, b, c, d = _M9[a] ^ _M2[b], _M2[a] ^ _M9[b], _M9[c] ^ _M2[d], _M2[c] ^ _M9[d]
    else:
        a, b, c, d = a ^ _M4[b], _M4[a] ^ b, c ^ _M4[d], _M4[c] ^ d
    return a << 12 | b << 8 | c << 4 | d


def expand_key(key: int) -> tuple[int, int, int]:
    """将 16 bit 密钥扩展成三个 16 bit 轮密钥 K0,K1,K2。"""
    validate_uint(key, 16, "密钥")
    words = [key >> 8, key & 255]
    for constant in RCON:
        last = words[-1]
        transformed = (SBOX[last & 15] << 4 | SBOX[last >> 4]) ^ constant
        next_word = words[-2] ^ transformed
        words.extend((next_word, next_word ^ last))
    return tuple(words[i] << 8 | words[i + 1] for i in (0, 2, 4))


def encrypt_block(plaintext: int, key: int) -> int:
    validate_uint(plaintext, 16, "明文")
    k0, k1, k2 = expand_key(key)
    state = plaintext ^ k0
    state = mix_columns(shift_rows(_sub(state, SBOX))) ^ k1
    return shift_rows(_sub(state, SBOX)) ^ k2


def decrypt_block(ciphertext: int, key: int) -> int:
    validate_uint(ciphertext, 16, "密文")
    k0, k1, k2 = expand_key(key)
    state = _sub(shift_rows(ciphertext ^ k2), INV_SBOX) ^ k1
    state = mix_columns(state, inverse=True)
    return _sub(shift_rows(state), INV_SBOX) ^ k0


@dataclass(frozen=True)
class TraceStep:
    name: str
    state: int


@dataclass(frozen=True)
class CipherTrace:
    output: int
    round_keys: tuple[int, int, int]
    steps: tuple[TraceStep, ...]


def _trace(block: int, key: int, decrypt: bool) -> CipherTrace:
    validate_uint(block, 16, "输入分组")
    keys = expand_key(key)
    if decrypt:
        operations = (
            ("轮密钥加 K2", lambda s: s ^ keys[2]),
            ("逆行移位", shift_rows),
            ("逆半字节替代", lambda s: _sub(s, INV_SBOX)),
            ("轮密钥加 K1", lambda s: s ^ keys[1]),
            ("逆列混淆", lambda s: mix_columns(s, inverse=True)),
            ("逆行移位", shift_rows),
            ("逆半字节替代", lambda s: _sub(s, INV_SBOX)),
            ("轮密钥加 K0", lambda s: s ^ keys[0]),
        )
    else:
        operations = (
            ("轮密钥加 K0", lambda s: s ^ keys[0]),
            ("第 1 轮 · 半字节替代", lambda s: _sub(s, SBOX)),
            ("第 1 轮 · 行移位", shift_rows),
            ("第 1 轮 · 列混淆", mix_columns),
            ("轮密钥加 K1", lambda s: s ^ keys[1]),
            ("第 2 轮 · 半字节替代", lambda s: _sub(s, SBOX)),
            ("第 2 轮 · 行移位", shift_rows),
            ("轮密钥加 K2", lambda s: s ^ keys[2]),
        )
    steps = [TraceStep("输入", block)]
    for name, operation in operations:
        block = operation(block)
        steps.append(TraceStep(name, block))
    return CipherTrace(block, keys, tuple(steps))


def encrypt_trace(plaintext: int, key: int) -> CipherTrace:
    return _trace(plaintext, key, False)


def decrypt_trace(ciphertext: int, key: int) -> CipherTrace:
    return _trace(ciphertext, key, True)
