"""Self-play trajectory data for the value model (roadmap step 7).

Every game played by v16 logs one (features, final_reward) row per action the
agent takes — mid-turn states included, which is exactly what the bench's
turn-plan discrimination needs.

    ../.venv/bin/python scripts/gen_trajectories.py [--games 5000]
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TRIBES = ("BEAST", "DRAGON", "MECH", "MURLOC", "UNDEAD",
          "DEMON", "ELEMENTAL", "PIRATE", "QUILBOAR")


def feat_row(view: dict, facts: dict, comp) -> list:
    board = view["me"].get("board") or []
    atk = sum(m.get("atk", 0) for m in board)
    hp = sum(m.get("hp", 0) for m in board)
    row = [facts["turn"], facts["tier"], facts["gold"], facts["health"], facts["armor"],
           facts["hand_count"], facts["board_count"], atk / 10.0, hp / 10.0,
           facts["num_alive"], facts["upgrade_price"] or 0, facts["win_streak"],
           1.0 if facts["hand_full"] else 0.0, 1.0 if facts["board_full"] else 0.0]
    row += [facts["tribes"].get(t, 0) for t in TRIBES]
    row += [1.0 if comp == t else 0.0 for t in TRIBES]
    return row


def play_game(seed):
    import json
    import taverngym
    from leeagent import gate, memory
    from leeagent.config import thresholds
    from leeagent.facts import extract_facts

    agent = gate.LeeAgent(memory.load(ROOT / "memories" / "seed.jsonl"),
                          th=thresholds(), use_nimble=False)
    agent.reset()
    agent._turn_seen = -1
    g = taverngym.Game(seed=seed)
    rows = []
    guard = 0
    while not g.is_over() and guard < 100000:
        for p in range(g.num_players):
            if not g.needs_action(p):
                continue
            if p == 0:
                view = json.loads(g.view(0))
                facts = extract_facts(view)
                if not facts["pending"]:
                    rows.append(feat_row(view, facts, agent._comp))
                g.step(p, agent.choose(g, p))
            else:
                g.step(p, g.bot_action(p))
        guard += 1
    if not g.is_over():
        return None
    placement = int(list(g.placements())[0])
    reward = 1 - 2 * (placement - 1) / 7
    return rows, reward


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=5000)
    ap.add_argument("--seed0", type=int, default=70000)
    a = ap.parse_args()
    X, y = [], []
    with mp.Pool(96) as pool:
        for out in pool.imap_unordered(play_game, range(a.seed0, a.seed0 + a.games),
                                       chunksize=8):
            if out is None:
                continue
            rows, reward = out
            for r in rows:
                X.append(r)
                y.append(reward)
    import numpy as np
    np.savez_compressed(ROOT / "data" / "trajectories.npz",
                        X=np.array(X, dtype=np.float32), y=np.array(y, dtype=np.float32))
    print(f"{len(y)} rows from {a.games} games -> data/trajectories.npz")


if __name__ == "__main__":
    main()
