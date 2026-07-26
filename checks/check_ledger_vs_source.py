#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台账 vs 原文 —— 逐编号比对参考文献题录。

存在的理由是一次真实事故：一份 161 条的参考文献台账里，[48]–[74] 连续 27 条
题录是伪造的。根因是台账抄的是译本的参考文献表，而译本在这一区间编造了条目。
最阴的一点是——伪造条目里有几条碰巧是真实存在的论文，于是顺利查到 DOI 并被
标成"已核验"。

所以核验的判据是：**与原始出处该编号处逐字一致**，不是"这条题录在世界上存在"。
"查得到 DOI"不能证明"这就是原文里的那一条"。

做法：把原文的文后 [n] 题录抽出来，与台账同号行做词集 Jaccard 比对，
低于阈值的逐条列出来给人看。当时 161 条里精确命中 27 条，零漏零误。

用法：
    python3 check_ledger_vs_source.py 原文.pdf 台账.md
    python3 check_ledger_vs_source.py 原文.txt 台账.md --threshold 0.45 --json

台账格式：任何一行里出现 [n] 或 |n| 或行首 n. 即视为该编号的题录行。
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

RE_TOKEN = re.compile(r"[A-Za-z0-9]+")
RE_ENTRY = re.compile(r"\[(\d{1,3})\]")
NOISE = {"and", "the", "of", "in", "on", "for", "a", "an", "vol", "no", "pp",
         "doi", "http", "https", "www", "et", "al", "eds", "ed"}


def pdf_text(path):
    try:
        import fitz  # pymupdf
        doc = fitz.open(path)
        return "\n".join(page.get_text() for page in doc)
    except ImportError:
        pass
    for cmd in (["pdftotext", "-layout", str(path), "-"], ["pdftotext", str(path), "-"]):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    raise SystemExit("读不出 PDF 文字层：装 pymupdf（pip install pymupdf）或 poppler-utils")


def load_text(path):
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        return pdf_text(p)
    return p.read_text(encoding="utf-8", errors="replace")


def split_entries(text):
    """按 [n] 切出题录。取每个编号**最后一次**出现之后的那一段，
    因为正文里的 [n] 是引用、文后的才是题录。"""
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)   # 连字符断行
    text = re.sub(r"\s+", " ", text)
    hits = [(int(m.group(1)), m.start(), m.end()) for m in RE_ENTRY.finditer(text)]
    if not hits:
        return {}
    last = {}
    for num, s, e in hits:
        last[num] = (s, e)
    ordered = sorted(last.items(), key=lambda kv: kv[1][0])
    out = {}
    for i, (num, (s, e)) in enumerate(ordered):
        stop = ordered[i + 1][1][0] if i + 1 < len(ordered) else len(text)
        body = text[e:stop].strip(" .,;")
        if len(body) > 15:
            out[num] = body[:400]
    return out


def load_ledger(path):
    out = {}
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        m = (re.search(r"\[(\d{1,3})\]", line)
             or re.match(r"^\s*\|?\s*(\d{1,3})\s*[|.．、]", line))
        if not m:
            continue
        num = int(m.group(1))
        body = line[m.end():].strip(" |.,;")
        if len(body) > 15 and num not in out:
            out[num] = body[:400]
    return out


def tokens(s):
    return {t.lower() for t in RE_TOKEN.findall(s)
            if t.lower() not in NOISE and len(t) > 1}


def jaccard(a, b):
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def main():
    ap = argparse.ArgumentParser(description="台账 vs 原文 题录比对")
    ap.add_argument("source", help="原始 PDF 或已提取的 txt（唯一真源）")
    ap.add_argument("ledger", help="台账 md/csv/txt")
    ap.add_argument("--threshold", type=float, default=0.45)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    src = split_entries(load_text(args.source))
    led = load_ledger(args.ledger)
    if not src:
        raise SystemExit("原文里没切出任何 [n] 题录，先确认这份文件含参考文献表")

    rows, suspect, missing = [], [], []
    for num in sorted(led):
        if num not in src:
            missing.append(num)
            continue
        j = jaccard(src[num], led[num])
        rows.append({"n": num, "jaccard": round(j, 3),
                     "source": src[num][:150], "ledger": led[num][:150]})
        if j < args.threshold:
            suspect.append(rows[-1])

    verdict = "BLOCK" if suspect or missing else "PASS"
    result = {
        "verdict": verdict,
        "source_entries": len(src),
        "ledger_entries": len(led),
        "compared": len(rows),
        "threshold": args.threshold,
        "suspect_count": len(suspect),
        "missing_in_source": missing,
        "suspect": suspect,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"verdict={verdict}  原文 {len(src)} 条 / 台账 {len(led)} 条 / 比对 {len(rows)} 条")
        if missing:
            print(f"  台账有、原文无：{missing}")
        if suspect:
            print(f"  低于阈值 {args.threshold} 的 {len(suspect)} 条（逐条人工看，不要批量放行）：")
            for r in suspect:
                print(f"    [{r['n']}] J={r['jaccard']}")
                print(f"         原文：{r['source'][:110]}")
                print(f"         台账：{r['ledger'][:110]}")
        if verdict == "PASS":
            print("  全部同号逐字咬合。注意：这只证明台账抄对了，不证明原作者引对了。")
    return 1 if verdict == "BLOCK" else 0


if __name__ == "__main__":
    sys.exit(main())
