"""Self-play log of buy events with board context (synergy-table input).

Every minion buy logs (card, board-at-buy-time, committed direction); the
game's final placement supplies the reward. Same seed segment discipline as
the other table builders: construction-only seeds, never for reporting.

    ../.venv/bin/python scripts/synergy_gen.py [--games 10000] [--seed0 90000]
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def norm_cid(c: dict) -> str | None:
    """Base card id (goldens count as their base card being present)."""
    cid = c.get("id")
    if not cid:
        return None
    return cid[:-2] if cid.endswith("_G") else cid


def play_game(seed):
    import taverngym
    from leeagent import gate, memory
    from leeagent.config import thresholds
    from leeagent.policy import card_quality, decode

    agent = gate.LeeAgent(memory.load(ROOT / "memories" / "seed.jsonl"),
                          th=thresholds(), use_nimble=False)
    agent.reset()
    agent._turn_seen = -1
    g = taverngym.Game(seed=seed)
    buys = []              # [S, [board ids], comp, turn, health, boardq]
    guard = 0
    while not g.is_over() and guard < 100000:
        for p in range(g.num_players):
            if not g.needs_action(p):
                continue
            if p == 0:
                view = json.loads(g.view(0))
                act = agent.choose(g, 0)
                d = decode(act)
                if d[0] == "buy":
                    shop = view["me"].get("shop") or []
                    card = shop[d[1]] if d[1] < len(shop) else {}
                    if card.get("type") != "spell":
                        me = view["me"]
                        board = me.get("board") or []
                        buys.append([norm_cid(card),
                                     [norm_cid(m) for m in board],
                                     agent._comp, view["turn"],
                                     me.get("health", 30),
                                     round(sum(card_quality(m) for m in board), 1)])
                g.step(p, act)
            else:
                g.step(p, g.bot_action(p))
        guard += 1
    if not g.is_over():
        return None
    place = int(list(g.placements())[0])
    return {"seed": seed, "place": place, "reward": 1 - 2 * (place - 1) / 7,
            "buys": buys}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=10000)
    ap.add_argument("--seed0", type=int, default=90000)
    a = ap.parse_args()
    n = 0
    out_path = ROOT / "data" / "synergy_games.jsonl"
    with mp.Pool(96) as pool, out_path.open("w") as f:
        for rec in pool.imap_unordered(play_game, range(a.seed0, a.seed0 + a.games),
                                       chunksize=8):
            if rec is None:
                continue
            f.write(json.dumps(rec) + "\n")
            f.flush()
            n += 1
    print(f"{n} games -> {out_path}")


if __name__ == "__main__":
    main()



if __name__ == "__main__":
    main()
