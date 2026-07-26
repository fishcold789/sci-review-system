#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""写盘回读 —— 最便宜的一道门，也是被跳过次数最多的一道。

已发生过的两次事故：
  · 一份文档落盘时被写成了一个网络错误页，没人发现；
  · 一次险些用陈旧快照覆盖掉后续新增内容。

两件事都不需要判断力，只需要一次机械检查。**每次写盘后跑一遍。**

用法：
    python3 check_writeback.py 产物.md
    python3 check_writeback.py 产物.md --min-bytes 2000 --contains "证据卡" --contains "P7"
    python3 check_writeback.py 产物.md --prev-sha <上一版sha256>   # 防"写了等于没写"
    python3 check_writeback.py 产物.md --json

退出码：0 = PASS，1 = BLOCK。
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

# 结构标记：真正的错误页第一个字节就是它，所以只看开头 300 字。
# 放宽到 2000 字会把"源码里写着这个正则"的本文件自己判成网页——真发生过。
HTML_MARKERS = r"<!doctype html|<html[\s>]|<body[\s>]|<head[\s>]"
# 文字标记：只有在"这份文件本身像网页"或"文件很小且标记出现在开头"时才算数。
# 否则一份正常讲解文档只要提到 Cloudflare 就会被误判——这条误报真的发生过。
TEXT_MARKERS = [
    "403 forbidden", "404 not found", "access denied", "just a moment",
    "are you a robot", "checking your browser", "请开启 javascript",
    "enable javascript", "sign in to continue",
]


def main():
    ap = argparse.ArgumentParser(description="写盘后回读核对")
    ap.add_argument("path")
    ap.add_argument("--min-bytes", type=int, default=1)
    ap.add_argument("--contains", action="append", default=[],
                    help="必须出现的字符串，可重复")
    ap.add_argument("--prev-sha", help="上一版 sha256；相同则说明这次写盘没生效")
    ap.add_argument("--head", type=int, default=200)
    ap.add_argument("--tail", type=int, default=200)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    issues = []
    p = Path(args.path)
    if not p.exists():
        print(json.dumps({"verdict": "BLOCK", "issues": ["文件不存在"]},
                         ensure_ascii=False))
        return 1

    raw = p.read_bytes()
    size = len(raw)
    sha = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8", errors="replace")
    head, tail = text[: args.head], text[-args.tail:]

    if size < args.min_bytes:
        issues.append(f"字节数 {size} < 期望 {args.min_bytes}")
    looks_html = bool(re.search(HTML_MARKERS, text[:300], re.I))
    head_low = text[:600].lower()
    if looks_html and p.suffix.lower() not in {".html", ".htm", ".xml", ".svg"}:
        issues.append("疑似落成了网页：文件开头是 HTML 结构标记")
    else:
        hit = next((m for m in TEXT_MARKERS if m in head_low), None)
        if hit and size < 5000:
            issues.append(f"疑似落成了错误页：开头命中 {hit!r}，且文件很小（{size} 字节）")
    if p.suffix.lower() in {".md", ".txt", ".py", ".json", ".csv"}:
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            issues.append(f"不是合法 UTF-8：{exc}")
    for s in args.contains:
        if s not in text:
            issues.append(f"缺少必须出现的内容：{s!r}")
    if args.prev_sha and args.prev_sha.strip().lower() == sha:
        issues.append("sha256 与上一版相同——这次写盘没有生效")

    verdict = "BLOCK" if issues else "PASS"
    result = {"verdict": verdict, "path": str(p), "bytes": size, "sha256": sha,
              "head": head, "tail": tail, "issues": issues}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"verdict={verdict}  {size} bytes  sha256={sha[:16]}…")
        print("--- 头 ---")
        print(head)
        print("--- 尾 ---")
        print(tail)
        for i in issues:
            print(f"  [BLOCK] {i}")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
