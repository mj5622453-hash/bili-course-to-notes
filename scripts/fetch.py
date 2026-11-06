#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B 站视频信息获取与下载封装（基于 yt-dlp）。

用法:
    # 1. 看分P结构（选片第一步，判断覆盖范围）
    python fetch.py info BV1xxxxxxxxx

    # 2. 查字幕
    python fetch.py subs BV1xxxxxxxxx --cookies cookies.txt

    # 3. 下字幕
    python fetch.py subs BV1xxxxxxxxx --cookies cookies.txt --save -o subs/

    # 4. 下视频（720p）
    python fetch.py video BV1xxxxxxxxx -o video/ --items 1,2,3

    # 5. 只下音频（无字幕时的兜底，几秒完成）
    python fetch.py audio BV1xxxxxxxxx -o audio/ --items 4

依赖: yt-dlp（pip install yt-dlp 或下载单文件 exe）
"""
import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"


def require(name: str) -> str:
    p = shutil.which(name)
    if not p:
        sys.exit(f"找不到 {name}，请先安装并加入 PATH")
    return p


def api_view(bvid: str) -> dict:
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://www.bilibili.com"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8"))
    if d.get("code") != 0:
        sys.exit(f"接口返回错误: {d.get('message')}")
    return d["data"]


def cmd_info(bvid: str):
    v = api_view(bvid)
    total = sum(p["duration"] for p in v["pages"])
    print(f"{v['title']}")
    print(f"UP: {v['owner']['name']} ｜ 播放: {v['stat']['view']:,} ｜ 分P: {len(v['pages'])}")
    print(f"总时长: {total // 3600}小时{total % 3600 // 60}分\n")
    for i, p in enumerate(v["pages"], 1):
        h, m2 = divmod(p["duration"], 3600)
        m, s = divmod(m2, 60)
        print(f"  P{i:02d}  {h:>2d}:{m:02d}:{s:02d}  {p['part'][:56]}")
    print("\n↑ 用分P标题判断覆盖范围，不要只看视频标题")


def cmd_subs(bvid: str, cookies: str | None, save: bool, outdir: str, items: str | None):
    ytdlp = require("yt-dlp")
    url = f"https://www.bilibili.com/video/{bvid}"
    base = [ytdlp, "--no-warnings"]
    if cookies:
        base += ["--cookies", cookies]

    if not save:
        r = subprocess.run(base + ["--list-subs", "--skip-download", url],
                           capture_output=True, text=True, errors="ignore")
        out = (r.stdout or "") + (r.stderr or "")
        if "ai-zh" in out or "zh-CN" in out:
            print("✓ 有中文字幕")
        else:
            print("✗ 无中文字幕 —— 走 audio 子命令下音频转写")
            print("  注意：若这是已知有字幕的视频，说明 cookie 过期了")
        for line in out.splitlines():
            if "p" in line and ":" in line and "subtitle" in line.lower():
                print("  ", line.strip())
        return

    Path(outdir).mkdir(parents=True, exist_ok=True)
    cmd = base + ["--skip-download", "--write-subs", "--sub-langs", "ai-zh",
                  "--sub-format", "srt", "-o", f"{outdir}/P%(playlist_index)02d.%(ext)s", url]
    if items:
        cmd[1:1] = ["--playlist-items", items]
    subprocess.run(cmd, check=False)
    got = list(Path(outdir).glob("*.srt"))
    print(f"下载 {len(got)} 个字幕")


def cmd_media(bvid: str, kind: str, outdir: str, items: str | None, height: int):
    ytdlp = require("yt-dlp")
    Path(outdir).mkdir(parents=True, exist_ok=True)
    url = f"https://www.bilibili.com/video/{bvid}"
    fmt = "ba/b" if kind == "audio" else f"bv*[height<={height}]+ba/b[height<={height}]"
    cmd = [ytdlp, "-f", fmt, "--no-warnings", "-o", f"{outdir}/P%(playlist_index)02d.%(ext)s"]
    if kind == "video":
        cmd += ["--merge-output-format", "mp4"]
    if items:
        cmd += ["--playlist-items", items]
    cmd.append(url)
    subprocess.run(cmd, check=False)


def main():
    ap = argparse.ArgumentParser(description="B 站视频信息与下载")
    ap.add_argument("action", choices=["info", "subs", "video", "audio"])
    ap.add_argument("bvid")
    ap.add_argument("--cookies", default=None, help="Netscape 格式 cookie 文件（下字幕需要）")
    ap.add_argument("--save", action="store_true", help="subs: 实际下载而非只检查")
    ap.add_argument("-o", "--outdir", default=".")
    ap.add_argument("--items", default=None, help="只处理指定分P，如 1,2,3")
    ap.add_argument("--height", type=int, default=720)
    args = ap.parse_args()

    if args.action == "info":
        cmd_info(args.bvid)
    elif args.action == "subs":
        cmd_subs(args.bvid, args.cookies, args.save, args.outdir, args.items)
    else:
        cmd_media(args.bvid, args.action, args.outdir, args.items, args.height)


if __name__ == "__main__":
    main()
