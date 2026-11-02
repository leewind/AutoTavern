"""A/B verification gate: same seeds, memory set A vs set B.

Accepts B only if its mean placement reward beats A's by >= gate_min_gain.
Paired seeds kill game-luck: both sides face identical lobbies and combats.
This is the only path that marks a memory `verified`.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import memory
from .agent import LeeAgent
from .config import thresholds


def run_games(store: list, seeds, use_nimble: bool = True, seat: int = 0, th: dict | None = None) -> dict:
    th = th or thresholds()
    results = []
    for seed in seeds:
        agent = LeeAgent(store, th=th, use_nimble=use_nimble)
        results.append(agent.run_game(seed, seat=seat))
    rewards = [r["reward"] for r in results]
    return {"n": len(results),
            "mean_reward": round(sum(rewards) / len(rewards), 4) if rewards else 0.0,
            "first_places": sum(1 for r in results if r["placement"] == 1),
            "mean_nimble_ms_per_game": round(
                sum(r["stats"]["nimble_ms"] for r in results) / max(len(results), 1), 0),
            "results": results}


def ab_test(store_a: list, store_b: list, n_games: int = 40, seed0: int = 10_000,
            use_nimble: bool = True, th: dict | None = None) -> dict:
    th = th or thresholds()
    seeds = list(range(seed0, seed0 + n_games))
    a = run_games(store_a, seeds, use_nimble=use_nimble, th=th)
    b = run_games(store_b, seeds, use_nimble=use_nimble, th=th)
    gain = round(b["mean_reward"] - a["mean_reward"], 4)
    return {"accepted": gain >= th["gate_min_gain"], "gain": gain,
            "threshold": th["gate_min_gain"],
            "a": {k: v for k, v in a.items() if k != "results"},
            "b": {k: v for k, v in b.items() if k != "results"}}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default=str(Path(__file__).resolve().parents[1] / "memories" / "seed.jsonl"))
    ap.add_argument("--b", required=True)
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--no-nimble", action="store_true")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    th = thresholds()
    verdict = ab_test(memory.load(a.a), memory.load(a.b),
                      n_games=a.n or th["gate_n_games"], use_nimble=not a.no_nimble, th=th)
    print(json.dumps(verdict, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(verdict, indent=2))
        print("saved:", a.out)


if __name__ == "__main__":
    main()
