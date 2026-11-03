"""Pure-logic tests for the synthetic-scout board pools."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from leeagent import scoutsynth                   # noqa: E402


def test_pools_shape():
    pools = scoutsynth._pools()
    assert pools, "data/scout_boards.json missing"
    for t in ("5", "9", "14"):
        entry = pools[t]
        assert entry["boards"] and len(entry["boards"]) <= 300
        assert 1 <= entry["avg_tier"] <= 7
        board = entry["boards"][0]
        assert all(m["id"] for m in board)


def test_danger_none_without_pool():
    # no pool for turn 1 (below the collected range)
    class FakeGame:
        def copy(self):
            raise AssertionError("must not copy when no pool")

    assert scoutsynth.danger(FakeGame(), 0, 1) is None
