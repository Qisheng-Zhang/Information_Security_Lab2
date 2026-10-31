"""运行单元测试、独立 C++ 互测，并生成五关可复现的实际结果。"""

import argparse
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import platform
import random
import shutil
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from saes.attacks import meet_in_the_middle
from saes.core import decrypt_block, encrypt_block, expand_key
from saes.encoding import ascii_to_blocks, blocks_to_bytes, escape_bytes
from saes.modes import PROFILE, CipherPacket, cbc_decrypt, cbc_encrypt, decrypt_packet, encrypt_ascii
from saes.multiple import double_decrypt, double_encrypt, triple_decrypt, triple_encrypt

RESULTS = ROOT / "docs/results"


def cross_check(skip=False):
    """真实调用独立 C++ 进程，比较加密、任意密文解密与 A/B 两方向互解。"""
    generator = random.Random(20261030)
    samples = [(0x6F6B, 0xA73B, 0x0738), (0xD6B3, 0xA73B, 0xAFA2),
               (0, 0, 0), (65535, 65535, 65535), (0x8000, 1, 0x1234)]
    samples += [(generator.randrange(65536), generator.randrange(65536), generator.randrange(65536)) for _ in range(1000)]
    compiler = shutil.which("g++")
    heading = "# 第 2 关：Python / C++ 独立实现交叉测试\n\n"
    if skip or not compiler:
        reason = "按命令参数跳过" if skip else "当前环境未找到 g++"
        (RESULTS / "cross_check.md").write_text(heading + f"未执行：{reason}。不能据此声称异构互测通过。\n", encoding="utf-8")
        return False, reason
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    executable = build / ("reference_saes.exe" if sys.platform == "win32" else "reference_saes")
    subprocess.run([compiler, "-std=c++11", "-O2", str(ROOT / "tests/reference_saes.cpp"), "-o", str(executable)], check=True, capture_output=True, text=True)
    input_data = "".join(f"{p:04X} {k:04X} {c:04X}\n" for p, k, c in samples)
    output = subprocess.run([str(executable)], input=input_data, capture_output=True, text=True, check=True, timeout=30)
    rows = output.stdout.splitlines()
    if len(rows) != len(samples):
        raise AssertionError("C++ 返回行数不匹配")
    csv = ["plaintext,key,cipher_input,python_encrypt,cpp_encrypt,python_decrypt,cpp_decrypt,python_dec_cpp_enc,cpp_dec_cpp_enc,passed"]
    for (p, k, c), row in zip(samples, rows):
        cpp_c, cpp_d, cpp_recovered = (int(part, 16) for part in row.split())
        python_c, python_d = encrypt_block(p, k), decrypt_block(c, k)
        python_recovered = decrypt_block(cpp_c, k)
        ok = python_c == cpp_c and python_d == cpp_d and cpp_recovered == p and python_recovered == p
        csv.append(",".join(f"{n:04X}" for n in (p, k, c, python_c, cpp_c, python_d, cpp_d, python_recovered, cpp_recovered)) + f",{ok}")
        if not ok:
            raise AssertionError(f"异构互测失败：P={p:04X} K={k:04X}")
    # 对方加密与本组加密一致后，C++ 对相同密文的还原也是 B 解 A。
    (RESULTS / "cross_check.csv").write_text("\n".join(csv) + "\n", encoding="utf-8")
    compiler_version = subprocess.run([compiler, "--version"], capture_output=True, text=True, check=True).stdout.splitlines()[0]
    text = heading + (
        f"实际执行：{len(samples)} 组，全部通过。\n\n"
        f"A：Python {platform.python_version()}，`saes/core.py`（整数状态）。\n\n"
        f"B：{compiler_version}，`tests/reference_saes.cpp`（四元素数组状态，独立多项式乘法）。\n\n"
        "逐组验证：加密相等、任意密文解密相等、A 解 B 恢复明文、B 解 A 恢复明文。\n\n"
        "B 的输入 C++ 解密样本还包含任意密文，并非只检测自身加密结果。完整记录见 `cross_check.csv`。\n\n"
        "这属于本机两种语言的独立实现互测，不冒充其他小组或不同操作系统的现场测试。"
        "与另一小组的现场记录请填写 [交叉测试记录模板](../交叉测试记录模板.md)。\n\n"
        "两份历史压缩包的比较：原 C++ S 盒和固定 0x80 轮常量不符合本次提供的 PDF。"
        "本测试参考实现已采用 PDF 的表 D.1、RCON=80/30；原压缩包源码未修改。\n"
    )
    (RESULTS / "cross_check.md").write_text(text, encoding="utf-8")
    vectors = {"profile": PROFILE, "vectors": [
        {"plaintext": f"{p:04X}", "key": f"{k:04X}", "ciphertext": f"{encrypt_block(p, k):04X}"}
        for p, k, _ in samples[:12]]}
    (RESULTS / "cross_vectors.json").write_text(json.dumps(vectors, indent=2), encoding="utf-8")
    return True, f"{len(samples)} 组全部通过"


def five_stage_report(test_result, duration, cross_result):
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S +08:00")
    p, key, key32, key48 = 0x6F6B, 0xA73B, 0x1F2E3D4C, 0x1F2E3D4C5A6B
    text = "Hello, S-AES!"
    ascii_packet = encrypt_ascii(text, key)
    (RESULTS / "ascii_cipher.json").write_text(ascii_packet.to_json(), encoding="utf-8")
    pairs = [(value, double_encrypt(value, key32)) for value in (p, 0x1234, 0xBEEF)]
    started = time.perf_counter()
    single_candidates = meet_in_the_middle(pairs[:1])
    recovered = meet_in_the_middle(pairs)
    attack_seconds = time.perf_counter() - started
    if key32 not in single_candidates or recovered != [key32]:
        raise AssertionError("中间相遇攻击演示未恢复预设密钥")
    packet = encrypt_ascii("Hello, S-AES CBC mode!", key, "CBC", 0x1357)
    (RESULTS / "cbc_cipher.json").write_text(packet.to_json(), encoding="utf-8")
    before = cbc_decrypt(list(packet.blocks), key, packet.iv)
    changed = list(packet.blocks)
    changed[0] ^= 1
    after = cbc_decrypt(changed, key, packet.iv)
    replaced = list(packet.blocks)
    replaced[1] = 0x0000
    replacement_result = cbc_decrypt(replaced, key, packet.iv)
    rows = ["| 分组 | 原明文 | 翻转 C1 后 | XOR 差值 |", "|---|---|---|---|"]
    rows.extend(f"| P{i} | {a:04X} | {b:04X} | {a ^ b:04X} |" for i, (a, b) in enumerate(zip(before, after), 1))
    replacement_rows = ["| 分组 | 原明文 | 替换 C2 后 | XOR 差值 |", "|---|---|---|---|"]
    replacement_rows.extend(f"| P{i} | {a:04X} | {b:04X} | {a ^ b:04X} |" for i, (a, b) in enumerate(zip(before, replacement_result), 1))
    passed = test_result.testsRun - len(test_result.failures) - len(test_result.errors) - len(test_result.skipped)
    report = f"""# 五关测试结果

执行时间：{now}。环境：Python {platform.python_version()} / {platform.system()} {platform.machine()}。

自动测试：**{passed}/{test_result.testsRun} 通过**，用时 {duration:.3f} 秒。原始日志见 `unittest.txt`。

## 第 1 关：基础算法与 GUI

- PDF 表 D.1 的正、逆 S 盒逐项核对通过；轮常量为 80、30。
- PDF D.3：`2D55 → BCE9 → A34A`。
- PDF D.2 各变换：`A749 XOR 2D55 = 8A1C → NS 604C → SR 6C40 → MC 3743`。
- 项目回归向量（不是该 PDF 中的完整加密算例）：P={p:04X}，K={key:04X}，C={encrypt_block(p, key):04X}，解密={decrypt_block(0x0738, key):04X}。
- 10000 组固定随机种子加解密往返通过；固定密钥 2D55 下全部 65536 个明文输出无重复。
- GUI 操作记录见 [gui_smoke.json](gui_smoke.json)；15 张实际桌面截图及操作步骤见 [截图说明](../截图说明.md)。

## 第 2 关：交叉测试

Python / 独立 C++：{cross_result[1]}。详见 `cross_check.md`、`cross_check.csv`。
另一小组的现场验证尚需组员交换向量并填写记录模板，不能以本机自检替代。

## 第 3 关：ASCII 字符串

- 原文：`{text}`，{len(text)} 字节，{len(ascii_packet.blocks)} 个两字节分组。
- 密文分组：`{' '.join(f'{b:04X}' for b in ascii_packet.blocks)}`。
- 原始密文字节转义显示：`{escape_bytes(blocks_to_bytes(list(ascii_packet.blocks)))}`。
- JSON 导出再导入后还原：`{decrypt_packet(CipherPacket.from_json(ascii_packet.to_json()), key).decode('ascii')}`。
- 空串、奇数长度、尾部空字节、换行都通过；非 ASCII 输入被拒绝。示例包：`ascii_cipher.json`。

## 第 4 关：多重加密与中间相遇

| 模式 | 密钥 | 明文 | 密文 | 解密 |
|---|---|---|---|---|
| 双重 EE / 32 bit | {key32:08X} | {p:04X} | {double_encrypt(p, key32):04X} | {double_decrypt(double_encrypt(p, key32), key32):04X} |
| 三重 EEE / 48 bit | {key48:012X} | {p:04X} | {triple_encrypt(p, key48, 48):04X} | {triple_decrypt(triple_encrypt(p, key48, 48), key48, 48):04X} |
| 三重 EEE / 32 bit，K1-K2-K1 | {key32:08X} | {p:04X} | {triple_encrypt(p, key32, 32):04X} | {triple_decrypt(triple_encrypt(p, key32, 32), key32, 32):04X} |

攻击已知对：{', '.join(f'({a:04X},{b:04X})' for a,b in pairs)}。

完整枚举 K1、K2 各 65536 个值：单对得到 {len(single_candidates)} 个候选并保留真密钥；
使用三对后得到 `{[f'{candidate:08X}' for candidate in recovered]}`，唯一候选为预设密钥。
上述两次攻击合计 {attack_seconds:.3f} 秒。相互矛盾的已知对返回零候选；取消操作测试通过。
48 bit 前导零密钥显式按 48 bit 处理，相关用例通过。

## 第 5 关：CBC 与篡改

K={key:04X}，IV={packet.iv:04X}，消息为 `Hello, S-AES CBC mode!`。

密文：`{' '.join(f'{b:04X}' for b in packet.blocks)}`。

原文：`{escape_bytes(decrypt_packet(packet, key))}`。

翻转 C1 的最低位后（原始包保持不变）：

{chr(10).join(rows)}

篡改后字节：`{escape_bytes(blocks_to_bytes(after, packet.original_length))}`。

P1 受非线性解密影响，P2 对应位翻转，P3 起相同。这里的“扰乱”不表示每一位必然翻转。

将 C2 从 {packet.blocks[1]:04X} 替换为 0000：

{chr(10).join(replacement_rows)}

P3 的 XOR 差值等于 C2 的替换差值 {packet.blocks[1]:04X}，P4 起不受影响。
空消息、任意位置翻转、替换分组、更改 IV 的传播边界均有自动测试。示例包：`cbc_cipher.json`。
CBC 本身不能认证密文，能观察到错误不等于能可靠检测所有篡改。
"""
    (RESULTS / "五关测试结果.md").write_text(report, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-cpp", action="store_true", help="无编译器时跳过互测并如实记录")
    args = parser.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    started = time.perf_counter()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    duration = time.perf_counter() - started
    log = stream.getvalue()
    (RESULTS / "unittest.txt").write_text(log, encoding="utf-8")
    print(log)
    if not result.wasSuccessful():
        return 1
    try:
        cross = cross_check(args.skip_cpp)
        five_stage_report(result, duration, cross)
    except (AssertionError, OSError, subprocess.SubprocessError) as exc:
        print(f"验证失败：{exc}")
        if isinstance(exc, subprocess.CalledProcessError):
            print(exc.stderr)
        return 1
    print("独立 C++ 互测：" + cross[1])
    print("五关报告已生成：docs/results/五关测试结果.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
