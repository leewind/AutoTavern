"""The memory bank: situation-action-rationale triples behind a code prefilter.

One jsonl line per memory:
  id, kind, when{...}, situation, action, rationale, bias{...}, provenance{...}

`when` is matched exactly by code (free, no tokens); `situation` is the semantic
residue Nimble judges; `bias` is the machine-readable instruction the policy
executes (vocabulary in policy.py). Unknown `when` keys are ignored, so generated
memories may extend the vocabulary without breaking old entries.
"""

from __future__ import annotations

import json
from pathlib import Path

REQUIRED = ("id", "kind", "when", "situation", "action", "rationale")


def matches(when: dict, facts: dict) -> bool:
    w = when or {}
    if "turn_min" in w and facts["turn"] < w["turn_min"]:
        return False
    if "turn_max" in w and facts["turn"] > w["turn_max"]:
        return False
    if "tier_min" in w and facts["tier"] < w["tier_min"]:
        return False
    if "tier_max" in w and facts["tier"] > w["tier_max"]:
        return False
    if "hp_below" in w and not facts["health"] < w["hp_below"]:
        return False
    if "hp_above" in w and not facts["health"] > w["hp_above"]:
        return False
    if "gold_gte" in w and facts["gold"] < w["gold_gte"]:
        return False
    if "gold_lte" in w and facts["gold"] > w["gold_lte"]:
        return False
    if "board_count_gte" in w and facts["board_count"] < w["board_count_gte"]:
        return False
    if "board_count_lte" in w and facts["board_count"] > w["board_count_lte"]:
        return False
    if "num_alive_lte" in w and facts["num_alive"] > w["num_alive_lte"]:
        return False
    if "win_streak_gte" in w and facts["win_streak"] < w["win_streak_gte"]:
        return False
    if w.get("hand_dup_in_shop") and not facts["hand_dup_in_shop"]:
        return False
    if w.get("opp_seen_more_minions") and not facts["opp_seen_more"]:
        return False
    if "opp_seen_keyword" in w and w["opp_seen_keyword"] not in facts["opp_seen_keywords"]:
        return False
    if w.get("board_text_has") and not any(
            all(s.lower() in t.lower() for s in w["board_text_has"])
            for t in facts["board_texts"]):
        return False
    for flag in ("hand_full", "board_full", "next_is_ghost"):
        if w.get(flag) is not None and bool(facts.get(flag)) != bool(w[flag]):
            return False
    for t, n in (w.get("tribe_min") or {}).items():
        if facts["tribes"].get(t, 0) < n:
            return False
    for t, n in (w.get("shop_tribe_min") or {}).items():
        if facts["shop_tribes"].get(t, 0) < n:
            return False
    if w.get("any_keyword") and not set(w["any_keyword"]) & set(facts["keywords"]):
        return False
    return True


def specificity(when: dict) -> int:
    """Constraint count: more constraints = more specific = ask Nimble first."""
    w = when or {}
    n = sum(1 for k in ("turn_min", "turn_max", "tier_min", "tier_max", "hp_below",
                        "hp_above", "gold_gte", "gold_lte", "board_count_gte",
                        "board_count_lte", "num_alive_lte", "win_streak_gte",
                        "hand_dup_in_shop", "opp_seen_more_minions", "opp_seen_keyword",
                        "hand_full", "board_full", "next_is_ghost")
            if w.get(k) is not None)
    n += sum(w.get("tribe_min", {}).values()) + sum(w.get("shop_tribe_min", {}).values())
    n += len(w.get("any_keyword") or [])
    return n


def prefilter(store: list, facts: dict, limit: int = 16) -> list:
    hit = [m for m in store if matches(m.get("when") or {}, facts)]
    hit.sort(key=lambda m: (-specificity(m.get("when") or {}), str(m.get("id"))))
    return hit[:limit]


def slim(m: dict) -> dict:
    """What Nimble sees of a candidate: id + situation only (token budget)."""
    return {"id": m["id"], "situation": m["situation"]}


def load(path) -> list:
    p = Path(path)
    if not p.is_file():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def save(store: list, path) -> None:
    Path(path).write_text("".join(json.dumps(m, ensure_ascii=False) + "\n" for m in store))


def new_id(store: list) -> str:
    nums = [int(m["id"][1:]) for m in store if str(m.get("id", "")).startswith("M")
            and str(m["id"])[1:].isdigit()]
    return f"M{(max(nums) + 1) if nums else 0:03d}"


def validate(m: dict) -> bool:
    return all(k in m and m[k] not in (None, "") for k in REQUIRED) and isinstance(m.get("when"), dict)
