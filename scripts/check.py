#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交付前自检：配图覆盖率、图片/链接可达性、时间戳完整性。

用法:
    python check.py notes.md
    python check.py notes.md --base .        # 相对路径的基准目录

为什么需要它：
    配图最容易「按章节配」而不是「按方法配」——一章放一张图看似齐了，
    但章内可能有 5 个方法。这个脚本逐小节检查，把没图的列出来。
"""
import argparse
import re
from pathlib import Path

METHOD_HINT = ("方法", "法", "技巧", "口诀", "步骤", "流程", "规律", "公式",
               "定理", "策略", "套路", "模型")


def analyze(md: Path):
    text = md.read_text(encoding="utf-8")
    cur, has_img, has_link = None, False, False
    sections = []

    for line in text.split("\n"):
        m = re.match(r"^(#{2,4})\s+(.+)", line)
        if m:
            if cur:
                sections.append({"title": cur, "img": has_img, "link": has_link})
            cur, has_img, has_link = m.group(2).strip(), False, False
        elif line.strip().startswith("!["):
            has_img = True
        elif re.search(r"\]\([^)]+\.(mp4|m4a|mp3)\)", line):
            has_link = True
    if cur:
        sections.append({"title": cur, "img": has_img, "link": has_link})

    # 资源可达性
    base = md.parent
    imgs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
    vids = re.findall(r"\]\(([^)]+\.(?:mp4|m4a|mp3))\)", text)
    miss_img = [p for p in imgs if not p.startswith("http") and not (base / p).exists()]
    miss_vid = [p for p in vids if not p.startswith("http") and not (base / p).exists()]

    # 时间戳
    stamps = re.findall(r"\bP\d{1,2}\s+\d{1,2}:\d{2}", text)

    return sections, (len(imgs), miss_img), (len(vids), miss_vid), len(stamps)


def main():
    ap = argparse.ArgumentParser(description="文档交付前自检")
    ap.add_argument("md")
    ap.add_argument("--quiet", action="store_true", help="只报问题")
    args = ap.parse_args()

    md = Path(args.md)
    sections, img_stat, vid_stat, n_stamp = analyze(md)

    no_img = [s["title"] for s in sections if not s["img"]]
    method_like = [t for t in no_img if any(k in t for k in METHOD_HINT)]

    print(f"== {md.name} ==")
    print(f"小节 {len(sections)} 个 ｜ 有图 {sum(1 for s in sections if s['img'])} ｜ 无图 {len(no_img)}")
    print(f"图片 {img_stat[0]} 张（缺失 {len(img_stat[1])}）｜ 视频链接 {vid_stat[0]} 个（缺失 {len(vid_stat[1])}）")
    print(f"时间戳 {n_stamp} 处")

    if method_like:
        print(f"\n⚠ 以下 {len(method_like)} 个「方法类」小节没有配图：")
        for t in method_like:
            print("   -", t)

    if img_stat[1]:
        print(f"\n✗ 图片路径不存在 {len(img_stat[1])} 个：")
        for p in img_stat[1][:8]:
            print("   ", p)

    if vid_stat[1]:
        print(f"\n✗ 视频路径不存在 {len(vid_stat[1])} 个：")
        for p in vid_stat[1][:8]:
            print("   ", p)

    if not args.quiet and no_img:
        print(f"\n（无图小节全览，共 {len(no_img)}）")
        for t in no_img:
            print("   ·", t)

    ok = not method_like and not img_stat[1] and not vid_stat[1]
    print("\n" + ("✓ 通过" if ok else "✗ 有项目需要处理"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
