"""Live-side no-regression check for the strategy A/B experiment (2026-11-04).

The bench arbitration variants (bot-continuation arm, paired salts) live
entirely in scripts/strategy_ab.py and patched answer files; leeagent/ itself
is untouched. This script proves it empirically: replay seeds 1800-1899 (an
already-burned segment, freeze_bias_fresh control arm) with the current
policy defaults and compare per-seed placements to the recorded run.
Deterministic engine + deterministic agent => byte-identical expected.

    ../.venv/bin/python scripts/live_recheck.py
"""

from __future__ import annotations

import json
import multiprocessing as mp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run(seed):
    from leeagent import gate
    from leeagent import memory as M
    from leeagent.config import ROOT as CFG_ROOT, thresholds
    bank = M.load(CFG_ROOT / "memories" / "seed.jsonl")
    a = gate.LeeAgent(bank, th=thresholds(), use_nimble=False)
    return seed, a.run_game(seed, seat=0)["placement"]


def main():
    ref = json.loads((ROOT / "runs" / "freeze_bias_fresh.json").read_text())
    rec = ref["seeds_1800_1899"]
    ref_place = dict(zip(range(rec["seeds"][0], rec["seeds"][1] + 1),
                         rec["placements_off"]))
    seeds = sorted(ref_place)

    with mp.Pool(96) as pool:
        got = dict(pool.imap_unordered(run, seeds))

    diff = {s: (ref_place[s], got[s]) for s in seeds if ref_place[s] != got[s]}
    top4_ref = sum(1 for p in ref_place.values() if p <= 4)
    top4_got = sum(1 for p in got.values() if p <= 4)
    out = {
        "seeds": [min(seeds), max(seeds)], "n": len(seeds),
        "byte_identical": not diff,
        "mismatches": diff,
        "mean_place_ref": round(sum(ref_place.values()) / len(seeds), 3),
        "mean_place_now": round(sum(got.values()) / len(seeds), 3),
        "top4_ref": top4_ref, "top4_now": top4_got,
    }
    (ROOT / "runs" / "live_recheck_1800.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "mismatches"}, indent=1))
    if diff:
        print(f"MISMATCH x{len(diff)}, first: {list(diff.items())[:5]}")


if __name__ == "__main__":
    main()
