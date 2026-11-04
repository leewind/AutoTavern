"""Paired gate for LATE_SEARCH: the E1 phase-mixed agent.

E0 (runs/strategy_direct_e0.json) split the decision-maker crown on the
bench's own tasks: heuristic scorer wins early (N1 0.690 vs best search
0.517), bot-continuation search wins late (N2 0.481 vs 0.259) and on
discover picks at any turn (D4 0.625 vs 0.312). E1 therefore changes ONLY
those two decision sites — every late recruit turn's first action (>=
LATE_SEARCH_TURN, data-defined: N1 spans 4-7, N2 8-12) and pending
discover/choose decisions — with the heuristic kept as nominator (top-K)
and all-bot paired rollouts (48 reseeds) as arbiter. Everything else,
including all early turns, is byte-untouched.

Arms (paired seeds, seat 0):
  on   agent.LATE_SEARCH = True
  off   default policy

Pre-registered criteria (house discipline, decided before outcomes):
  gate      proceed to fresh-seed replication (1900-1999) only if dev AND
            holdout both have delta_place < 0 and the merged sign p < 0.10
  adoption  only if the fresh set replicates the direction
  contact   fires and flips are reported per kind (recruit/pending); a
            flip rate <10% of fires would mean the arbitrator never
            disagrees with its nominator (search degenerate)

Caveat carried from round 9: bench alignment is not live realization —
this gate is the test of exactly that gap.

    ../.venv/bin/python scripts/late_search_gate.py [--sets 300:100,400:100]
"""

from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from leeagent import memory as M                    # noqa: E402
from leeagent.config import ROOT as CFG_ROOT        # noqa: E402

BASE_BANK = M.load(CFG_ROOT / "memories" / "seed.jsonl")


def run(args):
    seed, arm = args
    from leeagent import agent as agent_mod
    from leeagent import gate
    from leeagent.config import thresholds
    agent_mod.LATE_SEARCH = (arm == "on")
    a = gate.LeeAgent(BASE_BANK, th=thresholds(), use_nimble=False)
    r = a.run_game(seed, seat=0)
    fires = a.stats.get("late_searches") or []
    return seed, arm, r["placement"], fires


def sign_test(better: int, worse: int) -> float:
    n, k = better + worse, min(better, worse)
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def summarize(tag, on, off, fires):
    deltas = {s: on[s] - off[s] for s in on}
    better = sum(1 for d in deltas.values() if d < 0)
    worse = sum(1 for d in deltas.values() if d > 0)
    tie = len(deltas) - better - worse
    mean = sum(deltas.values()) / len(deltas)
    var = sum((d - mean) ** 2 for d in deltas.values()) / (len(deltas) - 1)
    t = mean / (var / len(deltas)) ** 0.5 if var else 0.0
    n_fire = len(fires)
    n_flip = sum(1 for f in fires
                 if f.get("means") and f.get("picked") != f.get("heuristic"))
    by_kind = {}
    for f in fires:
        k = by_kind.setdefault(f["kind"], [0, 0])
        k[0] += 1
        k[1] += 1 if (f.get("means") and f.get("picked") != f.get("heuristic")) else 0
    s = {
        "seeds": [min(on), max(on)], "n": len(on),
        "place_on": round(sum(on.values()) / len(on), 3),
        "place_off": round(sum(off.values()) / len(off), 3),
        "delta_place": round(mean, 3),
        "better/worse/tie": [better, worse, tie],
        "sign_p": round(sign_test(better, worse), 4),
        "paired_t": round(t, 2),
        "fires": n_fire,
        "flips": n_flip,
        "fires_by_kind": by_kind,
        "placements_on": [on[s] for s in sorted(on)],
        "placements_off": [off[s] for s in sorted(off)],
    }
    print(f"{tag}: on={s['place_on']:.2f} off={s['place_off']:.2f} "
          f"delta={mean:+.3f}  好/差/平 {better}/{worse}/{tie}  "
          f"p={s['sign_p']:.3f}  火/翻 {n_fire}/{n_flip} {by_kind}", flush=True)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default="300:100,400:100")
    ap.add_argument("--out", default=str(ROOT / "runs" / "late_search_gate.json"))
    a = ap.parse_args()

    out = {}
    fires_all = []
    for spec in a.sets.split(","):
        seed0, n = (int(x) for x in spec.split(":"))
        seeds = list(range(seed0, seed0 + n))
        jobs = [(s, arm) for s in seeds for arm in ("off", "on")]
        res = {"off": {}, "on": {}}
        with mp.Pool(96) as pool:
            for seed, arm, pl, fires in pool.imap_unordered(run, jobs):
                res[arm][seed] = pl
                if arm == "on":
                    for f in fires:
                        f = dict(f)
                        f["seed"] = seed
                        if f.get("means"):
                            f["picked"] = min(f["means"],
                                              key=lambda x: (f["means"][x],
                                                             f["cands"].index(x)))
                        fires_all.append(f)
        tag = f"seeds_{seed0}_{seed0 + n - 1}"
        out[tag] = summarize(tag, res["on"], res["off"],
                             [f for f in fires_all if seed0 <= f["seed"] < seed0 + n])

    out["fires_sample"] = sorted(fires_all, key=lambda f: f["seed"])[:400]
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"wrote {a.out}", flush=True)


if __name__ == "__main__":
    main()
