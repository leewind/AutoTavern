"""E0: how would the heuristic policy itself answer the N1/N2/D4 tasks?

Three-way decision-maker comparison on identical tasks (the search arms are
already measured; this adds the no-search baseline):

  natural   the policy's first chosen action (agent.choose) -- strict
            (off-policy tasks count wrong) and restricted (only tasks whose
            natural pick is among the offered options)
  forced    the policy's top-scored action AMONG the offered options
            (captured from policy.score_actions during the same choose call)

Scoring per task uses tavernbench.score.score_answer (the official logic,
same as bench_doc.py); labels are never read outside it.

    ../.venv/bin/python scripts/strategy_direct_e0.py
"""

from __future__ import annotations

import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO / "tavernbench"))

from tavernbench.score import score_answer          # noqa: E402


def main():
    from leeagent import agent as agent_mod
    from leeagent import gate, memory, policy
    from leeagent.config import thresholds
    from tavernbench import engine as E

    base = REPO / "tavernbench" / "data" / "eval"
    states = {}
    for l in gzip.open(base / "states.jsonl.gz", "rt"):
        r = json.loads(l)
        if r["id"].split("-")[0] in ("N1", "N2", "D4"):
            states[r["id"]] = r
    labels = {d["id"]: d for d in map(json.loads, open(base / "labels.jsonl"))}

    store = memory.load(ROOT / "memories" / "seed.jsonl")

    # capture score_actions' ranking during the real choose() call
    real_score = policy.score_actions
    captured = {}

    def spy(view, matched, legal, **kw):
        out = real_score(view, matched, legal, **kw)
        captured["ranking"] = out
        return out

    policy.score_actions = spy

    rows = []
    for rid in sorted(states):
        row = states[rid]
        g = E.from_state(row["state"])
        seat = row["seat"]
        opts = [int(k) for k in row["map"]]
        a = gate.LeeAgent(store, th=thresholds(), use_nimble=False)
        a.reset()
        a._turn_seen = -1
        natural = a.choose(g, seat)
        ranking = captured.get("ranking") or []
        by_action = {act: (i, sc) for i, (sc, act, _l, _w) in enumerate(ranking)}
        forced = None
        if all(k in by_action for k in opts):
            forced = max(opts, key=lambda k: (-by_action[k][0], by_action[k][1]))
        rec = {"id": rid, "options": opts, "natural": natural,
               "in_options": natural in opts, "forced": forced}
        for key, k in (("natural", natural if natural in opts else None),
                       ("forced", forced)):
            rec[key + "_correct"] = None
            if k is not None:
                ok, _sc = score_answer(
                    labels[rid], {"response": json.dumps(
                        {"answer": row["map"][str(k)]})})
                rec[key + "_correct"] = bool(ok)
        rows.append(rec)

    policy.score_actions = real_score

    summ = defaultdict(lambda: {"n": 0, "in": 0, "nat_ok": 0, "forced": 0,
                                "forced_ok": 0})
    for r in rows:
        s = summ[r["id"].split("-")[0]]
        s["n"] += 1
        s["in"] += r["in_options"]
        s["nat_ok"] += bool(r["natural_correct"])
        s["forced"] += r["forced"] is not None
        s["forced_ok"] += bool(r["forced_correct"])
    out = {"rows": rows, "summary": {}}
    print(f"{'scen':5} {'n':>3} {'自然首动作在选项内':>10} {'restricted':>10} "
          f"{'strict':>7} {'forced可判':>9} {'forced':>7}")
    for scen, s in sorted(summ.items()):
        out["summary"][scen] = {
            "n": s["n"],
            "natural_in_options": s["in"],
            "natural_restricted_acc": round(s["nat_ok"] / s["in"], 3) if s["in"] else None,
            "natural_strict_acc": round(s["nat_ok"] / s["n"], 3),
            "forced_decidable": s["forced"],
            "forced_acc": round(s["forced_ok"] / s["n"], 3),
        }
        print(f"{scen:5} {s['n']:>3} {s['in']:>10} "
              f"{s['nat_ok'] / s['in'] if s['in'] else 0:>10.3f} "
              f"{s['nat_ok'] / s['n']:>7.3f} {s['forced']:>9} "
              f"{s['forced_ok'] / s['n']:>7.3f}")
    (ROOT / "runs" / "strategy_direct_e0.json").write_text(json.dumps(out, indent=1))
    print("wrote runs/strategy_direct_e0.json")


if __name__ == "__main__":
    main()
