#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Markdown → 单页 HTML（带样式，可直接打印 / 离线阅读）。

用法:
    python build.py notes.md -o notes.html
    python build.py notes.md --title "判断推理学习总结"

依赖: pip install markdown
"""
import argparse
import sys
from pathlib import Path

try:
    import markdown
except ImportError:
    sys.exit("需要 markdown: pip install markdown")

CSS = """
:root{--ink:#1f2328;--sub:#5b6470;--line:#e3e8ef;--accent:#b5382f;--soft:#fdf3f1;--code:#f6f8fa}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:var(--ink);
 font-family:"PingFang SC","Microsoft YaHei",system-ui,-apple-system,sans-serif;
 font-size:16px;line-height:1.85}
.wrap{max-width:920px;margin:0 auto;padding:48px 28px 120px}
h1{font-size:2em;line-height:1.35;margin:0 0 .5em}
h2{font-size:1.42em;margin:2.4em 0 .9em;padding-bottom:.3em;
 border-bottom:2px solid var(--accent);display:inline-block}
h3{font-size:1.12em;margin:1.9em 0 .6em}
h3::before{content:"";display:inline-block;width:4px;height:.95em;
 background:var(--accent);margin-right:.5em;vertical-align:-.1em;border-radius:2px}
blockquote{margin:1.2em 0;padding:.8em 1.1em;background:var(--soft);
 border-left:3px solid var(--accent);color:#6b3b36;border-radius:0 6px 6px 0}
blockquote p{margin:.2em 0}
pre{background:var(--code);border:1px solid var(--line);border-radius:8px;
 padding:14px 16px;overflow-x:auto;font-size:.92em;line-height:1.7}
code{font-family:Consolas,Menlo,monospace;font-size:.94em}
p code,li code,td code{background:var(--code);padding:.12em .38em;border-radius:4px}
table{border-collapse:collapse;width:100%;margin:1.2em 0;font-size:.94em}
th,td{border:1px solid var(--line);padding:9px 12px;text-align:left;vertical-align:top}
th{background:#fafbfc;font-weight:600;color:var(--sub)}
tr:nth-child(even) td{background:#fcfdfe}
td:first-child{white-space:nowrap}
img{display:block;max-width:100%;margin:1.4em auto;border:1px solid var(--line);
 border-radius:8px;box-shadow:0 2px 10px rgba(20,30,50,.06)}
hr{border:0;border-top:1px solid var(--line);margin:2.6em 0}
ul,ol{padding-left:1.4em} li{margin:.28em 0}
strong{font-weight:650} a{color:var(--accent);word-break:break-all}
@media print{
 .wrap{max-width:none;padding:0}
 h2{page-break-after:avoid}
 img,pre,table,blockquote{page-break-inside:avoid}
 img{box-shadow:none}
}
"""


def main():
    ap = argparse.ArgumentParser(description="Markdown → HTML")
    ap.add_argument("md")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--title", default=None)
    args = ap.parse_args()

    src = Path(args.md)
    text = src.read_text(encoding="utf-8")
    body = markdown.markdown(text, extensions=["extra", "tables", "fenced_code", "sane_lists"])

    title = args.title
    if not title:
        first = next((l for l in text.splitlines() if l.startswith("# ")), "")
        title = first.lstrip("# ").strip() or src.stem

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>{CSS}</style></head>
<body><div class="wrap">
{body}
</div></body></html>"""

    out = Path(args.out or src.with_suffix(".html"))
    out.write_text(html, encoding="utf-8")

    n_img = html.count("<img")
    n_tbl = html.count("<table")
    print(f"生成 {out.name}  {len(html):,} 字符 ｜ 图 {n_img} ｜ 表 {n_tbl}")

    # 校验本地图片与链接是否存在
    import re
    base = out.parent
    miss = [s for s in re.findall(r'src="([^"]+)"', html)
            if not s.startswith("http") and not (base / s).exists()]
    if miss:
        print(f"⚠ {len(miss)} 个图片路径不存在：")
        for m in miss[:5]:
            print("   ", m)


if __name__ == "__main__":
    main()
