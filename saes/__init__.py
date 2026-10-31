"""与课程附录 D 一致的教学用 S-AES。"""

from .core import decrypt_block, decrypt_trace, encrypt_block, encrypt_trace, expand_key

__all__ = ["encrypt_block", "decrypt_block", "expand_key", "encrypt_trace", "decrypt_trace"]
