#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""稿件纪律与计量 —— 一次量完，因为这些指标互相牵制。

单独修一项必然把另一项推出区间，所以这个脚本只有"全量输出"一种模式，
不提供"只查某一项"。

三条语法硬规则（命中即 BLOCK）：
    A  段落主语不用人名        → 命中 `et al.`
    B  引用放从句末尾不放句首  → 行首出现 `[`
    C  破折号清零              → em dash / 双连字符

计量项（越界 WARN，附越界后该做什么）：
    段长、段均、平均句长、从属连词每句、括号每处项数、括号密度、
    四句以上段落的段内句长标准差、段长序列的 max/min

基线可以从范本量出来后用 --baseline 传入 JSON 覆盖默认值：
    {"sent_len": [32, 40], "sub_per_sent": [0.7, 1.0],
     "para_len": [55, 195], "para_mean": [115, 135], "sd_min": 8.5}

用法：
    python3 check_prose_discipline.py 稿件.md
    python3 check_prose_discipline.py 稿件.md --baseline 基线.json --json
    python3 check_prose_discipline.py 范本.txt --measure   # 只量不判，用来立基线
"""

import argparse
import json
import re
import statistics
import sys

BANNED = [
    "groundbreaking", "revolutionary", "delve", "leverage", "pivotal",
    "comprehensive", "meticulous", "it is worth noting",
]

SUBORDINATORS = [
    "which", "who", "whom", "whose", "that", "because", "since", "although",
    "though", "whereas", "while", "so that", "in order that", "unless",
    "if", "when", "where", "after", "before", "as ", "given that",
]

DEFAULT_BASELINE = {
    "sent_len": [32, 40],
    "sub_per_sent": [0.7, 1.0],
    "para_len": [55, 195],
    "para_mean": [115, 135],
    "sd_min": 8.5,
    "paren_items_max": 1,
    "paren_per_kw": 6,
}

ABBREV = r"(?<!\bFig)(?<!\bEq)(?<!\bRef)(?<!\bNo)(?<!\bal)(?<!\bi\.e)(?<!\be\.g)(?<!\bcf)(?<!\bvs)(?<!\bapprox)"
RE_SENT = re.compile(ABBREV + r"(?<=[.!?])\s+(?=[A-Z\[])")
RE_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\-/\.]*")
RE_PAREN = re.compile(r"\(([^()]*)\)")
RE_SKIP = re.compile(r"^\s*(#|\||>|```|---|\*\s|-\s|\d+\.\s)")


def paragraphs(text):
    out = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block or RE_SKIP.match(block):
            continue
        # 去掉行内的段落编号标记，如 "P3  " 或 "**P3**"
        block = re.sub(r"^\**P\d+\**[.:：]?\s*", "", block)
        if len(RE_WORD.findall(block)) < 15:
            continue
        out.append(block)
    return out


def sentences(par):
    return [s.strip() for s in RE_SENT.split(par) if s.strip()]


def count_subordinators(par):
    low = " " + par.lower() + " "
    return sum(len(re.findall(r"\b" + re.escape(w.strip()) + r"\b", low)) for w in SUBORDINATORS)


def paren_items(inner):
    """一个括号里装了几项。分号、顿号、逗号都算分隔；纯引用不计为项。"""
    body = re.sub(r"\[[^\]]*\]", "", inner).strip()
    if not body or re.fullmatch(r"[\d\s,;\-–—p\.]*", body):
        return 0
    return len([x for x in re.split(r"[;；、,，]", body) if x.strip()])


def measure(text):
    pars = paragraphs(text)
    stats = []
    for i, p in enumerate(pars, 1):
        sents = sentences(p)
        wlens = [len(RE_WORD.findall(s)) for s in sents]
        words = sum(wlens)
        stats.append({
            "id": f"P{i}",
            "words": words,
            "sents": len(sents),
            "sent_lens": wlens,
            "sent_mean": round(words / len(sents), 1) if sents else 0,
            "sent_sd": round(statistics.pstdev(wlens), 2) if len(wlens) > 1 else 0.0,
            "subs": count_subordinators(p),
            "sub_per_sent": round(count_subordinators(p) / len(sents), 2) if sents else 0,
            "parens": [paren_items(m) for m in RE_PAREN.findall(p)],
        })
    total_w = sum(s["words"] for s in stats)
    total_s = sum(s["sents"] for s in stats)
    total_sub = sum(s["subs"] for s in stats)
    lens = [s["words"] for s in stats] or [0]
    all_parens = [n for s in stats for n in s["parens"] if n > 0]
    return {
        "paragraphs": stats,
        "n_par": len(stats),
        "words": total_w,
        "sents": total_s,
        "sent_mean": round(total_w / total_s, 2) if total_s else 0,
        "sub_per_sent": round(total_sub / total_s, 2) if total_s else 0,
        "para_mean": round(total_w / len(stats), 1) if stats else 0,
        "para_min": min(lens),
        "para_max": max(lens),
        "para_ratio": round(max(lens) / min(lens), 2) if min(lens) else 0,
        "paren_count": len(all_parens),
        "paren_per_kw": round(len(all_parens) / total_w * 1000, 2) if total_w else 0,
        "paren_max_items": max(all_parens) if all_parens else 0,
    }


def judge(text, m, base):
    issues = []

    def add(level, rule, detail, action=""):
        issues.append({"level": level, "rule": rule, "detail": detail, "action": action})

    for ln, line in enumerate(text.splitlines(), 1):
        if re.search(r"\bet al\.", line):
            add("BLOCK", "A 段落主语不用人名", f"第 {ln} 行出现 et al.",
                "改成以方法/物理对象/约束/论点作主语，人名进方括号")
        if re.match(r"^\s*\[[A-Za-z0-9]", line):
            add("BLOCK", "B 引用不放句首", f"第 {ln} 行以 [ 开头",
                "把引用挪到从句末尾")
    n_dash = len(re.findall(r"—|(?<=\s)--(?=\s)|(?<=\w)\s—\s(?=\w)", text))
    if n_dash:
        add("BLOCK", "C 破折号清零", f"共 {n_dash} 处",
            "逐个二选一：并入主句成为并列成分，或删")
    for w in BANNED:
        if re.search(r"\b" + re.escape(w) + r"\b", text, re.I):
            add("BLOCK", "禁用词", f"出现 {w!r}", "换成具体动作或删")

    lo, hi = base["sent_len"]
    if not (lo <= m["sent_mean"] <= hi):
        add("WARN", "平均句长", f"{m['sent_mean']}（目标 {lo}–{hi}）",
            "偏低用并列合并；偏高拆句。合并只许用冒号、分号、and、but")
    lo, hi = base["sub_per_sent"]
    if not (lo <= m["sub_per_sent"] <= hi):
        act = ("去从属化：A, which is why B → A. B." if m["sub_per_sent"] > hi
               else "并列过度，用冒号或分号合并")
        add("WARN", "从属连词每句", f"{m['sub_per_sent']}（目标 {lo}–{hi}）", act)
    lo, hi = base["para_mean"]
    if not (lo <= m["para_mean"] <= hi):
        add("WARN", "段均词数", f"{m['para_mean']}（目标 {lo}–{hi}）",
            "节长靠段数调节，不靠把某一段写长")

    plo, phi = base["para_len"]
    for s in m["paragraphs"]:
        if s["words"] > phi:
            add("WARN", "单段过长", f"{s['id']} {s['words']} 词（上限 {phi}）", "拆段")
        elif s["words"] < plo:
            add("WARN", "单段过短", f"{s['id']} {s['words']} 词（下限 {plo}）",
                "除非它是末段的因果桥，否则并段")
        if s["sents"] >= 4 and s["sent_sd"] < base["sd_min"]:
            add("WARN", "段内句长无方向", f"{s['id']} 标准差 {s['sent_sd']}（≥{base['sd_min']}）",
                "摆前提用递减、推判断用递增、列条目交替、收尾递减")
        over = [n for n in s["parens"] if n > base["paren_items_max"]]
        if over:
            add("WARN", "括号装多项", f"{s['id']} 有 {len(over)} 处括号各装 {over} 项",
                "每括号只装一项，多项条件留主句用分号分开")

    if m["paren_per_kw"] > base["paren_per_kw"]:
        add("WARN", "括号密度", f"每千词 {m['paren_per_kw']} 处（上限 {base['paren_per_kw']}）",
            "括号是把一个功能位塞进另一句话的主要工具，密度高说明一句多职")
    if m["n_par"] >= 3 and m["para_ratio"] < 2.0:
        add("WARN", "段长序列偏平", f"max/min = {m['para_ratio']}（范本约 3.3）",
            "造一个 60–70 词的短段作为呼吸点")
    return issues


def main():
    ap = argparse.ArgumentParser(description="稿件纪律与计量")
    ap.add_argument("path")
    ap.add_argument("--baseline", help="基线 JSON，覆盖默认区间")
    ap.add_argument("--measure", action="store_true", help="只量不判（用来从范本立基线）")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    text = open(args.path, encoding="utf-8").read()
    base = dict(DEFAULT_BASELINE)
    if args.baseline:
        base.update(json.load(open(args.baseline, encoding="utf-8")))

    m = measure(text)
    if args.measure:
        print(json.dumps(m, ensure_ascii=False, indent=2))
        return 0

    issues = judge(text, m, base)
    verdict = "BLOCK" if any(i["level"] == "BLOCK" for i in issues) else (
        "WARN" if issues else "PASS")

    if args.json:
        print(json.dumps({"verdict": verdict, "metrics": m, "issues": issues},
                         ensure_ascii=False, indent=2))
        return 1 if verdict == "BLOCK" else 0

    print(f"verdict={verdict}")
    print(f"  段数 {m['n_par']}  词数 {m['words']}  句数 {m['sents']}")
    print(f"  段均 {m['para_mean']}（{m['para_min']}–{m['para_max']}，max/min {m['para_ratio']}）")
    print(f"  平均句长 {m['sent_mean']}  从属/句 {m['sub_per_sent']}")
    print(f"  括号 {m['paren_count']} 处，每千词 {m['paren_per_kw']}，单处最多 {m['paren_max_items']} 项")
    for i in issues:
        print(f"  [{i['level']}] {i['rule']}: {i['detail']}")
        if i["action"]:
            print(f"          → {i['action']}")
    return 1 if verdict == "BLOCK" else 0


if __name__ == "__main__":
    sys.exit(main())
