"""Synthetic-board scouting (roadmap 5): preview danger against the turn's
board DISTRIBUTION instead of one opponent snapshot.

The snapshot goes stale between scout time and the actual fight (the
opponent keeps buying); averaging combat previews over K real boards from
turn T measures "how do I fare against the field right now" with no
dependence on any single opponent's state.

Board pools: scripts/scout_boards.py (pure-bot games, construction seeds).
"""
from __future__ import annotations

import json
import random
from functools import lru_cache
from pathlib import Path

K_BOARDS = 4          # synthetic boards averaged per scout
N_SIMS = 16           # combat_preview sims per board


@lru_cache(maxsize=1)
def _pools() -> dict:
    p = Path(__file__).resolve().parents[1] / "data" / "scout_boards.json"
    return json.loads(p.read_text()) if p.is_file() else {}


def danger(game, seat: int, turn: int, k: int = K_BOARDS,
           n: int = N_SIMS) -> float | None:
    """Mean win rate (+ half ties) of `seat` vs K sampled turn-T boards.
    Each preview runs on a throwaway copy: a builder seat's board is
    cleared and rebuilt from the pool entry (base id + golden + stats)."""
    pool = _pools().get(str(turn))
    if not pool:
        return None
    rng = random.Random((seat + 1) * 1_000_003 + turn)
    boards = rng.sample(pool["boards"], min(k, len(pool["boards"])))
    scores = []
    for members in boards:
        g2 = game.copy()
        try:
            q = next(c % 8 for c in (seat + 1, seat + 2, seat + 3)
                     if (vb := json.loads(g2.view(c % 8))) is not None
                     and "me" in vb)
            for _ in (json.loads(g2.view(q))["me"].get("board") or []):
                g2.debug(json.dumps({"cmd": "remove", "p": q,
                                     "zone": "board", "index": 0}))
            for i, m in enumerate(members):
                cid = m["id"] or ""
                if cid.endswith("_G"):
                    cid = cid[:-2]
                if not cid:
                    continue
                g2.debug(json.dumps({
                    "cmd": "add_minion", "p": q, "zone": "board",
                    "card": cid, "pos": i, "golden": m.get("golden", False),
                    "atk": m.get("atk"), "hp": m.get("hp")}))
            g2.debug(json.dumps({"cmd": "set_player", "p": q,
                                 "tier": int(pool["avg_tier"])}))
            out = json.loads(g2.debug(json.dumps(
                {"cmd": "combat_preview", "a": seat, "b": q, "n": n})))
            scores.append(float(out.get("win_a", 0.0))
                          + 0.5 * float(out.get("tie", 0.0)))
        except Exception:
            continue
    if not scores:
        return None
    return sum(scores) / len(scores)
