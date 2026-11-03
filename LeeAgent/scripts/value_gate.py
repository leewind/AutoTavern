"""Paired adoption gate for value-gated upgrades (roadmap 7).

Same seeds, seat 0, two arms:
  on   current policy (E[reward|buy] vs E[reward|upgrade])
  off   same policy with _synergy_table() -> {} (the only diff is the feature)
Iron rule: dev 300-399 and holdout 400-499 must agree; a fresh repro set
(1600+) confirms before anything is reported.

    ../.venv/bin/python scripts/synergy_gate.py [--sets 300:100,400:100]
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
    import leeagent.agent as A
    from leeagent import gate
    from leeagent.config import thresholds
    if arm == "on":
        A.VALUE_GATE = True       # default False in agent.py until adopted
    a = gate.LeeAgent(BASE_BANK, th=thresholds(), use_nimble=False)
    return seed, a.run_game(seed, seat=0)["placement"]


def sign_test(better: int, worse: int) -> float:
    """Two-sided binomial sign-test p (decisive games only)."""
    n, k = better + worse, min(better, worse)
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def summarize(tag, on, off):
    deltas = {s: on[s] - off[s] for s in on}          # negative = on places better
    better = sum(1 for d in deltas.values() if d < 0)
    worse = sum(1 for d in deltas.values() if d > 0)
    tie = len(deltas) - better - worse
    mean = lambda d: sum(d.values()) / len(d)
    top4 = lambda d: 100 * sum(1 for p in d.values() if p <= 4) / len(d)
    dl = sorted(deltas.values())
    var = sum((d - sum(dl) / len(dl)) ** 2 for d in dl) / (len(dl) - 1)
    t = (sum(dl) / len(dl)) / (var / len(dl)) ** 0.5 if var else 0.0
    s = {
        "seeds": [min(on), max(on)], "n": len(on),
        "place_on": round(mean(on), 3), "place_off": round(mean(off), 3),
        "delta_place": round(mean(on) - mean(off), 3),
        "top4_on": round(top4(on), 1), "top4_off": round(top4(off), 1),
        "better/worse/tie": [better, worse, tie],
        "sign_p": round(sign_test(better, worse), 4),
        "paired_t": round(t, 2),
        "placements_on": [on[s] for s in sorted(on)],
        "placements_off": [off[s] for s in sorted(off)],
    }
    print(f"{tag}: on={s['place_on']:.2f} off={s['place_off']:.2f} "
          f"delta={s['delta_place']:+.3f}  top4 {s['top4_on']:.0f}% vs "
          f"{s['top4_off']:.0f}%  好/差/平 {better}/{worse}/{tie}  p={s['sign_p']:.3f}",
          flush=True)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default="300:100,400:100",
                    help="seed0:n per set, comma separated")
    ap.add_argument("--out", default=str(ROOT / "runs" / "value_gate.json"))
    a = ap.parse_args()

    out = {}
    for spec in a.sets.split(","):
        seed0, n = (int(x) for x in spec.split(":"))
        seeds = list(range(seed0, seed0 + n))
        # one fresh pool per arm: the off-patch would otherwise leak across arms
        with mp.Pool(48) as pool:
            on = dict(pool.map(run, [(s, "on") for s in seeds]))
        with mp.Pool(48) as pool:
            off = dict(pool.map(run, [(s, "off") for s in seeds]))
        out[f"seeds_{seed0}_{seed0 + n - 1}"] = summarize(
            f"[{seed0}-{seed0 + n - 1}]", on, off)

    both = [v["delta_place"] for v in out.values()]
    agree = all(d < 0 for d in both) and all(v["sign_p"] < 0.1 for v in out.values())
    out["verdict"] = "ADOPT (both sets better, p<0.1 each)" if agree else \
        "NO-ADOPT (sets disagree or not significant)"
    print(out["verdict"])
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
