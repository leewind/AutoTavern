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
    """v2: the v1 scalars plus hand/shop/board/opp-scout/comp content."""
    me = view["me"]
    board = me.get("board") or []
    hand = me.get("hand") or []
    shop = me.get("shop") or []
    atk = sum(m.get("atk", 0) for m in board)
    hp = sum(m.get("hp", 0) for m in board)

    def tier_hist(cards):
        h = [0] * 7
        for c in cards:
            t = c.get("tier") or 0
            if 0 <= t <= 6:
                h[t] += 1
        return h

    hand_minions = [c for c in hand if c.get("type") != "spell"]
    hand_spells = len(hand) - len(hand_minions)
    kw = {"TAUNT": 0, "DIVINE_SHIELD": 0, "VENOMOUS": 0, "REBORN": 0, "WINDFURY": 0}
    for m in board:
        for k in kw:
            if k in (m.get("keywords") or []):
                kw[k] += 1
    nxt = facts.get("next_opponent")
    entry = next((o for o in view.get("opponents") or [] if o.get("id") == nxt), None) \
        if nxt is not None else None
    seen = (entry or {}).get("seen_board") or []
    opp_n = len(seen)
    opp_atk = sum(m.get("atk", 0) for m in seen) / 10.0
    comp_count = facts["tribes"].get(comp, 0) if comp else 0
    comp_engines = sum(1 for m in board if comp in [
        r.upper().replace("MECHANICAL", "MECH") for r in (m.get("races") or [])]
        and any(k in (m.get("text") or "").lower()
                for k in ("whenever", "each turn", "after you", "gains +"))) if comp else 0

    row = [facts["turn"], facts["tier"], facts["gold"], facts["health"], facts["armor"],
           facts["hand_count"], facts["board_count"], atk / 10.0, hp / 10.0,
           facts["num_alive"], facts["upgrade_price"] or 0, facts["win_streak"],
           1.0 if facts["hand_full"] else 0.0, 1.0 if facts["board_full"] else 0.0,
           len(hand_minions), hand_spells,
           1.0 if facts["hand_dup_in_shop"] else 0.0,
           max((c.get("atk", 0) + c.get("hp", 0) + 3 * (c.get("tier") or 0)
                for c in shop if c.get("type") != "spell"), default=0) / 10.0,
           kw["TAUNT"], kw["DIVINE_SHIELD"], kw["VENOMOUS"], kw["REBORN"], kw["WINDFURY"],
           opp_n, opp_atk,
           1.0 if facts["opp_seen_more"] else 0.0, 1.0 if facts["next_is_ghost"] else 0.0,
           comp_count, comp_engines]
    row += tier_hist(hand)
    row += tier_hist(shop)
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
    import numpy as np
    # large runs stream into float32 shards: 100k games would be ~8M rows
    # and >30GB as python lists
    X_parts, y_parts, X, y, done = [], [], [], [], 0
    with mp.Pool(96) as pool:
        for out in pool.imap_unordered(play_game, range(a.seed0, a.seed0 + a.games),
                                       chunksize=8):
            if out is None:
                continue
            rows, reward = out
            X.extend(rows)
            y.extend([reward] * len(rows))
            done += 1
            if done % 5000 == 0:
                print(f"{done}/{a.games} games, {len(y)} rows", flush=True)
            if len(y) >= 2_000_000:
                X_parts.append(np.asarray(X, dtype=np.float32))
                y_parts.append(np.asarray(y, dtype=np.float32))
                X, y = [], []
    if X:
        X_parts.append(np.asarray(X, dtype=np.float32))
        y_parts.append(np.asarray(y, dtype=np.float32))
    Xa = np.vstack(X_parts) if X_parts else np.zeros((0, 0), dtype=np.float32)
    ya = np.concatenate(y_parts) if y_parts else np.zeros((0,), dtype=np.float32)
    np.savez_compressed(ROOT / "data" / "trajectories.npz", X=Xa, y=ya)
    print(f"{len(ya)} rows from {done} games -> data/trajectories.npz")


if __name__ == "__main__":
    main()
