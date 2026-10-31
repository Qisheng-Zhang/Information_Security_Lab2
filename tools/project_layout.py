"""仓库提交范围与五关演示素材清单。"""

PROJECT_DIRECTORIES = ("saes", "tests", "tools", "docs", "截图与视频")
PROJECT_FILES = (
    "app.py", "README.md", "requirements.txt", ".gitignore",
    "启动程序.bat", "运行测试.bat",
)
SCREENSHOT_NAMES = (
    "第1关_加密.png", "第1关_解密.png", "第1关_逐轮状态.png",
    "第2关_交叉测试.png",
    "第3关_字符串加密.png", "第3关_字符串解密.png",
    "第4关_双重加密.png", "第4关_双重解密.png", "第4关_中间相遇攻击.png",
    "第4关_三重加密.png", "第4关_三重解密.png",
    "第5关_CBC加密.png", "第5关_CBC解密.png", "第5关_翻转密文.png", "第5关_替换分组.png",
)
REQUIRED_DOCUMENTS = (
    "docs/README.md", "docs/作业要求.md", "docs/算法标准.md", "docs/用户指南.md",
    "docs/开发手册.md", "docs/测试报告.md", "docs/截图说明.md",
    "docs/交叉测试记录模板.md", "docs/仓库整理说明.md",
    "docs/S-AES实验报告_截图演示版.docx", "docs/results/README.md",
    "截图与视频/README.md",
)
REQUIRED_RESULTS = (
    "五关测试结果.md", "unittest.txt", "gui_smoke.json", "cross_check.md",
    "cross_check.csv", "cross_vectors.json", "cpp_demo_vectors.json",
    "ascii_cipher.json", "cbc_cipher.json",
)
EXCLUDED_PARTS = {"__pycache__", ".venv", ".git", "本地归档", "tmp", "build", "dist", ".pytest_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".exe", ".dll", ".log", ".tmp"}


def is_project_file(path):
    """固定提交目录内部仍排除缓存、锁文件及编译产物。"""
    return (not any(part in EXCLUDED_PARTS for part in path.parts)
            and not path.name.startswith("~$")
            and path.suffix.lower() not in EXCLUDED_SUFFIXES)
