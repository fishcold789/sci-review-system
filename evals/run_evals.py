#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回归测试 —— 每一项都拿真实内容喂真实检查器。

不做"某个字符串在不在某个文件里"这类静态自洽检查：那种测试全绿也证明不了
任何事——把参考文档正文换成关键词堆砌，照样全绿。

第 1 项是整套东西成不成立的**单点指标**：
    同一个结构、只把自然语言字段换成空话，必须给出不同的判决。
做不到这一条，其余全部无意义。

用法：python3 evals/run_evals.py [-v]
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "evals" / "fixtures"
PY = sys.executable


def run(script, *args):
    r = subprocess.run([PY, str(ROOT / "checks" / script), *map(str, args), "--json"],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout), r.returncode
    except json.JSONDecodeError:
        return {"verdict": "ERROR", "stderr": r.stderr[:400]}, r.returncode


CASES = []


def case(name):
    def deco(fn):
        CASES.append((name, fn))
        return fn
    return deco


@case("空话回归 · 正样本必须 PASS")
def _():
    out, _ = run("check_emptiness.py", FIX / "正样本.json")
    return out["verdict"] == "PASS", f"verdict={out['verdict']} issues={len(out.get('issues', []))}"


@case("空话回归 · 空话版必须不是 PASS ★单点指标")
def _():
    out, _ = run("check_emptiness.py", FIX / "空话版.json")
    return out["verdict"] != "PASS", f"verdict={out['verdict']} issues={len(out.get('issues', []))}"


@case("空话检测 · 拦下的理由必须落到具体字段")
def _():
    out, _ = run("check_emptiness.py", FIX / "空话版.json")
    wheres = {i["where"].split(".")[0] for i in out.get("issues", [])}
    hit = any(w.startswith("claims/") for w in wheres) and any(
        w.startswith("syntheses/") for w in wheres)
    return hit, f"命中字段类别 {sorted(wheres)[:4]}…"


@case("台账比对 · 伪造题录必须被单独揪出")
def _():
    out, _ = run("check_ledger_vs_source.py", FIX / "原文_题录.txt", FIX / "台账_含伪造.md")
    ns = [s["n"] for s in out.get("suspect", [])]
    return out["verdict"] == "BLOCK" and ns == [48], f"suspect={ns}"


@case("台账比对 · 咬合的条目不得误报")
def _():
    out, _ = run("check_ledger_vs_source.py", FIX / "原文_题录.txt", FIX / "台账_含伪造.md")
    ok = {s["n"] for s in out.get("suspect", [])}
    return {46, 47, 49}.isdisjoint(ok), f"误报编号 {sorted({46,47,49} & ok)}"


@case("稿件纪律 · 三条语法硬规则必须 BLOCK")
def _():
    out, _ = run("check_prose_discipline.py", FIX / "稿件_违规样例.md")
    rules = {i["rule"][:1] for i in out["issues"] if i["level"] == "BLOCK"}
    return out["verdict"] == "BLOCK" and {"A", "B", "C"} <= rules, f"命中 {sorted(rules)}"


@case("稿件纪律 · 禁用词必须 BLOCK")
def _():
    out, _ = run("check_prose_discipline.py", FIX / "稿件_违规样例.md")
    return any(i["rule"] == "禁用词" for i in out["issues"]), "未命中禁用词"


@case("稿件纪律 · 合格样例不得 BLOCK")
def _():
    out, _ = run("check_prose_discipline.py", FIX / "稿件_合格样例.md")
    return out["verdict"] != "BLOCK", f"verdict={out['verdict']}"


@case("稿件计量 · --measure 必须给出可立基线的字段")
def _():
    r = subprocess.run([PY, str(ROOT / "checks" / "check_prose_discipline.py"),
                        str(FIX / "稿件_合格样例.md"), "--measure"],
                       capture_output=True, text=True)
    m = json.loads(r.stdout)
    need = {"n_par", "words", "sents", "sent_mean", "sub_per_sent", "para_mean", "para_ratio"}
    return need <= set(m), f"缺字段 {sorted(need - set(m))}"


@case("写盘回读 · 错误页必须 BLOCK")
def _():
    out, _ = run("check_writeback.py", FIX / "落盘事故_错误页.md")
    return out["verdict"] == "BLOCK", f"verdict={out['verdict']}"


@case("写盘回读 · 本仓库自己的文件不得误报")
def _():
    bad = []
    for f in list((ROOT / "references").glob("*.md")) + \
             list((ROOT / "templates").glob("*.md")) + \
             list((ROOT / "checks").glob("*.py")) + [ROOT / "SKILL.md"]:
        out, _ = run("check_writeback.py", f, "--min-bytes", "400")
        if out["verdict"] != "PASS":
            bad.append((f.name, out.get("issues")))
    return not bad, f"误报 {bad}"


@case("领域词清扫 · 技能自身不得自带某个学科的默认内容")
def _():
    # 这里只做形状检查：SKILL.md 必须写明"领域知识由使用者提供"，
    # 且必须存在索要领域内容的槽。真正的清扫由人在改动后 grep 一遍。
    txt = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    need = ["它自身不带任何领域内容", "禁止等价表", "下游工程判据", "分类轴"]
    miss = [n for n in need if n not in txt]
    return not miss, f"缺 {miss}"


def main():
    verbose = "-v" in sys.argv
    ok = 0
    for name, fn in CASES:
        try:
            passed, detail = fn()
        except Exception as exc:                       # noqa: BLE001
            passed, detail = False, f"异常 {type(exc).__name__}: {exc}"
        mark = "PASS" if passed else "FAIL"
        ok += passed
        if not passed or verbose:
            print(f"[{mark}] {name}  —  {detail}")
        else:
            print(f"[{mark}] {name}")
    print(f"\n{ok}/{len(CASES)} 通过")
    return 0 if ok == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(main())
