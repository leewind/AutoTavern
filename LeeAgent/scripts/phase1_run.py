"""Phase-1 batch: expanded baseline + calibration, Nimble serialized.

Arms (paired seeds, seat 0):
  bot       the built-in scripted bot (reference)
  code      LeeAgent, code-only prefilter (no Nimble)
  nimble    LeeAgent, full hot path
plus the judgment calibration set (scripts/calibrate.py logic).

Everything appends to runs/phase1_batch.json so partial progress survives.
Nimble is single-concurrency: calibration runs between the code and nimble
arms, never alongside them.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import taverngym                                # noqa: E402

from leeagent import gate, memory               # noqa: E402
from leeagent.config import thresholds          # noqa: E402
from scripts.calibrate import probe, sample_states, summarize  # noqa: E402


def bot_arm(seeds):
    places = []
    for s in seeds:
        g = taverngym.Game(seed=s)
        while not g.is_over():
            for seat in range(g.num_players):
                if g.needs_action(seat):
                    g.step(seat, g.bot_action(seat))
        places.append(int(list(g.placements())[0]))
    rewards = [1 - 2 * (p - 1) / 7 for p in places]
    return {"placements": places, "mean_reward": round(sum(rewards) / len(rewards), 4),
            "first_places": sum(1 for p in places if p == 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed0", type=int, default=300)
    ap.add_argument("--cal-games", type=int, default=12)
    ap.add_argument("--cal-seed0", type=int, default=900)
    a = ap.parse_args()
    seeds = list(range(a.seed0, a.seed0 + a.n))
    out_path = ROOT / "runs" / "phase1_batch.json"
    out = {"seeds": [a.seed0, a.seed0 + a.n - 1], "n": a.n}

    t0 = time.time()
    print("arm: bot", flush=True)
    out["bot"] = bot_arm(seeds)
    print(f"  {out['bot']}  ({time.time()-t0:.0f}s)", flush=True)

    t0 = time.time()
    print("arm: code-only", flush=True)
    store = memory.load(ROOT / "memories" / "seed.jsonl")
    r = gate.run_games(store, seeds, use_nimble=False, th=thresholds())
    out["code"] = {"placements": [x["placement"] for x in r["results"]],
                   "mean_reward": r["mean_reward"],
                   "first_places": r["first_places"]}
    print(f"  mean={out['code']['mean_reward']} ({time.time()-t0:.0f}s)", flush=True)
    out_path.write_text(json.dumps(out, indent=1))

    t0 = time.time()
    print("arm: calibration", flush=True)
    states = sample_states(range(a.cal_seed0, a.cal_seed0 + a.cal_games), 3)
    rows = probe(states, None or ["M011", "M007", "M023", "M019", "M012"], thresholds())
    (ROOT / "runs").mkdir(exist_ok=True)
    (ROOT / "runs" / "calibration_rows.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    out["calibration"] = summarize(rows)
    print(f"  judgments={out['calibration']['n_judgments']} "
          f"best_t={out['calibration']['best_threshold']} ({time.time()-t0:.0f}s)", flush=True)
    out_path.write_text(json.dumps(out, indent=1))

    t0 = time.time()
    print("arm: nimble (long)", flush=True)
    r2 = gate.run_games(store, seeds, use_nimble=True, th=thresholds())
    out["nimble"] = {"placements": [x["placement"] for x in r2["results"]],
                     "mean_reward": r2["mean_reward"],
                     "first_places": r2["first_places"],
                     "mean_nimble_s_per_game": round(r2["mean_nimble_ms_per_game"] / 1000, 1)}
    print(f"  mean={out['nimble']['mean_reward']} ({time.time()-t0:.0f}s)", flush=True)
    out_path.write_text(json.dumps(out, indent=1))
    print("done ->", out_path, flush=True)


if __name__ == "__main__":
    main()
