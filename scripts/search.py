#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""搜索 B 站视频，输出结构化结果。

用法:
    python search.py "判断推理 系统课" -n 30 --out result.json
    python search.py "关键词" --profile ~/.bili_profile    # 用已登录 profile

依赖: pip install playwright && playwright install chromium
"""
import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    sys.exit("需要 playwright: pip install playwright && playwright install chromium")


async def search(keyword: str, profile: str | None, limit: int, headless: bool) -> list:
    async with async_playwright() as p:
        kwargs = {"channel": "chrome", "headless": headless,
                  "args": ["--disable-blink-features=AutomationControlled"]}
        if profile:
            ctx = await p.chromium.launch_persistent_context(str(Path(profile).expanduser()), **kwargs)
        else:
            browser = await p.chromium.launch(**{k: v for k, v in kwargs.items() if k != "args"})
            ctx = await browser.new_context()

        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        url = f"https://search.bilibili.com/all?keyword={keyword}&order=click"
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)

        cards = await page.evaluate("""() => {
            const out = [];
            document.querySelectorAll('.bili-video-card').forEach(c => {
                const a = c.querySelector('a[href*="/video/BV"]');
                const t = c.querySelector('.bili-video-card__info--tit');
                const d = c.querySelector('.bili-video-card__stats__duration');
                const p = c.querySelector('.bili-video-card__stats--item span');
                const u = c.querySelector('.bili-video-card__info--author');
                if (a && t) out.push({
                    bvid: (a.href.match(/BV[0-9A-Za-z]+/) || [''])[0],
                    title: t.innerText.trim(),
                    duration: d ? d.innerText.trim() : '',
                    play: p ? p.innerText.trim() : '',
                    up: u ? u.innerText.trim() : ''
                });
            });
            return out;
        }""")
        await ctx.close()
        return cards[:limit]


def main():
    ap = argparse.ArgumentParser(description="搜索 B 站视频")
    ap.add_argument("keyword", help="搜索关键词")
    ap.add_argument("-n", "--limit", type=int, default=30)
    ap.add_argument("--profile", default=None,
                    help="Playwright 持久化 profile 路径（带登录态，可下字幕）")
    ap.add_argument("--out", default=None, help="结果 JSON 输出路径")
    ap.add_argument("--show", action="store_true", help="显示浏览器窗口")
    args = ap.parse_args()

    cards = asyncio.run(search(args.keyword, args.profile, args.limit, not args.show))
    print(f"抓到 {len(cards)} 条\n")
    for i, c in enumerate(cards, 1):
        print(f"{i:2d}. [{c['duration']:>9}] 播放{c['play']:>8} | {c['bvid']} | {c['title'][:48]}")

    if args.out:
        Path(args.out).write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n已写出 {args.out}")


if __name__ == "__main__":
    main()
