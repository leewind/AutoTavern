"""Coordinate ascent over the comp model's eight thresholds.

Protocol (roadmap convergence decision): tune on a dedicated 200-game seed
set, then the final config must hold on BOTH dev(300-399) and holdout(400-499)
(no regression > 0.1 place on either), then a fresh-set final. One pool per
config (workers keep module patches — the leak lesson).

    ../.venv/bin/python scripts/comp_sweep.py
"""
from __future__ import annotations

import multiprocessing as mp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

AXES = [
    ("comp", "COMMIT_TURN", [3, 5]),
    ("comp", "COMMIT_MIN_BOARD", [1, 3]),
    ("comp", "W_AFFINITY", [2.0, 4.0]),
    ("comp", "W_DENSITY", [1.5, 4.0]),
    ("comp", "W_HERO", [0.0, 3.0]),
    ("policy", "COMP_BUY_BASE", [0.0, 6.0]),
    ("policy", "OFFCOMP_TAX", [0.0, 8.0]),
    ("policy", "COMP_SELL_PROTECT", [0.0, 10.0]),
]
BASE = {"comp": {"COMMIT_TURN": 4, "COMMIT_MIN_BOARD": 2, "W_AFFINITY": 3.0,
                 "W_DENSITY": 3.0, "W_HERO": 1.5},
        "policy": {"COMP_BUY_BASE": 3.0, "OFFCOMP_TAX": 4.0, "COMP_SELL_PROTECT": 6.0}}

TUNE_SEEDS = list(range(10000, 10200))
CHECK_SETS = {"dev": range(300, 400), "hold": range(400, 500)}


def run(args):
    seed, cfg = args
    import leeagent.policy as P
    import leeagent.comp as C
    from leeagent import gate, memory
    from leeagent.config import thresholds
    for mod, key, v in cfg:
        (P if mod == "policy" else C).__dict__[key] = v
    bank = memory.load(ROOT / "memories" / "seed.jsonl")
    return gate.LeeAgent(bank, th=thresholds(), use_nimble=False).run_game(seed, seat=0)["placement"]


def evaluate(cfg, seeds):
    # a fresh pool per config: workers retain module patches between tasks
    with mp.Pool(48) as pool:
        places = pool.map(run, [(s, cfg) for s in seeds])
    top4 = sum(1 for p in places if p <= 4)
    return sum(places) / len(places), top4


def main():
    best = {k: dict(v) for k, v in BASE.items()}

    def flat(d):
        return [(m, k, v) for m in di for k, v in di[m].items()] if False else \
               [(m, k, v) for m, ks in d.items() for k, v in ks.items()]

    base_place, base_top4 = evaluate(flat(best), TUNE_SEEDS)
    print(f"baseline: place={base_place:.3f} top4={base_top4/2:.0f}%", flush=True)

    for mod, key, values in AXES:
        cur = best[mod][key]
        results = [(cur, base_place, base_top4)]
        for v in values:
            trial = {k: dict(x) for k, x in best.items()}
            trial[mod][key] = v
            pl, t4 = evaluate(flat(trial), TUNE_SEEDS)
            results.append((v, pl, t4))
            print(f"  {mod}.{key}={v}: place={pl:.3f} top4={t4/2:.0f}%", flush=True)
        # adopt only on a real margin (>0.05 place) — guard against noise-chasing
        winner = min(results, key=lambda r: r[1])
        if winner[0] != cur and base_place - winner[1] > 0.05:
            best[mod][key] = winner[0]
            base_place, base_top4 = winner[1], winner[2]
            print(f"  -> adopt {mod}.{key}={winner[0]} (place {base_place:.3f})", flush=True)
        else:
            print(f"  -> keep {mod}.{key}={cur}", flush=True)

    print("final tuned config:", {m: best[m] for m in best}, flush=True)

    # holdout gate: both dev and holdout must hold
    ref = {}
    for name, seeds in CHECK_SETS.items():
        ref[name] = evaluate([], seeds)          # current tree = base constants
    tuned = {}
    for name, seeds in CHECK_SETS.items():
        tuned[name] = evaluate(flat(best), seeds)
    ok = all(tuned[n][0] <= ref[n][0] + 0.1 for n in CHECK_SETS)
    for n in CHECK_SETS:
        print(f"check {n}: base place={ref[n][0]:.3f}/{ref[n][1]/1:.0f}%  "
              f"tuned place={tuned[n][0]:.3f}  {'ok' if tuned[n][0] <= ref[n][0] + 0.1 else 'REGRESS'}",
              flush=True)
    print("VERDICT:", "ACCEPT" if ok else "REJECT (keep base constants)", flush=True)


if __name__ == "__main__":
    main()
