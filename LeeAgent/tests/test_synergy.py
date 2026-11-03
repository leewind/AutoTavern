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
