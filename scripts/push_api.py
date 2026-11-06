# -*- coding: utf-8 -*-
"""通过 GitHub Contents API 上传文件。

什么时候用：git push 连不上 github.com:443，但 api.github.com 能直连时。
这是国内网络的常见情况——git 走 443 被墙，而 api 域名没被墙。

用法:
    export GH_TOKEN=ghp_xxx
    python scripts/push_api.py              # 用脚本里的 REPO 和 FILES
    GH_REPO=user/repo python scripts/push_api.py

注意: token 用完请及时撤销，别提交到版本库。
"""
import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

TOKEN = os.environ.get("GH_TOKEN", "")
REPO = os.environ.get("GH_REPO", "mj5622453-hash/bili-course-to-notes")
API = f"https://api.github.com/repos/{REPO}/contents"
ROOT = Path(__file__).resolve().parent.parent  # scripts/ 的上一级

FILES = [
    ".gitignore", "LICENSE", "README.md", "SKILL.md",
    "scripts/search.py", "scripts/fetch.py", "scripts/extract.py",
    "scripts/frames.py", "scripts/cut.py", "scripts/build.py", "scripts/check.py",
]

# 不走任何代理（api.github.com 直连可达）
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def req(method, url, data=None):
    r = urllib.request.Request(url, method=method, data=data)
    r.add_header("Authorization", f"Bearer {TOKEN}")
    r.add_header("Accept", "application/vnd.github+json")
    r.add_header("User-Agent", "bili-course-to-notes-publisher")
    if data:
        r.add_header("Content-Type", "application/json")
    return opener.open(r, timeout=60)


def get_sha(path):
    try:
        with req("GET", f"{API}/{path}") as r:
            return json.loads(r.read().decode())["sha"]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def put_file(path, sha, first: bool):
    raw = (ROOT / path).read_bytes()
    body = {
        "message": f"{'feat: 初始提交' if first else 'chore: 更新'} {path}",
        "content": base64.b64encode(raw).decode(),
    }
    if sha:
        body["sha"] = sha
    data = json.dumps(body).encode()
    with req("PUT", f"{API}/{path}", data) as r:
        return json.loads(r.read().decode())["content"]["path"]


ok, fail = [], []
for i, f in enumerate(FILES):
    try:
        sha = get_sha(f)
        p = put_file(f, sha, i == 0)
        size = (ROOT / f).stat().st_size
        print(f"✓ {f:<24} {size:>7,} B  {'更新' if sha else '新建'}")
        ok.append(f)
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:200]
        print(f"✗ {f:<24} HTTP {e.code} {detail}")
        fail.append(f)
    except Exception as e:
        print(f"✗ {f:<24} {type(e).__name__}: {e}")
        fail.append(f)

print(f"\n成功 {len(ok)} / {len(FILES)}")
if fail:
    print("失败:", fail)
