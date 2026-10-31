"""输入解析、2 字节分组与保留所有字节的显示。"""

import re

from .core import validate_uint


def parse_number(text: str, bits: int = 16) -> int:
    """完整 bits 位 01 串按二进制解析，其余按 hex；小写 0b 显式二进制。"""
    if bits not in (16, 32, 48):
        raise ValueError("位宽须为 16、32 或 48")
    compact = re.sub(r"[\s_]", "", text)
    if not compact:
        raise ValueError("输入不能为空")
    # 大写 HEX 0B01 是合法的四位分组；不能把它误识别为二进制前缀。
    if compact.startswith("0b"):
        digits, base = compact[2:], 2
        valid = bool(re.fullmatch(r"[01]+", digits))
    elif compact.lower().startswith("0x"):
        digits, base = compact[2:], 16
        valid = bool(re.fullmatch(r"[0-9a-fA-F]+", digits))
    elif len(compact) == bits and set(compact) <= {"0", "1"}:
        digits, base, valid = compact, 2, True
    else:
        digits, base = compact, 16
        valid = bool(re.fullmatch(r"[0-9a-fA-F]+", digits))
    if not valid or len(digits) > (bits if base == 2 else bits // 4):
        raise ValueError(f"请输入不超过 {bits // 4} 位 hex 或 {bits} 位二进制（可带 0x/0b）")
    return validate_uint(int(digits, base), bits, "输入")


def format_bits(value: int, bits: int = 16) -> str:
    validate_uint(value, bits)
    binary = f"{value:0{bits}b}"
    return " ".join(binary[i:i + 4] for i in range(0, bits, 4))


def bytes_to_blocks(data: bytes) -> tuple[list[int], int]:
    length = len(data)
    padded = data + (b"\0" if length % 2 else b"")
    return [int.from_bytes(padded[i:i + 2], "big") for i in range(0, len(padded), 2)], length


def blocks_to_bytes(blocks: list[int], original_length: int | None = None) -> bytes:
    for block in blocks:
        validate_uint(block, 16, "分组")
    data = b"".join(block.to_bytes(2, "big") for block in blocks)
    if original_length is not None:
        if type(original_length) is not int or original_length < 0 or (original_length + 1) // 2 != len(blocks):
            raise ValueError("原始字节数与分组数量不匹配")
        data = data[:original_length]
    return data


def ascii_to_blocks(text: str) -> tuple[list[int], int]:
    try:
        return bytes_to_blocks(text.encode("ascii"))
    except UnicodeEncodeError as exc:
        raise ValueError("本关使用 ASCII 编码，请输入英文、数字、符号或换行") from exc


def escape_bytes(data: bytes) -> str:
    """密文可含 0x00..0xFF；不可打印字节显示为可逆的 \\xHH，反斜杠为 \\\\。"""
    return "".join(chr(b) if 32 <= b <= 126 and b != 92 else f"\\x{b:02X}" for b in data)
