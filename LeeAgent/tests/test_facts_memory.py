"""Pure-logic tests plus one optional live Nimble retrieval test.

    ../.venv/bin/python -m pytest LeeAgent/tests -q     (from the repo root)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from leeagent import memory                      # noqa: E402
from leeagent.config import ROOT as CFG_ROOT     # noqa: E402
from leeagent.facts import extract_facts, render_state  # noqa: E402

SEED = CFG_ROOT / "memories" / "seed.jsonl"


def _facts(**over):
    f = {"turn": 9, "health": 23, "armor": 0, "tier": 4, "gold": 10, "gold_cap": 10,
         "hand_count": 2, "hand_limit": 10, "hand_full": False, "board_count": 7,
         "board_full": True, "shop_count": 6, "upgrade_price": 5, "tribes": {"BEAST": 3},
         "keywords": ["TAUNT"], "shop_tribes": {"BEAST": 2}, "num_alive": 6,
         "next_is_ghost": False, "next_opponent": 1, "win_streak": 0, "pending": False}
    f.update(over)
    return f


def test_when_matching_ranges_and_flags():
    assert memory.matches({"turn_min": 6, "turn_max": 12}, _facts())
    assert not memory.matches({"turn_min": 10}, _facts())
    assert memory.matches({"hp_above": 20, "hp_below": 30}, _facts())
    assert not memory.matches({"hand_full": True}, _facts())
    assert memory.matches({"hand_full": False}, _facts())
    assert memory.matches({"tribe_min": {"BEAST": 2}, "shop_tribe_min": {"BEAST": 1}}, _facts())
    assert not memory.matches({"tribe_min": {"BEAST": 5}}, _facts())
    assert memory.matches({"any_keyword": ["TAUNT", "CLEAVE"]}, _facts())
    assert not memory.matches({"any_keyword": ["WINDFURY"]}, _facts())
    assert memory.matches({}, _facts())


def test_prefilter_specificity_order_and_cap():
    store = [
        {"id": "A", "when": {}, "situation": "s"},
        {"id": "B", "when": {"turn_min": 5}, "situation": "s"},
        {"id": "C", "when": {"tribe_min": {"BEAST": 2}, "hp_above": 10}, "situation": "s"},
        {"id": "D", "when": {"turn_min": 99}, "situation": "s"},
    ]
    hit = memory.prefilter(store, _facts(), limit=2)
    assert [m["id"] for m in hit] == ["C", "B"]  # specificity desc, non-matching D out


def test_seed_store_loads_and_validates():
    store = memory.load(SEED)
    assert len(store) == 24
    assert all(memory.validate(m) for m in store)
    ids = [m["id"] for m in store]
    assert len(set(ids)) == 24


def test_facts_from_a_real_game():
    import taverngym
    g = taverngym.Game(seed=1)
    for seat in range(g.num_players):
        if g.needs_action(seat):
            g.step(seat, g.bot_action(seat))
    while g.turn < 5 and not g.is_over():
        for seat in range(g.num_players):
            if g.needs_action(seat):
                g.step(seat, g.bot_action(seat))
    for seat in range(g.num_players):
        view = json.loads(g.view(seat))
        f = extract_facts(view)
        assert 1 <= f["num_alive"] <= 8 and f["turn"] >= 0
        assert f["hand_full"] == (f["hand_count"] >= f["hand_limit"])
        assert isinstance(f["tribes"], dict)
        assert "Turn" in render_state(view)


def test_new_id():
    assert memory.new_id([]) == "M000"
    assert memory.new_id([{"id": "M001"}]) == "M002"
    assert memory.new_id([{"id": "M999"}, {"id": "M001"}]) == "M1000"


@pytest.mark.skipif(not (CFG_ROOT.parent / ".venv" / "bin").exists(),
                    reason="repo venv missing")
def test_live_retrieval_stays_in_budget():
    """Live Nimble test: skipped silently when the service is down."""
    from leeagent import nimble
    if not nimble.health():
        pytest.skip("nimble service down")
    import taverngym
    from leeagent.retrieval import retrieve
    from leeagent.config import thresholds
    g = taverngym.Game(seed=1)
    for seat in range(g.num_players):
        if g.needs_action(seat):
            g.step(seat, g.bot_action(seat))
    while g.turn < 8 and not g.is_over():
        for seat in range(g.num_players):
            if g.needs_action(seat):
                g.step(seat, g.bot_action(seat))
    view = json.loads(g.view(0))
    r = retrieve(memory.load(SEED), view, extract_facts(view), thresholds())
    assert r.candidates, "prefilter found nothing"
    assert r.tokens > 0
    assert all(0.0 <= p <= 1.0 for _m, p in r.matched + r.uncertain)
