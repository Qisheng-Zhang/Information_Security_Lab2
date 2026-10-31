import json
import random
import threading
import unittest

from saes.attacks import AttackCancelled, meet_in_the_middle
from saes.core import (INV_SBOX, RCON, SBOX, block_to_state, decrypt_block,
                       decrypt_trace, encrypt_block, encrypt_trace, expand_key,
                       gf_mul, mix_columns, shift_rows, sub_nibbles)
from saes.encoding import (ascii_to_blocks, blocks_to_bytes, bytes_to_blocks,
                           escape_bytes, format_bits, parse_number)
from saes.modes import (CipherPacket, cbc_decrypt, cbc_encrypt, decrypt_packet,
                        encrypt_ascii, generate_iv)
from saes.multiple import (double_decrypt, double_encrypt, split_keys,
                           triple_decrypt, triple_encrypt)


class CoreTests(unittest.TestCase):
    def test_pdf_sboxes(self):
        self.assertEqual(SBOX, (9, 4, 10, 11, 13, 1, 8, 5, 6, 2, 0, 3, 12, 14, 15, 7))
        self.assertEqual(INV_SBOX, (10, 5, 9, 11, 1, 7, 8, 15, 6, 0, 2, 3, 12, 4, 13, 14))
        self.assertEqual(RCON, (0x80, 0x30))
        for value in range(16):
            self.assertEqual(INV_SBOX[SBOX[value]], value)

    def test_pdf_key_expansion(self):
        self.assertEqual(expand_key(0x2D55), (0x2D55, 0xBCE9, 0xA34A))

    def test_pdf_transform_examples(self):
        # PDF p.507 的矩阵 [A 4;7 9] 按列序拼成 A749，而非 A479。
        self.assertEqual(block_to_state(0xA749), ((0xA, 4), (7, 9)))
        self.assertEqual(0xA749 ^ 0x2D55, 0x8A1C)
        self.assertEqual(sub_nibbles(0x8A1C), 0x604C)
        self.assertEqual(shift_rows(0x604C), 0x6C40)
        self.assertEqual(mix_columns(0x6C40), 0x3743)
        self.assertEqual(mix_columns(0x3743, True), 0x6C40)

    def test_pdf_gf_example_and_field_laws(self):
        self.assertEqual(gf_mul(4, 0xC), 5)
        for left in range(16):
            for right in range(16):
                self.assertEqual(gf_mul(left, right), gf_mul(right, left))
                self.assertEqual(gf_mul(left, right ^ 5), gf_mul(left, right) ^ gf_mul(left, 5))

    def test_fixed_regression_vector(self):
        self.assertEqual(encrypt_block(0x6F6B, 0xA73B), 0x0738)
        self.assertEqual(decrypt_block(0x0738, 0xA73B), 0x6F6B)
        # 旧 C++ 参数产生 AFA2；本实现以所给 PDF 为准。
        self.assertEqual(encrypt_block(0xD6B3, 0xA73B), 0x000F)

    def test_random_roundtrips_10000(self):
        generator = random.Random(20261030)
        for _ in range(10000):
            plain, key = generator.randrange(65536), generator.randrange(65536)
            self.assertEqual(decrypt_block(encrypt_block(plain, key), key), plain)

    def test_full_domain_permutation_for_one_key(self):
        ciphertexts = {encrypt_block(p, 0x2D55) for p in range(65536)}
        self.assertEqual(len(ciphertexts), 65536)

    def test_trace_matches_core_and_reverses(self):
        forward = encrypt_trace(0x6F6B, 0xA73B)
        backward = decrypt_trace(forward.output, 0xA73B)
        self.assertEqual(forward.output, encrypt_block(0x6F6B, 0xA73B))
        self.assertEqual(backward.output, 0x6F6B)
        self.assertEqual([s.state for s in forward.steps], list(reversed([s.state for s in backward.steps])))

    def test_invalid_integer_inputs(self):
        for invalid in (-1, 65536, True, 2.5, "1234"):
            with self.assertRaises(ValueError):
                encrypt_block(invalid, 0)
            with self.assertRaises(ValueError):
                decrypt_block(0, invalid)


class EncodingTests(unittest.TestCase):
    def test_supported_number_forms(self):
        for text in ("A73B", "0xa73b", "1010011100111011", "1010 0111 0011 1011", "0b1010011100111011", "A7_3B"):
            self.assertEqual(parse_number(text), 0xA73B)
        self.assertEqual(parse_number("1234"), 0x1234)
        self.assertEqual(parse_number("10"), 0x10)
        self.assertEqual(parse_number("0b10"), 2)
        self.assertEqual(parse_number("00001F2E3D4C", 48), 0x1F2E3D4C)
        self.assertEqual(format_bits(0x000F), "0000 0000 0000 1111")

    def test_all_formatted_hex_values_parse(self):
        for value in range(65536):
            self.assertEqual(parse_number(f"{value:04X}"), value)
        self.assertEqual(parse_number("0B01"), 0x0B01)
        self.assertEqual(parse_number("0x0b01"), 0x0B01)

    def test_rejected_number_forms(self):
        for text in ("", " ", "-1", "+1", "0x", "0b", "0b102", "GGGG", "10000", "0x10000", "1" * 17):
            with self.assertRaises(ValueError, msg=text):
                parse_number(text)

    def test_all_byte_values_are_preserved(self):
        raw = bytes(range(256))
        blocks, length = bytes_to_blocks(raw)
        self.assertEqual(blocks_to_bytes(blocks, length), raw)
        self.assertEqual(escape_bytes(b"A\x00\xFF\\"), "A\\x00\\xFF\\x5C")

    def test_empty_odd_and_trailing_null(self):
        for text in ("", "A", "AB", "ABC", "A\0", "AB\0", "ABC\n"):
            blocks, length = ascii_to_blocks(text)
            self.assertEqual(blocks_to_bytes(blocks, length), text.encode("ascii"))
        with self.assertRaises(ValueError):
            ascii_to_blocks("中文")
        with self.assertRaises(ValueError):
            blocks_to_bytes([1, 2], 1)


class ModesTests(unittest.TestCase):
    def test_ascii_ecb_packets_fresh_session(self):
        for text in ("", "A", "AB", "Hello, S-AES!", "ABC\n", "ABC\0"):
            packet = encrypt_ascii(text, 0xA73B)
            restored = CipherPacket.from_json(packet.to_json())
            self.assertEqual(decrypt_packet(restored, 0xA73B), text.encode("ascii"))
            self.assertNotIn('"key"', packet.to_json())

    def test_cbc_packets_and_iv(self):
        for text in ("", "X", "ABCD", "Hello\nCBC\0"):
            packet = encrypt_ascii(text, 0xA73B, "CBC", 0x1357)
            restored = CipherPacket.from_json(packet.to_json())
            self.assertEqual(restored.iv, 0x1357)
            self.assertEqual(decrypt_packet(restored, 0xA73B), text.encode("ascii"))
        self.assertNotEqual(encrypt_ascii("ABCD", 1, "CBC", 1).blocks, encrypt_ascii("ABCD", 1, "CBC", 2).blocks)

    def test_iv_generation_range(self):
        self.assertTrue(all(0 <= generate_iv() <= 65535 for _ in range(100)))

    def test_cbc_formula(self):
        blocks = [0x1234, 0x5678, 0x9ABC]
        c1 = encrypt_block(blocks[0] ^ 0x1357, 0xA73B)
        c2 = encrypt_block(blocks[1] ^ c1, 0xA73B)
        c3 = encrypt_block(blocks[2] ^ c2, 0xA73B)
        self.assertEqual(cbc_encrypt(blocks, 0xA73B, 0x1357), [c1, c2, c3])
        self.assertEqual(cbc_decrypt([c1, c2, c3], 0xA73B, 0x1357), blocks)

    def test_cbc_bitflip_propagation(self):
        plain = [0x4142, 0x4344, 0x4546, 0x4748]
        cipher = cbc_encrypt(plain, 0xA73B, 0x1357)
        for index in range(len(cipher)):
            changed = cipher.copy()
            changed[index] ^= 0x0001
            after = cbc_decrypt(changed, 0xA73B, 0x1357)
            self.assertNotEqual(after[index], plain[index])
            if index + 1 < len(plain):
                self.assertEqual(after[index + 1] ^ plain[index + 1], 1)
            self.assertEqual(after[:index], plain[:index])
            self.assertEqual(after[index + 2:], plain[index + 2:])

    def test_cbc_replacement_propagation(self):
        plain = [0x4142, 0x4344, 0x4546, 0x4748]
        cipher = cbc_encrypt(plain, 0xA73B, 0x1357)
        changed = cipher.copy()
        changed[1] = cipher[1] ^ 0xFFFF
        after = cbc_decrypt(changed, 0xA73B, 0x1357)
        self.assertEqual(after[2] ^ plain[2], 0xFFFF)
        self.assertEqual(after[0], plain[0])
        self.assertEqual(after[3], plain[3])

    def test_changing_iv_only_changes_first_plain_block(self):
        plain = [0x4142, 0x4344, 0x4546]
        cipher = cbc_encrypt(plain, 0xA73B, 0x1357)
        after = cbc_decrypt(cipher, 0xA73B, 0x1356)
        self.assertEqual(after[0] ^ plain[0], 1)
        self.assertEqual(after[1:], plain[1:])

    def test_reject_invalid_packets(self):
        good = json.loads(encrypt_ascii("ABC", 1, "CBC", 2).to_json())
        for field, invalid in (("version", True), ("version", 2), ("profile", "other"), ("mode", "CTR"),
                               ("original_length", -1), ("original_length", True), ("original_length", 8),
                               ("iv", None), ("iv", "10000"), ("blocks", ["ZZZZ"]), ("blocks", [65535])):
            bad = good.copy()
            bad[field] = invalid
            with self.assertRaises(ValueError, msg=field):
                CipherPacket.from_json(json.dumps(bad))
        for text in ("not json", "[]", "null", "{}"):
            with self.assertRaises(ValueError):
                CipherPacket.from_json(text)

    def test_validate_empty_message_parameters(self):
        with self.assertRaises(ValueError):
            cbc_encrypt([], -1, 0)
        with self.assertRaises(ValueError):
            cbc_decrypt([], 0, 65536)
        with self.assertRaises(ValueError):
            encrypt_ascii("", -1)


class MultipleTests(unittest.TestCase):
    def test_double_order_and_roundtrip(self):
        p, k1, k2 = 0x6F6B, 0x1F2E, 0x3D4C
        key = k1 << 16 | k2
        self.assertEqual(double_encrypt(p, key), encrypt_block(encrypt_block(p, k1), k2))
        self.assertEqual(double_decrypt(double_encrypt(p, key), key), p)

    def test_triple_48_and_leading_zero_key(self):
        for key in (0x1F2E3D4C5A6B, 0x00001F2E3D4C, 0):
            k1, k2, k3 = split_keys(key, 48)
            expected = encrypt_block(encrypt_block(encrypt_block(0x1234, k1), k2), k3)
            self.assertEqual(triple_encrypt(0x1234, key, 48), expected)
            self.assertEqual(triple_decrypt(expected, key, 48), 0x1234)

    def test_triple_32_key_reuse(self):
        key, p = 0x1F2E3D4C, 0x6F6B
        expected = encrypt_block(encrypt_block(encrypt_block(p, 0x1F2E), 0x3D4C), 0x1F2E)
        self.assertEqual(triple_encrypt(p, key, 32), expected)
        self.assertEqual(triple_decrypt(expected, key, 32), p)

    def test_multiencryption_random_roundtrips(self):
        generator = random.Random(42)
        for _ in range(200):
            p, key32, key48 = generator.randrange(65536), generator.getrandbits(32), generator.getrandbits(48)
            self.assertEqual(double_decrypt(double_encrypt(p, key32), key32), p)
            self.assertEqual(triple_decrypt(triple_encrypt(p, key48), key48), p)
            self.assertEqual(triple_decrypt(triple_encrypt(p, key32, 32), key32, 32), p)


class AttackTests(unittest.TestCase):
    def test_complete_search_collision_retention_and_filtering(self):
        key = 0x1F2E3D4C
        pairs = [(p, double_encrypt(p, key)) for p in (0x6F6B, 0x1234, 0xBEEF)]
        one_pair = meet_in_the_middle(pairs[:1])
        self.assertIn(key, one_pair)
        self.assertGreater(len(one_pair), 1)
        # 同一 K2 可命中多个 K1，不能用中间值 -> 单个密钥覆盖碰撞。
        self.assertTrue(any(sum(1 for k in one_pair if k & 65535 == k2) > 1 for k2 in range(5)))
        recovered = meet_in_the_middle(pairs)
        self.assertEqual(recovered, [key])

    def test_contradictory_pairs_return_no_key(self):
        self.assertEqual(meet_in_the_middle([(0x1234, 0), (0x1234, 1)]), [])

    def test_cancellation_and_invalid_pairs(self):
        event = threading.Event()
        event.set()
        with self.assertRaises(AttackCancelled):
            meet_in_the_middle([(0, 0)], cancel=event)
        with self.assertRaises(ValueError):
            meet_in_the_middle([])
        with self.assertRaises(ValueError):
            meet_in_the_middle([(65536, 0)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
