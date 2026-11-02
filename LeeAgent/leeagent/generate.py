"""Cold path: distill one finished game into candidate memory triples.

One deepseek call per game (thinking disabled — the same protocol as our
TavernBench runs). The candidates are *not* trusted: they carry
provenance.status = "candidate" and only the A/B gate can promote them.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from leeagent import memory                          # noqa: E402
from leeagent.config import BENCH_ENV_FILE, thresholds  # noqa: E402

SYSTEM = """You distill Hearthstone Battlegrounds games into reusable memories for a game-playing agent.
Return a JSON array of at most {n} objects, each:
{{"kind": "econ|position|comp|target|strategy",
  "when": {{...}},      // exact, code-checked preconditions; vocabulary:
                       // turn_min, turn_max, tier_min, tier_max, hp_below, hp_above,
                       // gold_gte, gold_lte, board_count_gte, num_alive_lte,
                       // hand_full, board_full, next_is_ghost,
                       // tribe_min: {{TRIBE: n}}, shop_tribe_min: {{TRIBE: n}}, any_keyword: [KW]
                       // use {} for anything you cannot pin down exactly
  "situation": "...",  // <=18 English words, only the part code cannot check
  "action": "...",     // one concrete instruction
  "rationale": "...",  // why it wins games
  "bias": {{...}}}     // optional machine instruction, vocabulary:
                       // prefer_buy_tribe, prefer_buy_any, prefer_upgrade, prefer_freeze,
                       // prefer_endturn, prefer_play, penalize_endturn_with_gold, sell_to_trigger
Only propose a memory if this game gave real evidence for it. [] if none."""


def read_env(path: Path) -> dict:
    out = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip().removeprefix("export ").strip()] = v.strip().strip('"').strip("'")
    return out


def distill(game_result: dict, store: list, th: dict | None = None, env_file: Path = BENCH_ENV_FILE) -> list:
    th = th or thresholds()
    env = read_env(env_file)
    from openai import OpenAI
    client = OpenAI(api_key=env.get("API_KEY"), base_url=(env.get("API_BASE") or "").rstrip("/") or None,
                    max_retries=2)

    turn_lines = []
    for t in game_result.get("turns", []):
        turn_lines.append(f"turn {t['turn']}: gold {t['gold']} hp {t['health']} tier {t['tier']} "
                          f"matched {[m for m, _ in t.get('matched', [])]} acts {t.get('actions', [])}")
    prompt = (f"Placement: {game_result['placement']} of 8.\n"
              f"Existing memory ids: {[m['id'] for m in store]} — do not duplicate them.\n\n"
              + "\n".join(turn_lines))

    rsp = client.chat.completions.create(
        model=env.get("MODEL", "deepseek-chat"),
        messages=[{"role": "system", "content": SYSTEM.format(n=th["max_new_candidates"], when="{}")},
                  {"role": "user", "content": prompt}],
        max_tokens=1500, temperature=0.2,
        extra_body={"thinking": {"type": "disabled"}})
    text = rsp.choices[0].message.content or ""
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return []
    try:
        raw = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    if isinstance(raw, dict):
        raw = [raw]

    out = []
    for d in raw[:th["max_new_candidates"]]:
        if not isinstance(d, dict) or d.get("kind") not in ("econ", "position", "comp", "target", "strategy"):
            continue
        cand = {"id": memory.new_id(store + out), "kind": d["kind"],
                "when": d.get("when") or {}, "situation": str(d.get("situation", ""))[:200],
                "action": str(d.get("action", ""))[:200], "rationale": str(d.get("rationale", ""))[:300],
                "bias": {k: v for k, v in (d.get("bias") or {}).items()
                         if k in ("prefer_buy_tribe", "prefer_buy_any", "prefer_upgrade",
                                  "prefer_freeze", "prefer_endturn", "prefer_play",
                                  "penalize_endturn_with_gold", "sell_to_trigger")},
                "provenance": {"status": "candidate", "ab_gain": None, "n_games": 0,
                               "source_game": game_result.get("seed")}}
        if memory.validate(cand):
            out.append(cand)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True, help="runs/game_*.json from play_one.py")
    ap.add_argument("--store", default=str(Path(__file__).resolve().parents[1] / "memories" / "seed.jsonl"))
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "memories" / "candidates.jsonl"))
    a = ap.parse_args()
    result = json.loads(Path(a.log).read_text())
    store = memory.load(a.store)
    cands = distill(result, store)
    path = Path(a.out)
    with path.open("a") as f:
        for c in cands:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"{len(cands)} candidates appended to {path}")
    for c in cands:
        print(" ", c["id"], c["kind"], "|", c["situation"][:70])


if __name__ == "__main__":
    main()
