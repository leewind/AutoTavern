"""Coordinate-ascent threshold training for the policy's continuous knobs.

Sweeps one axis at a time (3 candidate values), 100 paired dev games per
config, all configs in parallel processes. Winner becomes the new default for
the next axis. 96 cores make each round ~30s.

    ../.venv/bin/python scripts/param_sweep.py --seeds 300-399 --rounds 4
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# the axes, in sensitivity order; each round tries these values
AXES = [
    ("swap_margin", [6, 10, 14]),          # slot-upgrade sell margin (base 10)
    ("scout_behind", [0.25, 0.30, 0.40]),  # below: all-in tempo (base 0.30)
    ("hp_gate", [16, 20, 24]),             # no levelling below this hp (base 20)
    ("curve_mult", [1.7, 2.0, 2.3]),       # upgrade when turn > m*tier (base 2.0)
]


def _run_one(args):
    seed, overrides = args
    import leeagent.policy as P
    from leeagent import gate, memory
    from leeagent.config import thresholds

    # patch the policy constants per config
    P.SWAP_MARGIN = overrides.get("swap_margin", 10)
    P.SCOUT_BEHIND = overrides.get("scout_behind", 0.30)
    P.HP_GATE = overrides.get("hp_gate", 20)
    P.CURVE_MULT = overrides.get("curve_mult", 2.0)

    store = memory.load(ROOT / "memories" / "seed.jsonl")
    a = gate.LeeAgent(store, th=thresholds(), use_nimble=False)
    return a.run_game(seed, seat=0)["placement"]


def evaluate(seeds, overrides, pool):
    places = pool.map(_run_one, [(s, overrides) for s in seeds])
    top4 = sum(1 for p in places if p <= 4)
    rewards = [1 - 2 * (p - 1) / 7 for p in places]
    return top4, sum(rewards) / len(rewards), sum(places) / len(places)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed0", type=int, default=300)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--rounds", type=int, default=len(AXES))
    a = ap.parse_args()
    seeds = list(range(a.seed0, a.seed0 + a.n))

    import leeagent.policy as P
    P.SWAP_MARGIN, P.SCOUT_BEHIND, P.HP_GATE, P.CURVE_MULT = 10, 0.30, 20, 2.0

    best = {"swap_margin": 10, "scout_behind": 0.30, "hp_gate": 20, "curve_mult": 2.0}
    with mp.Pool(96) as pool:
        t4, mr, mp_ = evaluate(seeds, best, pool)
        print(f"baseline: top4={t4}% mean={mr:+.3f} place={mp_:.2f}", flush=True)
        for axis, values in AXES[:a.rounds]:
            for v in values:
                cfg = {**best, axis: v}
                t4, mr, mp_ = evaluate(seeds, cfg, pool)
                mark = " <== " if v == best[axis] else ""
                print(f"{axis}={v}: top4={t4}% mean={mr:+.3f} place={mp_:.2f}{mark}", flush=True)
            # pick the winner of this axis by top4, tie-break mean reward
            results = []
            for v in values:
                cfg = {**best, axis: v}
                t4, mr, mp_ = evaluate(seeds, cfg, pool)
                results.append((t4, mr, v))
            results.sort(key=lambda x: (x[0], x[1]), reverse=True)
            best[axis] = results[0][2]
            print(f"  -> {axis} = {best[axis]}", flush=True)
    print("final config:", json.dumps(best), flush=True)


if __name__ == "__main__":
    main()
