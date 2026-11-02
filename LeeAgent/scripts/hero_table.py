"""Empirical hero strength table: every pool hero played K full games by v16.

During seat 0's hero select, the target hero is injected with the engine's
offer_hero debug command (replaces the first option), chosen, and the game is
played out with the LeeAgent policy against seven scripted bots. The table
maps hero id -> mean placement.

    ../.venv/bin/python scripts/hero_table.py [--games 16]
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def hero_unit(args):
    hero_id, seed = args
    import taverngym
    from leeagent import gate
    from leeagent.config import thresholds
    from leeagent import memory

    g = taverngym.Game(seed=seed)
    agent = gate.LeeAgent(memory.load(ROOT / "memories" / "seed.jsonl"),
                          th=thresholds(), use_nimble=False)
    agent.reset()
    agent._turn_seen = -1
    forced = False
    guard = 0
    while not g.is_over() and guard < 100000:
        for p in range(g.num_players):
            if not g.needs_action(p):
                continue
            if p == 0 and not forced:
                view = json.loads(g.view(0))
                pend = view["me"].get("pending") or {}
                if pend.get("kind") == "hero":
                    g.debug(json.dumps({"cmd": "offer_hero", "p": 0, "hero": hero_id}))
                    pend = (json.loads(g.view(0))["me"].get("pending") or {})
                    for k, o in enumerate(pend.get("options") or []):
                        if o.get("id") == hero_id:
                            g.step(0, 30 + k)
                            forced = True
                            break
                    if forced:
                        continue
            g.step(p, agent.choose(g, p) if p == 0 else g.bot_action(p))
        guard += 1
    return hero_id, int(list(g.placements())[0]) if g.is_over() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=16)
    ap.add_argument("--seed0", type=int, default=50000)
    a = ap.parse_args()

    import taverngym
    catalog = json.loads(taverngym.catalog_json())
    heroes = [c["id"] for c in catalog
              if c["kind"] == "hero" and c.get("in_pool") and c.get("implemented")]
    print(f"{len(heroes)} pool heroes x {a.games} games", flush=True)

    jobs = [(h, a.seed0 + i) for h in heroes for i in range(a.games)]
    results = {}
    with mp.Pool(96) as pool:
        for hid, pl in pool.imap_unordered(hero_unit, jobs, chunksize=8):
            if pl is not None:
                results.setdefault(hid, []).append(pl)
    table = {h: {"n": len(v), "mean_place": round(sum(v) / len(v), 3)}
             for h, v in sorted(results.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))}
    out = ROOT / "data" / "hero_table.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(table, indent=1))
    best = list(table.items())[:8]
    worst = list(table.items())[-5:]
    print("top8:", [(h, v["mean_place"]) for h, v in best])
    print("bottom5:", [(h, v["mean_place"]) for h, v in worst])
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
