"""Pure-logic tests for the synergy-table consumption in policy."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from leeagent import policy as P                    # noqa: E402


def test_synergy_bonus(monkeypatch):
    fake = {"BEAST": {"S1": {
        "C1": {"lift": 0.2, "n1": 30, "sig": True},
        "C2": {"lift": 0.9, "n1": 30, "sig": False},   # big but not significant
    }}}
    monkeypatch.setattr(P, "_SYNERGY_TABLE", fake)
    monkeypatch.setattr(P, "SYNERGY_W", 8.0)           # default is 0 (gate-rejected)
    assert P.synergy_bonus("S1", ["C1"], "BEAST") == 8.0 * 0.2
    assert P.synergy_bonus("S1", ["C2"], "BEAST") == 0.0
    assert P.synergy_bonus("S1", ["C1", "C2"], "BEAST") == P.SYNERGY_W * 0.2
    assert P.synergy_bonus("S1", ["C1"], "DRAGON") == 0.0
    assert P.synergy_bonus("S1", ["C1"], None) == 0.0
    assert P.synergy_bonus(None, ["C1"], "BEAST") == 0.0
    assert P.synergy_bonus("S9", ["C1"], "BEAST") == 0.0


def test_synergy_off_arm(monkeypatch):
    """The gate's OFF arm patches _synergy_table to {} — consumption must
    degrade to exactly zero bonus."""
    monkeypatch.setattr(P, "_synergy_table", lambda: {})
    assert P.synergy_bonus("S1", ["C1"], "BEAST") == 0.0


def test_fixed_pair_bonus(monkeypatch):
    fake = [{"core": "C1", "support": "S1", "tribe": "BEAST", "gain": -1.0,
             "n": 35}]
    monkeypatch.setattr(P, "_FIXED_PAIRS", fake)
    monkeypatch.setattr(P, "FIXED_PAIR_W", 24.0)       # default is 0 (gate-rejected)
    # measured direction only: core owned -> support in shop
    assert P.fixed_pair_bonus("S1", {"C1"}) == 24.0 * 0.5     # gain capped at 0.5
    assert P.fixed_pair_bonus("C1", {"S1"}) == 0.0            # reverse not measured
    assert P.fixed_pair_bonus("S1", set()) == 0.0
    assert P.fixed_pair_bonus(None, {"C1"}) == 0.0


def test_pair_partner_unfrozen(monkeypatch):
    fake = [{"core": "C1", "support": "S1", "tribe": "BEAST", "gain": -1.0,
             "n": 35}]
    monkeypatch.setattr(P, "_FIXED_PAIRS", fake)
    shop = [{"id": "X"}, {"id": "S1"}, {"id": "S1_G"}, {"id": "S1", "frozen": True}]
    assert P.pair_partner_unfrozen(shop, {"C1"}) is True       # S1 base or golden
    assert P.pair_partner_unfrozen(shop, {"C2"}) is False      # core not owned
    frozen_only = [{"id": "S1", "frozen": True}]
    assert P.pair_partner_unfrozen(frozen_only, {"C1"}) is False  # no toggle loop


def test_recipe_core_bonus_default_off():
    """USE_RECIPES defaults off (adopt gate: feature inert) — the bonus
    must be exactly zero until the switch is flipped."""
    import leeagent.comp as C
    assert C.USE_RECIPES is False
    table = C.recipe_table()
    assert table.get("recipes")
    r0 = table["recipes"][0]
    assert C.recipe_core_bonus(r0["cores"][0], set(), r0["tribe"]) == 0.0
