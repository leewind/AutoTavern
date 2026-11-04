"""Regenerate docs/LEEAGENT_BENCH_RESULTS.md from an answers file.

Reuses tavernbench.score's own score_answer so the table always matches the
official scorer (same tolerance / value-map logic); no reimplementation.

    ../.venv/bin/python scripts/bench_doc.py [answers.jsonl]
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(REPO / "tavernbench"))

from tavernbench.score import load_answers, score_answer   # noqa: E402


def main():
    ans_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "bench_answers_eval.jsonl"
    base = REPO / "tavernbench" / "data" / "eval"
    labels = {d["id"]: d for d in map(json.loads, open(base / "labels.jsonl"))}
    prompts = {d["id"]: d for d in map(json.loads, open(base / "prompts.jsonl"))}
    answers = load_answers(ans_path)

    rows, cat_stat = [], {}
    for rid in sorted(labels):
        lab, row = labels[rid], answers.get(rid, {"response": None, "error": "missing"})
        ok, sc = score_answer(lab, row)
        cat = prompts[rid]["category"]
        c = cat_stat.setdefault(cat, [0, 0.0])
        c[0] += 1
        c[1] += ok
        rows.append((rid, cat, prompts[rid]["scenario"],
                     row.get("response"), lab["answer"], ok, sc))

    n = len(labels)
    acc = sum(ok for _, _, _, _, _, ok, _ in rows) / n
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                            cwd=REPO, capture_output=True, text=True).stdout.strip()
    out = [f"# LeeAgent TavernBench 全量逐题结果(2026-11-04,commit {commit})",
           "",
           "口径:`tavernbench.score`(全 368 题计分)。管线:引擎桥接(确定性)"
           "+ 标签口径 rollout(N1/N2/D4:全席 bot 续打、选项间配对 salt、"
           "128 reps、无初筛——2026-11-04 采纳,见 scripts/strategy_ab.py)"
           "+ D2 价值初筛 + 规则出口(deepseek,内容寻址缓存)。",
           ""]
    out.append("| 类别 | n | acc |")
    out.append("|---|---|---|")
    for cat in sorted(cat_stat, key=lambda c: -cat_stat[c][0]):
        cn, ok = cat_stat[cat]
        out.append(f"| {cat} | {cn} | {ok / cn:.3f} |")
    out.append("")
    out.append(f"**overall acc {acc:.3f}**({int(round(acc * n))}/{n})")
    out.append("")
    out.append("| id | 类别 | 场景 | 我方答案 | 标签 | 对错 | 得分 |")
    out.append("|---|---|---|---|---|---|---|")
    for rid, cat, scen, resp, lab_ans, ok, sc in rows:
        mine = resp if resp is not None else "(无答)"
        out.append(f"| {rid} | {cat} | {scen} | `{mine}` | "
                   f"`{json.dumps(lab_ans, ensure_ascii=False)}` | "
                   f"{'✓' if ok else '✗'} | {sc:.3f} |")
    target = REPO / "docs" / "LEEAGENT_BENCH_RESULTS.md"
    target.write_text("\n".join(out) + "\n")
    print(f"wrote {target} ({len(rows)} rows, overall {acc:.3f})")


if __name__ == "__main__":
    main()
