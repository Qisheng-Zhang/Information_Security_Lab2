"""检查交付文件、五关原图、JSON/CSV 数据与 Markdown 本地链接。"""

import csv
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.project_layout import (PROJECT_DIRECTORIES, PROJECT_FILES,
                                  REQUIRED_DOCUMENTS, REQUIRED_RESULTS,
                                  SCREENSHOT_NAMES, is_project_file)


def check_repository(root=ROOT, include_screenshots=True):
    root = Path(root).resolve()
    errors = []
    expected = list(PROJECT_FILES) + list(REQUIRED_DOCUMENTS)
    expected += [f"docs/results/{name}" for name in REQUIRED_RESULTS]
    if include_screenshots:
        expected += [f"截图与视频/{name}" for name in SCREENSHOT_NAMES]
    for relative in expected:
        if not (root / relative).is_file():
            errors.append(f"缺少文件：{relative}")
    paths = [root / "README.md"]
    for directory in PROJECT_DIRECTORIES:
        paths.extend(path for path in (root / directory).rglob("*.md") if is_project_file(path.relative_to(root)))
    links = 0
    for path in paths:
        if not path.is_file():
            continue
        content = re.sub(r"^```[^\n]*\n.*?^```\s*$", "", path.read_text(encoding="utf-8-sig"), flags=re.M | re.S)
        for match in re.finditer(r"!?\[[^\]\n]*\]\(([^)\n]+)\)", content):
            target = match.group(1).strip().strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                continue
            relative = unquote(parsed.path)
            destination = (path.parent / relative).resolve() if relative else path
            links += 1
            if not destination.is_relative_to(root):
                errors.append(f"链接越出项目：{path.relative_to(root)} → {target}")
            elif not destination.exists():
                if not include_screenshots and destination.parent.name == "截图与视频" and destination.suffix == ".png":
                    continue
                errors.append(f"失效链接：{path.relative_to(root)} → {target}")
            elif parsed.fragment and destination.suffix == ".md":
                linked_text = destination.read_text(encoding="utf-8-sig")
                anchors = re.findall(r'<a\s+id=[\"\']([^\"\']+)', linked_text)
                for heading in re.findall(r"^#{1,6}\s+(.+)$", linked_text, flags=re.M):
                    anchors.append(re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-"))
                if unquote(parsed.fragment) not in anchors:
                    errors.append(f"失效锚点：{path.relative_to(root)} → {target}")
    for path in (root / "docs/results").glob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
        except (ValueError, OSError) as exc:
            errors.append(f"JSON 无效：{path.name}：{exc}")
    csv_path = root / "docs/results/cross_check.csv"
    if csv_path.is_file():
        with csv_path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        if len(rows) != 1005 or any(row.get("passed") != "True" for row in rows):
            errors.append("交叉测试 CSV 需要包含 1005 组通过记录")
        demo_path = root / "docs/results/cpp_demo_vectors.json"
        if demo_path.is_file():
            demo = json.loads(demo_path.read_text(encoding="utf-8-sig"))
            expected_vectors = [{"plaintext": row["plaintext"], "key": row["key"], "ciphertext": row["cpp_encrypt"]} for row in rows]
            if demo.get("vectors") != expected_vectors:
                errors.append("完整演示向量与实际 C++ 输出不一致")
    report = root / "docs/S-AES实验报告_截图演示版.docx"
    if report.is_file():
        try:
            with zipfile.ZipFile(report) as archive:
                if archive.testzip() is not None or "word/document.xml" not in archive.namelist():
                    errors.append("Word 报告包结构无效")
        except zipfile.BadZipFile:
            errors.append("Word 报告不是有效 DOCX")
    return {"markdown_files": len(paths), "local_links": links, "required_files": len(expected), "screenshots": len(SCREENSHOT_NAMES) if include_screenshots else 0, "errors": errors}


def main():
    result = check_repository()
    if result["errors"]:
        for error in result["errors"]:
            print(error)
        return 1
    print(f"仓库检查通过：{result['markdown_files']} 份 Markdown，{result['local_links']} 个本地链接，15 张原图，1005 组 C++ 记录。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
