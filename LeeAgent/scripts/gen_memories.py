"""Roadmap 6: programmatic memory generation (no LLM distillation).

The first distillation batch (agent logs -> deepseek) was fully gate-rejected:
a mid-level agent's own games carry no incremental signal. These candidates
are templated from ENVIRONMENT DATA instead - the empirical hero table and
the catalog engine density - and the paired gate arbitrates every family:

  tempo   top-quartile heroes (measured mean_place) climb tiers turn 6-9
  hold    bottom-quartile heroes keep gold on board turn 5-7
  commit  dense tribes commit direction early (turn 4, 2 minions)
  climb   low health late: spend on tier, not board

    ../.venv/bin/python scripts/gen_memories.py [--out memories/generated.jsonl]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def gen() -> list[dict]:
    out = []
    hero_table = json.loads((ROOT / "data" / "hero_table.json").read_text())
    ranked = sorted(hero_table.items(), key=lambda kv: kv[1]["mean_place"])
    n = len(ranked)
    top = ranked[: n // 4]                      # best quartile: LOWER place
    bot = ranked[-(n // 4):]

    def add(mid, kind, when, situation, action, rationale, bias):
        out.append({"id": mid, "kind": kind, "when": when, "situation": situation,
                    "action": action, "rationale": rationale, "bias": bias,
                    "provenance": {"status": "candidate", "ab_gain": None,
                                   "n_games": 0,
                                   "source": "gen_memories 2026-11-04"}})

    for hid, t in top:
        add(f"G-TEMPO-{hid}", "econ",
            {"hero_in": [hid], "turn_min": 6, "turn_max": 9},
            f"Playing {hid} (measured mean place {t['mean_place']:.2f}, n={t['n']}), "
            "mid game, upgrade affordable",
            "Prefer upgrading the tavern over marginal buys",
            f"Top-quartile hero by bot self-play ({t['n']} games); tier tempo "
            "compounds a strong hero power",
            {"prefer_upgrade": 4})
    for hid, t in bot:
        add(f"G-HOLD-{hid}", "econ",
            {"hero_in": [hid], "turn_min": 5, "turn_max": 7},
            f"Playing {hid} (measured mean place {t['mean_place']:.2f}, n={t['n']}), "
            "early-mid game",
            "Keep gold on minions; do not chase tiers yet",
            f"Bottom-quartile hero by bot self-play ({t['n']} games); the board "
            "must carry the weaker hero power first",
            {"hold_upgrade": True})

    from leeagent.comp import engine_density
    dens = engine_density()
    med = sorted(dens.values())[len(dens) // 2]
    for tribe, d in sorted(dens.items(), key=lambda kv: -kv[1])[:5]:
        if d < med:
            break
        add(f"G-COMMIT-{tribe}", "comp",
            {"turn_min": 4, "tribe_min": {tribe: 2}},
            f"Two {tribe} minions on board by turn 4 and {tribe} has {d} "
            "scaling engines in the catalog",
            f"Commit the comp direction to {tribe} now",
            f"{tribe} engine density {d} (upper half of the pool); early "
            "commitment beats waiting for the third minion",
            {"commit_tribe": tribe})

    add("G-CLIMB-LOWHP", "econ",
        {"turn_min": 9, "hp_below": 16},
        "Late game, health below 16 - one more lost fight is fatal",
        "Spend on tavern tier over board minions",
        "Placement damage from a stronger tier outweighs marginal board value "
        "at death's door",
        {"prefer_upgrade": 5})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "memories" / "generated.jsonl"))
    a = ap.parse_args()
    cands = gen()
    with open(a.out, "w") as f:
        for m in cands:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    fam = {}
    for m in cands:
        fam[m["id"].split("-")[1]] = fam.get(m["id"].split("-")[1], 0) + 1
    print(f"{len(cands)} candidates -> {a.out}  families: {fam}")


if __name__ == "__main__":
    main()
