"""Parallel A/B gate for the candidate memory bank (fresh seeds, paired).

    ../.venv/bin/python scripts/run_gate2.py [--n 100] [--seed0 2000]
"""
import argparse
import json
import multiprocessing as mp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from leeagent import memory as M                    # noqa: E402
from leeagent.config import ROOT as CFG_ROOT        # noqa: E402


def build():
    seed_bank = M.load(CFG_ROOT / "memories" / "seed.jsonl")
    cands = M.load(CFG_ROOT / "memories" / "candidates_clean.jsonl")
    return seed_bank, seed_bank + cands


def run(args):
    seed, bank = args
    from leeagent import gate
    from leeagent.config import thresholds
    a = gate.LeeAgent(bank, th=thresholds(), use_nimble=False)
    return a.run_game(seed, seat=0)["placement"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed0", type=int, default=2000)
    a = ap.parse_args()
    seeds = list(range(a.seed0, a.seed0 + a.n))
    bank_a, bank_b = build()

    with mp.Pool(48) as pool:
        pa = pool.map(run, [(s, bank_a) for s in seeds])
    with mp.Pool(48) as pool:
        pb = pool.map(run, [(s, bank_b) for s in seeds])

    def stats(places):
        rewards = [1 - 2 * (p - 1) / 7 for p in places]
        return round(sum(rewards) / len(places), 4), sum(1 for p in places if p <= 4)

    ra, ta = stats(pa)
    rb, tb = stats(pb)
    better = sum(1 for x, y in zip(pa, pb) if y < x)
    worse = sum(1 for x, y in zip(pa, pb) if y > x)
    gain = round(rb - ra, 4)
    verdict = {"seeds": [a.seed0, a.seed0 + a.n - 1], "n": a.n,
               "a_mean_reward": ra, "a_top4": ta, "b_mean_reward": rb, "b_top4": tb,
               "gain": gain, "better": better, "worse": worse,
               "accepted": gain >= 0.05}
    print(json.dumps(verdict, indent=1))
    out = ROOT / "runs" / f"gate_{a.seed0}.json"
    out.write_text(json.dumps(verdict, indent=1))
    print("saved ->", out)


if __name__ == "__main__":
    main()
