"""双重 S-AES 的中间相遇攻击；保留碰撞密钥，不假设单对能唯一恢复。"""

from collections.abc import Callable, Iterable
from threading import Event

from .core import decrypt_block, encrypt_block, validate_uint
from .multiple import double_encrypt


class AttackCancelled(Exception):
    """用户取消攻击。"""


def meet_in_the_middle(
    pairs: Iterable[tuple[int, int]],
    progress: Callable[[str, int, int], None] | None = None,
    cancel: Event | None = None,
) -> list[int]:
    """枚举完整 K1/K2 空间，额外明密文对过滤候选，返回全部 32 bit 候选。"""
    pairs = tuple(pairs)
    if not pairs:
        raise ValueError("至少需要一组明密文对")
    for plain, cipher in pairs:
        validate_uint(plain, 16, "已知明文")
        validate_uint(cipher, 16, "已知密文")

    def checkpoint(stage: str, done: int):
        if cancel is not None and cancel.is_set():
            raise AttackCancelled("攻击已取消")
        if progress is not None:
            progress(stage, done, 0x10000)

    plain, cipher = pairs[0]
    forward: dict[int, list[int]] = {}
    checkpoint("建立 K1 中间值表", 0)
    for k1 in range(0x10000):
        if k1 % 512 == 0:
            checkpoint("建立 K1 中间值表", k1)
        middle = encrypt_block(plain, k1)
        forward.setdefault(middle, []).append(k1)
    checkpoint("建立 K1 中间值表", 0x10000)
    candidates = []
    for k2 in range(0x10000):
        if k2 % 512 == 0:
            checkpoint("匹配 K2 并过滤候选", k2)
        for k1 in forward.get(decrypt_block(cipher, k2), ()):
            key = k1 << 16 | k2
            if all(double_encrypt(p, key) == c for p, c in pairs[1:]):
                candidates.append(key)
    checkpoint("匹配 K2 并过滤候选", 0x10000)
    return candidates
