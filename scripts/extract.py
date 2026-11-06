#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 SRT 字幕转成带时间戳的段落文本，并做结构化提取。

用法:
    # SRT -> 段落文本（合并碎句，带 [H:MM:SS] 时间戳）
    python extract.py srt2text subs/*.srt -o text/

    # 每 10 分钟采样一句，用来摸全片骨架
    python extract.py outline text/*.txt --every 600

    # 抓"考点命名句"，用来提取知识点清单
    python extract.py concepts text/*.txt

    # 提取强烈信号句（公式/口诀/结论）
    python extract.py signals text/*.txt
"""
import argparse
import re
import sys
from pathlib import Path

TS = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})")


def _sec(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def _fmt(x):
    x = int(x)
    return f"{x // 3600}:{(x % 3600) // 60:02d}:{x % 60:02d}"


def srt_paragraphs(path: Path, gap: float = 1.5, maxlen: int = 110):
    """把碎句合并成段落：静默 > gap 秒 或 累计 > maxlen 字就断段"""
    items = []
    for blk in re.split(r"\n\s*\n", path.read_text(encoding="utf-8", errors="ignore")):
        m = TS.search(blk)
        if not m:
            continue
        st, en = _sec(*m.groups()[:4]), _sec(*m.groups()[4:])
        body = TS.sub("", blk).strip()
        body = re.sub(r"^\d+\s*$", "", body, flags=re.M).replace("\n", "").strip()
        if body:
            items.append((st, en, body))

    paras, cur, cs, le = [], [], None, None
    for s, e, x in items:
        if le is not None and (s - le > gap or sum(len(c) for c in cur) > maxlen):
            paras.append((cs, le, "".join(cur)))
            cur, cs = [], None
        if cs is None:
            cs = s
        cur.append(x)
        le = e
    if cur:
        paras.append((cs, le, "".join(cur)))
    return paras


def cmd_srt2text(files, outdir):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    for f in files:
        p = Path(f)
        paras = srt_paragraphs(p)
        tag = p.stem.split(".")[0]
        text = "\n\n".join(f"[{_fmt(s)}] {y}" for s, _, y in paras)
        (out / f"{tag}.txt").write_text(text, encoding="utf-8")
        chars = sum(len(y) for _, _, y in paras)
        print(f"{tag}: {len(paras)} 段, {chars:,} 字")


def _iter_lines(files):
    for f in files:
        for line in Path(f).read_text(encoding="utf-8").split("\n\n"):
            m = re.match(r"\[(\d{2,3}:\d{2}(?::\d{2})?)\]\s*(.+)", line.strip())
            if m:
                yield Path(f).stem, m.group(1), m.group(2)


def cmd_outline(files, every: int):
    cur_file, marks = None, set()
    for fname, t, text in _iter_lines(files):
        if fname != cur_file:
            print(f"\n########## {fname} ##########")
            cur_file, marks = fname, set()
        parts = [int(x) for x in t.split(":")]
        sec = parts[0] * 3600 + parts[1] * 60 + (parts[2] if len(parts) > 2 else 0)
        k = sec // every
        if k not in marks:
            marks.add(k)
            print(f"{t} | {text[:80]}")


CONCEPT_PATS = [
    r"第[一二三四五六七八九十]+[个种类步]",
    r"就叫", r"这叫做", r"这个叫", r"我们称", r"称为",
    r"考点是", r"题型是", r"规律是", r"方法是",
]


def cmd_concepts(files, window: int = 30):
    pat = re.compile("|".join(CONCEPT_PATS))
    for fname, t, text in _iter_lines(files):
        if pat.search(text[:window]) and 15 < len(text) < 180:
            print(f"[{fname} {t}] {text[:110]}")


SIGNAL_PATS = ["口诀", "公式", "记住", "结论", "本质", "力度", "优先", "注意", "陷阱", "区分"]


def cmd_signals(files):
    for fname, t, text in _iter_lines(files):
        if any(k in text for k in SIGNAL_PATS) and len(text) > 25:
            print(f"[{fname} {t}] {text[:120]}")


def main():
    ap = argparse.ArgumentParser(description="字幕结构化提取")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("srt2text")
    p1.add_argument("files", nargs="+")
    p1.add_argument("-o", "--outdir", default="text")

    p2 = sub.add_parser("outline")
    p2.add_argument("files", nargs="+")
    p2.add_argument("--every", type=int, default=600, help="采样间隔秒数")

    p3 = sub.add_parser("concepts")
    p3.add_argument("files", nargs="+")

    p4 = sub.add_parser("signals")
    p4.add_argument("files", nargs="+")

    a = ap.parse_args()
    if a.cmd == "srt2text":
        cmd_srt2text(a.files, a.outdir)
    elif a.cmd == "outline":
        cmd_outline(a.files, a.every)
    elif a.cmd == "concepts":
        cmd_concepts(a.files)
    elif a.cmd == "signals":
        cmd_signals(a.files)


if __name__ == "__main__":
    main()
