# 原始测试结果与示例数据

| 文件 | 用途 | 来源 |
| --- | --- | --- |
| [五关测试结果.md](五关测试结果.md) | 各关算法数据、候选数、耗时与 CBC 差值 | `tools/verify.py` |
| [unittest.txt](unittest.txt) | 30 项单元测试的逐项日志 | `tools/verify.py` |
| [cross_check.md](cross_check.md) | Python/C++ 环境与验证方法 | `tools/verify.py` |
| [cross_check.csv](cross_check.csv) | 1005 组加密、任意密文解密与互解结果 | `tools/verify.py` 实际执行 C++ |
| [cross_vectors.json](cross_vectors.json) | 12 组简短交换示例 | `tools/verify.py` |
| [cpp_demo_vectors.json](cpp_demo_vectors.json) | 截图中载入的完整 1005 组 C++ 输出 | 由实际交叉测试 CSV 整理 |
| [ascii_cipher.json](ascii_cipher.json) | `Hello, S-AES!` 的 ASCII 密文包 | `tools/verify.py` |
| [cbc_cipher.json](cbc_cipher.json) | `Hello, S-AES CBC mode!` 的 CBC 密文包 | `tools/verify.py` |
| [gui_smoke.json](gui_smoke.json) | Qt 版本与 41 项界面检查 | `tools/gui_smoke.py --offscreen` |

重新验证会更新相应日志与耗时；截图是此前实际桌面操作的记录。简短向量适合交换格式演示，完整 C++ 数据适合复现截图中的 1005 组验证。

[返回测试报告](../测试报告.md) · [查看截图说明](../截图说明.md)
