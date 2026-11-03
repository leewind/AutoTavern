"""Empirical trinket strength table (same protocol as the hero table).

At seat 0's trinket pending the offer is re-rolled (engine offer_trinkets)
until the target appears, then chosen at its real cost; the game plays out
with the current policy. Ranking is therefore cost-honest.

    ../.venv/bin/python scripts/trinket_table.py [--games 24]
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def trinket_unit(args):
    kind, tid, seed = args
    import taverngym
    from leeagent import gate, memory
    from leeagent.config import thresholds

    g = taverngym.Game(seed=seed)
    agent = gate.LeeAgent(memory.load(ROOT / "memories" / "seed.jsonl"),
                          th=thresholds(), use_nimble=False)
    agent.reset()
    agent._turn_seen = -1
    forced = False
    rerolls = 0
    guard = 0
    while not g.is_over() and guard < 100000:
        for p in range(g.num_players):
            if not g.needs_action(p):
                continue
            if p == 0 and not forced:
                view = json.loads(g.view(0))
                pend = view["me"].get("pending") or {}
                if pend.get("kind") == "trinket":
                    # the lesser window is turn 6, the greater window turn 9:
                    # forcing a greater offer in the lesser window would hand
                    # us a powerful trinket four turns early (that bug made
                    # every greater trinket "average 1st place")
                    window_greater = view["turn"] >= 9
                    if window_greater == (kind == "greater"):
                        opts = pend.get("options") or []
                        if tid in {o.get("id") for o in opts}:
                            k = next(i for i, o in enumerate(opts) if o.get("id") == tid)
                            if 30 + k in [i for i, b in enumerate(g.legal_mask(0)) if b]:
                                g.step(0, 30 + k)
                                forced = True
                                continue
                            return kind, tid, None   # offered but unaffordable
                        if rerolls >= 30:            # conditional trinkets may
                            return kind, tid, None   # never be legally offered
                        rerolls += 1
                        g.debug(json.dumps({"cmd": "offer_trinkets", "p": 0,
                                            "greater": kind == "greater"}))
                        continue
            g.step(p, agent.choose(g, p) if p == 0 else g.bot_action(p))
        guard += 1
    if not g.is_over():
        return kind, tid, None
    return kind, tid, int(list(g.placements())[0])


def _safe_unit(args):
    try:
        return trinket_unit(args)
    except Exception as e:                     # locate bad jobs, don't kill the pool
        import traceback
        print(f"UNIT-FAIL {args}: {e}", traceback.format_exc()[-400:], flush=True)
        return args[0], args[1], None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=24)
    ap.add_argument("--seed0", type=int, default=80000)
    a = ap.parse_args()

    import taverngym
    catalog = json.loads(taverngym.catalog_json())
    trinkets = [(("greater" if "greater" in c["kind"] else "lesser"), c["id"])
                for c in catalog
                if "trinket" in c.get("kind", "").lower()
                and c.get("implemented") and c.get("in_pool")]
    print(f"{len(trinkets)} trinkets x {a.games} games", flush=True)

    jobs = [(kind, tid, a.seed0 + i) for kind, tid in trinkets for i in range(a.games)]
    results = {}
    discarded = 0
    with mp.Pool(96) as pool:
        for kind, tid, pl in pool.imap_unordered(_safe_unit, jobs, chunksize=8):
            if pl is None:
                discarded += 1
                continue
            results.setdefault((kind, tid), []).append(pl)
    table = {tid: {"kind": kind, "n": len(v), "mean_place": round(sum(v) / len(v), 3)}
             for (kind, tid), v in results.items()}
    table = dict(sorted(table.items(), key=lambda kv: kv[1]["mean_place"]))
    out = ROOT / "data" / "trinket_table.json"
    out.write_text(json.dumps(table, indent=1))
    print(f"discarded {discarded} (never offered legally)")
    print("top8:", [(t, v["mean_place"]) for t, v in list(table.items())[:8]])
    print("bottom5:", [(t, v["mean_place"]) for t, v in list(table.items())[-5:]])
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
