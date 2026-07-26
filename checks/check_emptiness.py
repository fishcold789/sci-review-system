#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""空话检测 —— 判断一份"形状正确"的材料是不是没有内容。

它拦的不是措辞难看，是**一句话里没有任何可以被推翻的东西**。
三条判据，全部与学科无关（不出现任何领域名词）：

  1. 可证伪成分：每条主张至少带一个 量 / 界 / 名
       量 = 数字（有无单位皆可）
       界 = 边界或条件结构（只、仅、不超过、上界、当…时、失效、depends on、unless…）
       名 = 具体指名的东西（缩写、含数字的标识、连字符技术词、中文里嵌的拉丁词）
  2. 实词量：把停用词和评价性空词删掉之后，还得剩下东西
  3. 证据—主张咬合：一条主张与它引的证据之间，实词重叠不得为零

用法：
    python3 check_emptiness.py bundle.json          # 证据包（JSON）
    python3 check_emptiness.py --text 稿件.md        # 散文（按段落判，只跑判据 1、2）
    python3 check_emptiness.py bundle.json --json    # 机器可读输出

退出码：0 = PASS，1 = BLOCK，2 = 用法错误。
"""

import argparse
import json
import re
import sys

# ---------------------------------------------------------------- 词表
# 只放"逻辑/计量结构词"与"评价性空词"，不放任何学科名词。

BOUND_ZH = [
    "只有", "只能", "只在", "仅在", "仅当", "仅限", "唯有", "至多", "至少",
    "不超过", "不低于", "上界", "下界", "上限", "下限", "阈值", "量级",
    "当", "若", "如果", "除非", "否则", "前提", "条件下", "取决于", "依赖于",
    "失效", "不再", "无法", "不能", "做不到", "反例", "例外",
    "大于", "小于", "高于", "低于", "优于", "劣于", "快于", "慢于",
    "更低", "更高", "降低", "提高", "减小", "增大", "限于", "相同", "不同",
    "一致", "可比", "匹配", "相对于", "相比", "同一",
]
BOUND_EN = [
    "only", "unless", "otherwise", "provided that", "requires", "required",
    "fails", "fail", "cannot", "does not", "do not", "no longer",
    "depends on", "depend on", "differs", "differ", "changes when",
    "at most", "at least", "more than", "less than", "greater than",
    "lower than", "upper bound", "lower bound", "threshold", "bounded",
    "when ", "if ", "under ", "except",
    "lower", "higher", "smaller", "larger", "better", "worse", "reduced",
    "increased", "decreased", "improved", "limited to", "restricted to",
    "confined to", "identical", "comparable", "matched", "relative to",
    "compared", "same ",
]

# 评价性空词：删掉之后句子不损失任何可核对的信息
VACUOUS_ZH = [
    "长足", "显著", "重要", "巨大", "广泛", "深入", "丰富", "良好", "优异",
    "有效地", "相关", "一定", "较好", "较为", "进一步", "日益", "不断",
    "众多", "大量", "诸多", "各种", "多种", "若干", "领域", "方面", "情况",
    "进展", "取得", "有所", "进行", "开展", "具有", "存在", "方法", "研究",
    "近年来", "目前", "当前", "国内外", "本文", "该", "相应",
]
VACUOUS_EN = [
    "significant", "significantly", "remarkable", "extensive", "various",
    "numerous", "considerable", "important", "relevant", "progress",
    "recent years", "in general", "a lot of", "many kinds", "certain",
    "comprehensive", "novel", "advanced", "state of the art",
]

STOP_ZH = set("的了和与及或在是有为对于中上下这那其之着地得也都很就还又并且而但因所以被把从到与个种些")
STOP_EN = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are",
    "was", "were", "be", "been", "by", "with", "that", "this", "these", "those",
    "it", "its", "as", "at", "from", "than", "then", "after", "before", "both",
    "across", "we", "our", "their", "has", "have", "had", "which", "there",
}

CJK = r"一-鿿"
RE_CJK = re.compile(f"[{CJK}]")
RE_NUM = re.compile(r"\d")
RE_LATIN_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9\-/]*")
RE_ACRONYM = re.compile(r"\b[A-Z]{2,}\b")
RE_HAS_DIGIT_TOKEN = re.compile(r"\b\w*\d\w*\b")
RE_HYPHEN_TECH = re.compile(r"\b[A-Za-z]+-[A-Za-z]+\b")


def is_cjk_text(s):
    return len(RE_CJK.findall(s)) >= max(2, len(s) * 0.2)


# ---------------------------------------------------------------- 判据 1
def falsifiable_parts(text):
    """返回这条记录带了哪些可证伪成分：quantity / bound / name。"""
    parts = []
    low = text.lower()
    if RE_NUM.search(text):
        parts.append("量")
    if any(w in text for w in BOUND_ZH) or any(w in low for w in BOUND_EN):
        parts.append("界")
    name = (
        RE_ACRONYM.search(text)
        or RE_HAS_DIGIT_TOKEN.search(text)
        or RE_HYPHEN_TECH.search(text)
        or (is_cjk_text(text) and RE_LATIN_TOKEN.search(text))
    )
    if name:
        parts.append("名")
    return parts


# ---------------------------------------------------------------- 判据 2
def content_tokens(text):
    """删掉停用词、评价性空词、边界标记之后剩下的实词。

    返回 (中文剩余字, 英文剩余词)。两者阈值不同：一个汉字承载的信息比
    一个英文词少，所以中文门槛更高。混排时任一侧达标即可。
    """
    s = text
    for w in VACUOUS_ZH + BOUND_ZH:
        s = s.replace(w, " ")
    low_removed = s
    for w in sorted(VACUOUS_EN + BOUND_EN, key=len, reverse=True):
        low_removed = re.sub(re.escape(w), " ", low_removed, flags=re.I)
    s = low_removed
    zh = [c for c in RE_CJK.findall(s) if c not in STOP_ZH]
    en = [t.lower() for t in RE_LATIN_TOKEN.findall(s)
          if t.lower() not in STOP_EN and len(t) > 1]
    return zh, en


def content_size(text):
    zh, en = content_tokens(text)
    return len(zh) + len(en)


def enough_content(text, zh_min, en_min):
    zh, en = content_tokens(text)
    return len(zh) >= zh_min or len(en) >= en_min, len(zh), len(en)


# ---------------------------------------------------------------- 判据 3
def overlap(a, b):
    za, ea = content_tokens(a)
    zb, eb = content_tokens(b)
    return len((set(za) | set(ea)) & (set(zb) | set(eb)))


# ---------------------------------------------------------------- 检查主体
class Report:
    def __init__(self):
        self.issues = []

    def add(self, level, where, rule, detail):
        self.issues.append(
            {"level": level, "where": where, "rule": rule, "detail": detail}
        )

    @property
    def blocked(self):
        return any(i["level"] == "BLOCK" for i in self.issues)


def check_record(rep, where, text, zh_min, en_min, need_falsifiable=True):
    text = (text or "").strip()
    if not text:
        rep.add("BLOCK", where, "非空", "字段为空")
        return
    ok, nz, ne = enough_content(text, zh_min, en_min)
    if not ok:
        rep.add(
            "BLOCK", where, "实词量",
            f"删掉停用词与评价性空词后只剩 中文{nz}字/英文{ne}词"
            f"（要求 ≥{zh_min}字 或 ≥{en_min}词）：{text!r}",
        )
    if need_falsifiable:
        parts = falsifiable_parts(text)
        if not parts:
            rep.add(
                "BLOCK", where, "可证伪成分",
                f"既没有量、也没有界、也没有名，无法被推翻：{text!r}",
            )


def check_bundle(data):
    rep = Report()
    ev_by_id = {e.get("evidence_id"): e for e in data.get("evidence", [])}

    for e in data.get("evidence", []):
        where = f"evidence/{e.get('evidence_id')}"
        check_record(rep, where + ".summary", e.get("summary", ""), 5, 3)
        if not (e.get("anchor_id") or e.get("anchor")):
            rep.add("BLOCK", where, "锚点", "证据没有可定位到页/图/表的锚点")

    for c in data.get("claims", []):
        cid = c.get("claim_id")
        where = f"claims/{cid}"
        text = c.get("text", "")
        check_record(rep, where + ".text", text, 6, 4)

        if RE_NUM.search(text):
            conds = c.get("conditions") or []
            has_inline = any(w in text for w in BOUND_ZH) or any(
                w in text.lower() for w in BOUND_EN
            )
            if not conds and not has_inline:
                rep.add(
                    "BLOCK", where, "数字带条件",
                    f"出现数字但既无 conditions 字段也无条件结构：{text!r}",
                )

        eids = c.get("evidence_ids") or []
        if not eids:
            rep.add("BLOCK", where, "证据覆盖", "主张没有挂任何证据")
        for eid in eids:
            ev = ev_by_id.get(eid)
            if ev is None:
                rep.add("BLOCK", where, "证据存在", f"引用了不存在的证据 {eid}")
                continue
            ov = overlap(text, ev.get("summary", ""))
            if ov == 0:
                rep.add(
                    "BLOCK", where, "证据咬合",
                    f"与 {eid} 的实词重叠为 0，证据没有在支撑这条主张",
                )

    for s in data.get("syntheses", []):
        sid = s.get("synthesis_id")
        where = f"syntheses/{sid}"
        for field in ("agreements", "conflicts"):
            items = s.get(field) or []
            if not items:
                rep.add("BLOCK", where, "综合非空", f"{field} 为空")
            for i, item in enumerate(items):
                check_record(rep, f"{where}.{field}[{i}]", item, 4, 3)
        for field in ("boundary", "conflict_assessment"):
            if field in s:
                check_record(rep, f"{where}.{field}", s.get(field, ""), 4, 3)
        if len(s.get("source_ids") or []) < 2:
            rep.add("BLOCK", where, "综合来源", "综合块少于两个来源，不是综合")

    return rep


def check_prose(text):
    rep = Report()
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    for i, p in enumerate(paras, 1):
        if p.startswith(("#", "|", ">", "```", "-", "*")):
            continue
        if len(p) < 20:
            continue
        where = f"段落 P{i}"
        parts = falsifiable_parts(p)
        if not parts:
            rep.add("BLOCK", where, "可证伪成分", f"整段没有量/界/名：{p[:60]}…")
        vac = sum(p.count(w) for w in VACUOUS_ZH) + sum(
            len(re.findall(re.escape(w), p, re.I)) for w in VACUOUS_EN
        )
        size = max(1, content_size(p))
        if vac / size > 0.25:
            rep.add(
                "WARN", where, "空词密度",
                f"评价性空词 {vac} 处 / 实词 {size}，比值 {vac/size:.2f} > 0.25",
            )
    return rep


def main():
    ap = argparse.ArgumentParser(description="空话检测")
    ap.add_argument("path", help="证据包 JSON，或配合 --text 时的稿件路径")
    ap.add_argument("--text", action="store_true", help="按散文检查（Markdown/txt）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    raw = open(args.path, encoding="utf-8").read()
    if args.text:
        rep = check_prose(raw)
    else:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"不是合法 JSON：{exc}（散文请加 --text）", file=sys.stderr)
            return 2
        rep = check_bundle(data)

    verdict = "BLOCK" if rep.blocked else "PASS"
    if args.json:
        print(json.dumps({"verdict": verdict, "issues": rep.issues},
                         ensure_ascii=False, indent=2))
    else:
        print(f"verdict={verdict}  issues={len(rep.issues)}")
        for i in rep.issues:
            print(f"  [{i['level']}] {i['where']} · {i['rule']}: {i['detail']}")
    return 1 if verdict == "BLOCK" else 0


if __name__ == "__main__":
    sys.exit(main())
