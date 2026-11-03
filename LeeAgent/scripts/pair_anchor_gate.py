"""Paired adoption gate for roadmap reopen-path-b: pair cores as comp anchors.

Same seeds, seat 0, two arms:
  on   comp.PAIR_ANCHOR = 6.0 (a held verified core is worth ~2 board minions)
  off   default v18+ (PAIR_ANCHOR = 0)
Contact survey (2026-11-04, dev 300-399): 41% of games own a pair core in the
commit window; 14% commit a DIFFERENT tribe while holding a core (the flip
surface), 6% hold a core but never commit. Ceiling ~ -0.08 place/100 games.

    ../.venv/bin/python scripts/pair_anchor_gate.py [--sets 300:100,400:100]
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
    from leeagent import comp as C
    from leeagent import gate
    from leeagent.config import thresholds
    C.PAIR_ANCHOR = 6.0 if arm == "on" else 0.0
    a = gate.LeeAgent(BASE_BANK, th=thresholds(), use_nimble=False)
    return seed, a.run_game(seed, seat=0)["placement"]


def sign_test(better: int, worse: int) -> float:
    n, k = better + worse, min(better, worse)
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def summarize(tag, on, off):
    deltas = {s: on[s] - off[s] for s in on}
    better = sum(1 for d in deltas.values() if d < 0)
    worse = sum(1 for d in deltas.values() if d > 0)
    tie = len(deltas) - better - worse
    mean = sum(deltas.values()) / len(deltas)
    dl = sorted(deltas.values())
    var = sum((d - sum(dl) / len(dl)) ** 2 for d in dl) / (len(dl) - 1)
    t = (sum(dl) / len(dl)) / (var / len(dl)) ** 0.5 if var else 0.0
    s = {
        "seeds": [min(on), max(on)], "n": len(on),
        "place_on": round(sum(on.values()) / len(on), 3),
        "place_off": round(sum(off.values()) / len(off), 3),
        "delta_place": round(mean, 3),
        "better/worse/tie": [better, worse, tie],
        "sign_p": round(sign_test(better, worse), 4),
        "paired_t": round(t, 2),
        "placements_on": [on[s] for s in sorted(on)],
        "placements_off": [off[s] for s in sorted(off)],
    }
    print(f"{tag}: on={s['place_on']:.2f} off={s['place_off']:.2f} "
          f"delta={mean:+.3f}  好/差/平 {better}/{worse}/{tie}  "
          f"p={s['sign_p']:.3f}", flush=True)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default="300:100,400:100")
    ap.add_argument("--out", default=str(ROOT / "runs" / "pair_anchor_gate.json"))
    a = ap.parse_args()

    out = {}
    for spec in a.sets.split(","):
        seed0, n = (int(x) for x in spec.split(":"))
        seeds = list(range(seed0, seed0 + n))
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
