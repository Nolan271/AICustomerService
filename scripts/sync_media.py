"""
将 MinerU 解析出的图片同步到 data/media/images/ 统一目录

用法：
    uv run python scripts/sync_media.py

功能：
    1. 扫描 MinerU 输出目录下所有图片
    2. 复制到 data/media/images/（扁平化，UUID 命名）
    3. 同名文件自动跳过（幂等）

迁移新服务器时，先配好 .env 中的 MEDIA_DIR，再运行此脚本。
"""

import os
import shutil
import sys
from pathlib import Path

# 加入项目根目录
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings

# MinerU 输出目录（从 docker-compose 挂载路径获取）
MINERU_BASE = Path(r"C:\Users\muzhi\MinerU")

# 目标目录（从 .env 读取）
TARGET_DIR = Path(settings.MEDIA_DIR)


def sync_images():
    if not MINERU_BASE.exists():
        print(f"[跳过] MinerU 目录不存在: {MINERU_BASE}")
        return 0

    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    skipped = 0

    for entry in os.listdir(MINERU_BASE):
        entry_path = MINERU_BASE / entry
        images_dir = entry_path / "images"

        if not images_dir.is_dir():
            continue

        for img_file in images_dir.iterdir():
            if img_file.suffix.lower() not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                continue

            target_file = TARGET_DIR / img_file.name
            if target_file.exists():
                skipped += 1
                continue

            shutil.copy2(str(img_file), str(target_file))
            copied += 1
            print(f"  OK {img_file.name}")

    print(f"\n完成：复制 {copied} 张，跳过 {skipped} 张（已存在）")
    print(f"图片目录：{TARGET_DIR}")
    return copied


if __name__ == "__main__":
    sync_images()
