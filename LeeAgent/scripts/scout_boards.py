"""Turn-indexed opponent-board pools for synthetic scouting (roadmap 5).

Pure-bot games (no LeeAgent — eight scripted seats): every seat's board is
recorded each turn it acts, giving the distribution of real boards a
scouting preview should be averaged over. Construction seeds only.

    ../.venv/bin/python scripts/scout_boards.py [--games 3000] [--seed0 120000]
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TURNS = range(3, 17)          # fight-relevant turns
CAP = 300                     # boards kept per turn


def collect_game(seed):
    import taverngym

    g = taverngym.Game(seed=seed)
    seen = {}                 # (turn, seat) -> board json
    guard = 0
    while not g.is_over() and guard < 200000:
        for p in range(g.num_players):
            if not g.needs_action(p):
                continue
            v = json.loads(g.view(p))
            t = v["turn"]
            if t in TURNS and (t, p) not in seen:
                me = v["me"]
                board = [{"id": c.get("id"), "atk": c.get("atk", 0),
                          "hp": c.get("hp", 0), "golden": bool(c.get("golden"))}
                         for c in (me.get("board") or [])]
                seen[(t, p)] = {"turn": t, "tier": me.get("tier", 1),
                                "board": board}
            g.step(p, g.bot_action(p))
        guard += 1
    if not g.is_over():
        return None
    return list(seen.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=3000)
    ap.add_argument("--seed0", type=int, default=120_000)
    a = ap.parse_args()
    pools: dict[int, list] = {}
    n_games = 0
    with mp.Pool(96) as pool:
        for recs in pool.imap_unordered(collect_game,
                                        range(a.seed0, a.seed0 + a.games),
                                        chunksize=8):
            if recs is None:
                continue
            n_games += 1
            for r in recs:
                pools.setdefault(r["turn"], []).append(
                    [r["tier"], r["board"]])
    out = {}
    for t, rows in pools.items():
        random.seed(t)
        random.shuffle(rows)
        tiers = [r[0] for r in rows[:CAP]]
        out[str(t)] = {"avg_tier": round(sum(tiers) / len(tiers), 2),
                       "boards": [r[1] for r in rows[:CAP]]}
    p = ROOT / "data" / "scout_boards.json"
    p.write_text(json.dumps(out))
    print(f"{n_games} games; per-turn pools:",
          {t: len(v["boards"]) for t, v in sorted(out.items())})
    print(f"-> {p}")


if __name__ == "__main__":
    main()
