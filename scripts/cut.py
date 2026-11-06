#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按考点时间轴把课程切成片段，切点吸附到字幕句子边界。

用法:
    # 1. 写一份时间轴 clips.json
    [
      {"part": "P01", "start": 2375, "end": 3780, "title": "01_位置规律-平移"},
      {"part": "P01", "start": 3780, "end": 4740, "title": "02_宫格型平移"}
    ]

    # 2. 切（自动细分超过 --max-dur 的片段，切点吸附句子边界）
    python cut.py clips.json --video-dir video/ --text-dir text/ --out clips/

视频文件命名需与 part 对应：video/P01.mp4
text 目录放 extract.py srt2text 的产物：text/P01.txt（用于取句子边界）

依赖: ffmpeg
"""
import argparse
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

PREROLL = 25   # 起点提前秒数，避免从半句话开始
TAIL = 8       # 终点后留秒数


def ffmpeg() -> str:
    p = shutil.which("ffmpeg")
    if not p:
        raise SystemExit("找不到 ffmpeg")
    return p


def sentence_marks(text_file: Path) -> list[int]:
    """该分P所有句子起始时刻（秒）"""
    if not text_file.exists():
        return []
    out = []
    for line in text_file.read_text(encoding="utf-8").split("\n\n"):
        m = re.match(r"\[(\d+):(\d{2}):(\d{2})\]", line.strip())
        if m:
            out.append(int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)))
    return sorted(set(out))


def snap(t: int, marks: list[int], lo: int, hi: int, tol: int = 90) -> int:
    """把切点吸附到最近的句子起始，且落在 (lo, hi) 内"""
    cand = [x for x in marks if lo < x < hi]
    if not cand:
        return t
    best = min(cand, key=lambda x: abs(x - t))
    return best if abs(best - t) <= tol else t


def cut_one(video: Path, s: int, e: int, dst: Path) -> bool:
    """-c copy 无损快切。会从最近关键帧起切，反而有利于边界完整。"""
    cmd = [ffmpeg(), "-hide_banner", "-loglevel", "error",
           "-ss", str(s), "-to", str(e), "-i", str(video),
           "-c", "copy", "-avoid_negative_ts", "make_zero", "-y", str(dst)]
    subprocess.run(cmd, check=False)
    return dst.exists() and dst.stat().st_size > 10240


def main():
    ap = argparse.ArgumentParser(description="按考点切片")
    ap.add_argument("timeline", help="clips.json")
    ap.add_argument("--video-dir", default="video")
    ap.add_argument("--text-dir", default="text", help="字幕文本目录（取句子边界）")
    ap.add_argument("-o", "--out", default="clips")
    ap.add_argument("--max-dur", type=int, default=1500, help="超过此长度自动细分")
    ap.add_argument("--target", type=int, default=720, help="细分后的目标时长")
    args = ap.parse_args()

    items = json.loads(Path(args.timeline).read_text(encoding="utf-8"))
    vd, td, od = Path(args.video_dir), Path(args.text_dir), Path(args.out)
    od.mkdir(parents=True, exist_ok=True)

    marks_cache, index, n_split = {}, [], 0
    for it in items:
        part, s, e, title = it["part"], int(it["start"]), int(it["end"]), it["title"]
        video = vd / f"{part}.mp4"
        if not video.exists():
            print(f"跳过（缺视频）{part}")
            continue

        s = max(0, s - PREROLL)
        e = e + TAIL
        dur = e - s

        if dur <= args.max_dur:
            segs = [(s, e, title)]
        else:
            if part not in marks_cache:
                marks_cache[part] = sentence_marks(td / f"{part}.txt")
            marks = marks_cache[part]
            k = max(2, math.ceil(dur / args.target))
            cuts = [s]
            for i in range(1, k):
                t = s + dur * i // k
                cuts.append(snap(t, marks, cuts[-1] + 120, e - 60))
            cuts.append(e)
            cuts = sorted(set(cuts))
            base = title.split("_")[0]
            rest = title.split("_", 1)[1] if "_" in title else ""
            segs = [(cuts[i], cuts[i + 1], f"{base}-{i + 1}_{rest}")
                    for i in range(len(cuts) - 1) if cuts[i + 1] - cuts[i] >= 60]
            n_split += 1

        for a, b, name in segs:
            dst = od / f"{name}.mp4"
            if cut_one(video, a, b, dst):
                mb = dst.stat().st_size / 1048576
                print(f"✓ {name}  {a // 60}:{a % 60:02d}–{b // 60}:{b % 60:02d}  {mb:.0f}MB")
                index.append({"file": dst.name, "part": part, "start": a, "end": b,
                              "dur": b - a, "title": name})
            else:
                print(f"✗ {name} 失败")

    (od / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n共 {len(index)} 个片段（其中 {n_split} 组做了细分）")


if __name__ == "__main__":
    main()
