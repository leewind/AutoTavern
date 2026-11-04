"""Paired gate for COMP_ROLLOUT: rollout arbitration of the comp direction.

Idea (2026-11-04, de-risked by the bench label-protocol A/B): at the
once-per-game comp commit, take comp.rank() top-3 tribes, replay the live
game COMP_ROLLOUT_REPS times per candidate — same reseeds for every
candidate, seat replayed by this same policy with its direction pinned,
opponents by the engine bots (the exact future the live game faces) — and
commit to the best mean placement. Unlike bias injection, the search carries
decision-grade magnitude and can overturn a wrong non-tied decision.

Arms (paired seeds, seat 0, defaults untouched):
  on   agent.COMP_ROLLOUT = True
  off   default policy

Pre-registered criteria (decided before looking, per house discipline):
  contact   if the on-arm flips the heuristic direction in <10% of searched
            games, NO-GO (the injection-surface wall, transposed)
  gate      proceed to a fresh-seed replication only if dev AND holdout both
            have delta_place < 0 and the merged sign p < 0.10
  adoption  only if the fresh set (1900-1999) replicates the direction

Protocol note (pre-outcome correction): candidates from comp.rank(min_board=1) —
a contact survey on dev 300-339 (no outcome data) showed min_board=2 starves the
set (23/34 games single-candidate); =1 gives 2-3 candidates in 32/34, heuristic
pick always rank[0].

    ../.venv/bin/python scripts/comp_rollout_gate.py [--sets 300:100,400:100]
                                                    [--reps 48]
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
    seed, arm, reps = args
    from leeagent import agent as agent_mod
    from leeagent import gate
    from leeagent.config import thresholds
    agent_mod.COMP_ROLLOUT = (arm == "on")
    agent_mod.COMP_ROLLOUT_REPS = reps
    a = gate.LeeAgent(BASE_BANK, th=thresholds(), use_nimble=False)
    r = a.run_game(seed, seat=0)
    cs = (a.stats.get("comp_searches") or [None])[0]
    return seed, arm, r["placement"], cs


def sign_test(better: int, worse: int) -> float:
    n, k = better + worse, min(better, worse)
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def summarize(tag, on, off, contacts):
    deltas = {s: on[s] - off[s] for s in on}
    better = sum(1 for d in deltas.values() if d < 0)
    worse = sum(1 for d in deltas.values() if d > 0)
    tie = len(deltas) - better - worse
    mean = sum(deltas.values()) / len(deltas)
    var = sum((d - mean) ** 2 for d in deltas.values()) / (len(deltas) - 1)
    t = mean / (var / len(deltas)) ** 0.5 if var else 0.0
    searched = [c for c in contacts if c and c.get("means")]
    flipped = [c for c in searched if c.get("picked") != c.get("heuristic")]
    s = {
        "seeds": [min(on), max(on)], "n": len(on),
        "place_on": round(sum(on.values()) / len(on), 3),
        "place_off": round(sum(off.values()) / len(off), 3),
        "delta_place": round(mean, 3),
        "better/worse/tie": [better, worse, tie],
        "sign_p": round(sign_test(better, worse), 4),
        "paired_t": round(t, 2),
        "searched_games": len(searched),
        "flipped_games": len(flipped),
        "flip_rate": round(len(flipped) / len(searched), 3) if searched else None,
        "placements_on": [on[s] for s in sorted(on)],
        "placements_off": [off[s] for s in sorted(off)],
    }
    print(f"{tag}: on={s['place_on']:.2f} off={s['place_off']:.2f} "
          f"delta={mean:+.3f}  好/差/平 {better}/{worse}/{tie}  "
          f"p={s['sign_p']:.3f}  接触 {len(flipped)}/{len(searched)}",
          flush=True)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default="300:100,400:100")
    ap.add_argument("--reps", type=int, default=48)
    ap.add_argument("--out", default=str(ROOT / "runs" / "comp_rollout_gate.json"))
    a = ap.parse_args()

    out = {}
    contacts_all = []
    for spec in a.sets.split(","):
        seed0, n = (int(x) for x in spec.split(":"))
        seeds = list(range(seed0, seed0 + n))
        jobs = [(s, arm, a.reps) for s in seeds for arm in ("off", "on")]
        res = {"off": {}, "on": {}}
        with mp.Pool(96) as pool:
            for seed, arm, pl, cs in pool.imap_unordered(run, jobs):
                res[arm][seed] = pl
                if arm == "on" and cs:
                    cs = dict(cs)
                    cs["seed"] = seed
                    if cs.get("means"):
                        cs["picked"] = min(cs["means"],
                                           key=lambda c: (cs["means"][c],
                                                          cs["candidates"].index(c)))
                    contacts_all.append(cs)
        tag = f"seeds_{seed0}_{seed0 + n - 1}"
        out[tag] = summarize(tag, res["on"], res["off"],
                             [c for c in contacts_all if seed0 <= c["seed"] < seed0 + n])

    # contact detail for the record
    out["contacts"] = [{k: c.get(k) for k in
                        ("seed", "turn", "heuristic", "picked", "candidates", "means")}
                       for c in sorted(contacts_all, key=lambda c: c["seed"])]
    out["reps"] = a.reps
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"wrote {a.out}", flush=True)


if __name__ == "__main__":
    main()
