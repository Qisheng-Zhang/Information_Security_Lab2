"""按仓库提交清单打包源码、文档、结果和五关原图。"""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from saes.version import __version__
from tools.check_repository import check_repository
from tools.project_layout import PROJECT_DIRECTORIES, PROJECT_FILES, is_project_file

OUTPUT = ROOT / f"dist/S-AES-Studio-{__version__}.zip"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--without-screenshots", action="store_true", help="省略独立 PNG 原图；Word 报告仍保留嵌入图片")
    args = parser.parse_args()
    checks = check_repository(include_screenshots=not args.without_screenshots)
    if checks["errors"]:
        raise SystemExit("打包前检查失败：\n" + "\n".join(checks["errors"]))
    paths = [ROOT / name for name in PROJECT_FILES]
    for directory in PROJECT_DIRECTORIES:
        paths.extend(path for path in (ROOT / directory).rglob("*") if path.is_file()
                     and is_project_file(path.relative_to(ROOT))
                     and not (args.without_screenshots and directory == "截图与视频" and path.suffix.lower() == ".png"))
    output = OUTPUT.with_name(f"S-AES-Studio-{__version__}-code.zip") if args.without_screenshots else OUTPUT
    output.parent.mkdir(exist_ok=True)
    prefix = Path(f"S-AES-Studio-{__version__}")
    manifest = {"version": __version__, "files": {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}}
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            archive.write(path, prefix / path.relative_to(ROOT))
        archive.writestr((prefix / "MANIFEST.json").as_posix(), json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise SystemExit("ZIP 校验失败")
        for relative, expected_hash in manifest["files"].items():
            if hashlib.sha256(archive.read((prefix / relative).as_posix())).hexdigest() != expected_hash:
                raise SystemExit(f"文件校验失败：{relative}")
        print(f"交付包：{output.name}，{len(archive.namelist())} 个文件，{output.stat().st_size} 字节。")


if __name__ == "__main__":
    main()
