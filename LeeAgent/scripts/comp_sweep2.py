"""Paired coordinate ascent over the comp model's eight thresholds (v2).

Improvements over comp_sweep.py: (a) paired same-seed evaluation - both arms
see the identical lobby, halving the noise at n=100; (b) tune on dev(300-399)
per the roadmap convergence decision, verify holdout(400-499), final on the
next fresh segment (1800-1899); (c) adoption inside the sweep needs paired
delta < -0.15 with more better-than-worse games (not a bare mean margin).

    ../.venv/bin/python scripts/comp_sweep2.py [--final-only]
"""
from __future__ import annotations

import argparse
import math
import multiprocessing as mp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# (module, key, candidates) - current tree values are read at runtime;
# COMMIT_MIN_BOARD=1 is excluded by roadmap decision (mechanism regression)
AXES = [
    ("comp", "COMMIT_TURN", [4, 6]),
    ("comp", "COMMIT_MIN_BOARD", [2]),
    ("comp", "W_AFFINITY", [2.0, 4.0]),
    ("comp", "W_DENSITY", [1.5, 4.0]),
    ("comp", "W_HERO", [0.0, 3.0]),
    ("policy", "COMP_BUY_BASE", [3.0, 6.0]),
    ("policy", "OFFCOMP_TAX", [2.0, 8.0]),
    ("policy", "COMP_SELL_PROTECT", [3.0, 10.0]),
]
TUNE_SEEDS = list(range(300, 400))
CHECK_SETS = {"holdout": range(400, 500), "fresh1800": range(1800, 1900)}


def run(args):
    seed, cfg = args
    import leeagent.policy as P
    import leeagent.comp as C
    from leeagent import gate, memory
    from leeagent.config import thresholds
    for mod, key, v in cfg:
        (P if mod == "policy" else C).__dict__[key] = v
    bank = memory.load(ROOT / "memories" / "seed.jsonl")
    return seed, gate.LeeAgent(bank, th=thresholds(), use_nimble=False).run_game(seed, seat=0)["placement"]


def arm(cfg, seeds):
    """One fresh pool per arm: workers retain module patches between tasks."""
    with mp.Pool(48) as pool:
        return dict(pool.map(run, [(s, cfg) for s in seeds]))


def paired(base, cand, tag):
    d = {s: cand[s] - base[s] for s in base}      # negative = candidate better
    bet = sum(1 for v in d.values() if v < 0)
    wor = sum(1 for v in d.values() if v > 0)
    mean = sum(d.values()) / len(d)
    n, k = bet + wor, min(bet, wor)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n) if n else 1.0
    print(f"{tag}: delta={mean:+.3f}  好/差/平 {bet}/{wor}/{len(d)-bet-wor}  p={p:.3f}",
          flush=True)
    return mean, bet, wor, p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--final-only", action="store_true",
                    help="skip tuning; gate the config in --cfg against defaults")
    ap.add_argument("--cfg", default="", help="mod.key=val,comma separated")
    a = ap.parse_args()

    if a.final_only:
        cfg = []
        for kv in filter(None, a.cfg.split(",")):
            mk, v = kv.split("=")
            m, k = mk.split(".")
            cfg.append((m, k, float(v) if "." in v else int(v)))
        _final(cfg, "supplied")
        return

    base_cfg = []          # current tree constants
    base = arm(base_cfg, TUNE_SEEDS)
    print(f"tuning on dev {TUNE_SEEDS[0]}-{TUNE_SEEDS[-1]}, "
          f"base place={sum(base.values())/len(base):.3f}", flush=True)

    adopted = []
    for mod, key, cands in AXES:
        cur = getattr(__import__(f"leeagent.{mod}", fromlist=[key]), key)
        results = [(cur, 0.0, 0, 0, 1.0)]
        for v in cands:
            trial = base_cfg + [(mod, key, v)]
            m, bet, wor, p = paired(base, arm(trial, TUNE_SEEDS),
                                    f"  {mod}.{key}={v}")
            results.append((v, m, bet, wor, p))
        winner = min(results, key=lambda r: r[1])
        if winner[0] != cur and winner[1] < -0.15 and winner[2] > winner[3]:
            base_cfg = base_cfg + [(mod, key, winner[0])]
            base = arm(base_cfg, TUNE_SEEDS)      # re-base: ascent is sequential
            adopted.append((mod, key, winner[0], winner[1]))
            print(f"  -> adopt {mod}.{key}={winner[0]} "
                  f"(paired {winner[1]:+.3f}, base place "
                  f"{sum(base.values())/len(base):.3f})", flush=True)
        else:
            print(f"  -> keep {mod}.{key}={cur}", flush=True)

    print("adopted:", adopted or "nothing", flush=True)
    _final([(m, k, v) for m, k, v, _ in adopted], "ascent")


def _final(cfg, how):
    """holdout + fresh-seed paired gate vs the tree defaults."""
    if not cfg:
        print("no deltas to gate", flush=True)
        return
    print(f"final gate ({how}) cfg={cfg}", flush=True)
    ok = True
    for name, seeds in CHECK_SETS.items():
        base = arm([], seeds)
        cand = arm(cfg, list(seeds))
        m, bet, wor, p = paired(base, cand, f"[{name}]")
        if m >= 0:
            ok = False
    print("VERDICT:", "ADOPT" if ok else
          "NO-ADOPT (keep current constants)", flush=True)


if __name__ == "__main__":
    main()
