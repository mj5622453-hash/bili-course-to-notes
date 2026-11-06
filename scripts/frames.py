#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抽帧、按画面差异分页、拼联系表。

用法:
    # 定点抽帧（推荐）：按考点时间戳单抽，命中率远高于均匀抽
    python frames.py pick video.mp4 --at 120,300,450,900 -o images/ --name pre

    # 密集抽帧（需要先摸清结构时用）
    python frames.py scan video.mp4 -o frames/ --every 6

    # 按画面差异分页（每页取最后一帧，批注最完整）
    python frames.py pages frames/ -o pages/

    # 拼 3x3 联系表，便于快速筛图
    python frames.py sheet pages/ -o sheet.jpg

依赖: ffmpeg, Pillow, numpy
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def ffmpeg() -> str:
    p = shutil.which("ffmpeg")
    if not p:
        sys.exit("找不到 ffmpeg")
    return p


def pick(video: str, stamps: list[int], outdir: str, prefix: str):
    """定点单抽一帧。时间点建议取「知识点开头 5-20 秒」。"""
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    ff = ffmpeg()
    for t in stamps:
        dst = out / f"{prefix}_{t:05d}.jpg"
        # 注意 format=yuvj420p：不加会触发 mjpeg 编码器 "Non full-range YUV" 错误
        subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-ss", str(t),
                        "-i", video, "-frames:v", "1", "-q:v", "2", "-y", str(dst)],
                       check=False)
        print(f"{t // 60}:{t % 60:02d} -> {dst.name}  ({'ok' if dst.exists() else 'FAIL'})")


def scan(video: str, outdir: str, every: float):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    ff = ffmpeg()
    fps = f"1/{every}"
    cmd = [ff, "-hide_banner", "-loglevel", "error", "-i", video, "-an",
           "-vf", f"fps={fps},scale=1280:-1,format=yuvj420p", "-q:v", "3",
           "-y", str(out / "f%05d.jpg")]
    subprocess.run(cmd, check=False)
    n = len(list(out.glob("*.jpg")))
    print(f"抽出 {n} 帧")
    if n <= 1:
        print("⚠ 只出 0-1 帧：检查 stderr 全文，常见原因是缺 format=yuvj420p")


def pages(frames_dir: str, outdir: str, thresh: float = 1.0):
    """按灰度 32x32 平均绝对差切段，每段取最后一帧"""
    import numpy as np
    from PIL import Image

    fs = sorted(Path(frames_dir).glob("*.jpg"))
    if not fs:
        sys.exit("没有帧")

    def gray(p):
        return np.asarray(Image.open(p).convert("L").resize((32, 32)), dtype=np.int16)

    segs, cur, prev = [], [], None
    for f in fs:
        a = gray(f)
        if prev is None or float(np.abs(a - prev).mean()) > thresh:
            if cur:
                segs.append(cur)
            cur = [f]
        else:
            cur.append(f)
        prev = a
    if cur:
        segs.append(cur)

    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    for i, seg in enumerate(segs, 1):
        shutil.copy(seg[-1], out / f"{i:04d}.jpg")
    print(f"分页 {len(segs)} 页（每页取段内最后一帧）")


def sheet(src_dir: str, out_path: str, cols: int = 3, cell=(440, 248)):
    from PIL import Image, ImageDraw

    fs = sorted(Path(src_dir).glob("*.jpg"))
    if not fs:
        sys.exit("没有图片")
    CW, CH = cell
    PAD, LB = 8, 20
    rows = (len(fs) + cols - 1) // cols
    W = cols * CW + (cols + 1) * PAD
    H = rows * (CH + LB) + (rows + 1) * PAD
    s = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(s)
    for i, f in enumerate(fs):
        r, c = divmod(i, cols)
        x, y = PAD + c * (CW + PAD), PAD + r * (CH + LB + PAD)
        s.paste(Image.open(f).convert("RGB").resize((CW, CH), Image.LANCZOS), (x, y))
        d.text((x + 2, y + CH + 3), f.stem[:34], fill="black")
    s.save(out_path, quality=86)
    print(f"联系表 {out_path}（{len(fs)} 张，{rows}x{cols}）")


def main():
    ap = argparse.ArgumentParser(description="抽帧与分页")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("pick")
    p1.add_argument("video")
    p1.add_argument("--at", required=True, help="逗号分隔的秒数")
    p1.add_argument("-o", "--outdir", default="images")
    p1.add_argument("--name", default="f")

    p2 = sub.add_parser("scan")
    p2.add_argument("video")
    p2.add_argument("-o", "--outdir", default="frames")
    p2.add_argument("--every", type=float, default=6, help="每 N 秒一帧")

    p3 = sub.add_parser("pages")
    p3.add_argument("src")
    p3.add_argument("-o", "--outdir", default="pages")
    p3.add_argument("--thresh", type=float, default=1.0)

    p4 = sub.add_parser("sheet")
    p4.add_argument("src")
    p4.add_argument("-o", "--out", default="sheet.jpg")
    p4.add_argument("--cols", type=int, default=3)

    a = ap.parse_args()
    if a.cmd == "pick":
        pick(a.video, [int(x) for x in a.at.split(",")], a.outdir, a.name)
    elif a.cmd == "scan":
        scan(a.video, a.outdir, a.every)
    elif a.cmd == "pages":
        pages(a.src, a.outdir, a.thresh)
    elif a.cmd == "sheet":
        sheet(a.src, a.out, a.cols)


if __name__ == "__main__":
    main()
