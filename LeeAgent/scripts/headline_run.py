"""Headline live evaluation on a fresh seed segment (deployed policy vs bot).

Paired on the same seeds: seat 0 plays the deployed LeeAgent (current
module defaults -- includes the adopted LATE_SEARCH) against the engine's
seven scripted bots; the reference arm plays the pure scripted bot.
    ../.venv/bin/python scripts/headline_run.py [--seed0 2000] [--n 100]
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def agent_game(seed):
    from leeagent import gate, memory
    from leeagent.config import ROOT as CFG_ROOT, thresholds
    bank = memory.load(CFG_ROOT / "memories" / "seed.jsonl")
    a = gate.LeeAgent(bank, th=thresholds(), use_nimble=False)
    return seed, a.run_game(seed, seat=0)["placement"]


def bot_game(seed):
    import taverngym
    g = taverngym.Game(seed=seed)
    guard = 0
    while not g.is_over() and guard < 100000:
        for p in range(g.num_players):
            if g.needs_action(p):
                g.step(p, g.bot_action(p))
        guard += 1
    return seed, int(list(g.placements())[0]) if g.is_over() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed0", type=int, default=2000)
    ap.add_argument("--n", type=int, default=100)
    a = ap.parse_args()
    seeds = list(range(a.seed0, a.seed0 + a.n))
    with mp.Pool(96) as pool:
        agent = dict(pool.imap_unordered(agent_game, seeds))
        bot = dict(pool.imap_unordered(bot_game, seeds))
    t4a = sum(1 for p in agent.values() if p <= 4)
    t4b = sum(1 for p in bot.values() if p <= 4)
    out = {
        "seeds": [a.seed0, a.seed0 + a.n - 1], "n": a.n,
        "agent_top4": t4a, "agent_mean_place": round(sum(agent.values()) / a.n, 3),
        "bot_top4": t4b, "bot_mean_place": round(sum(bot.values()) / a.n, 3),
        "placements_agent": [agent[s] for s in seeds],
        "placements_bot": [bot[s] for s in seeds],
    }
    path = ROOT / "runs" / f"headline_{a.seed0}_{a.seed0 + a.n - 1}.json"
    path.write_text(json.dumps(out, indent=1))
    print(f"seeds {a.seed0}-{a.seed0 + a.n - 1}: "
          f"agent 前四 {t4a}/{a.n} = {t4a / a.n:.1%}, "
          f"均名 {out['agent_mean_place']}  |  "
          f"bot 前四 {t4b}/{a.n} = {t4b / a.n:.1%}, "
          f"均名 {out['bot_mean_place']}  -> {path.name}")


if __name__ == "__main__":
    main()
