"""无 GUI 的分组命令行接口，便于跨平台互测。"""

import argparse

from .core import decrypt_block, encrypt_block
from .encoding import format_bits, parse_number
from .multiple import double_decrypt, double_encrypt, triple_decrypt, triple_encrypt


def main():
    parser = argparse.ArgumentParser(description="S-AES 附录 D 分组加解密")
    parser.add_argument("operation", choices=("encrypt", "decrypt"))
    parser.add_argument("data", help="16 bit 分组，hex 或二进制")
    parser.add_argument("key", help="密钥，hex 或二进制")
    parser.add_argument("--mode", choices=("single", "double", "triple32", "triple48"), default="single")
    args = parser.parse_args()
    bits = 16 if args.mode == "single" else 48 if args.mode == "triple48" else 32
    try:
        data, key = parse_number(args.data), parse_number(args.key, bits)
        decrypt = args.operation == "decrypt"
        if args.mode == "single":
            output = (decrypt_block if decrypt else encrypt_block)(data, key)
        elif args.mode == "double":
            output = (double_decrypt if decrypt else double_encrypt)(data, key)
        else:
            output = (triple_decrypt if decrypt else triple_encrypt)(data, key, bits)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"{output:04X}")
    print(format_bits(output))


if __name__ == "__main__":
    main()
