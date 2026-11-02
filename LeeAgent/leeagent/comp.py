"""Comp commitment: pick a tribe direction once per game, then play into it.

The direction decision is code-scored (catalog engine density + board
affinity + hero affinity); the policy consumes the committed tribe through
score_actions' `comp` parameter. Scaling-engine text value only counts
INSIDE the committed direction — the global version was ablated harmful.
"""

from __future__ import annotations

import json
from functools import lru_cache

TRIBES = ("BEAST", "DRAGON", "MECH", "MURLOC", "UNDEAD",
          "DEMON", "ELEMENTAL", "PIRATE", "QUILBOAR")

# direction-decision constants (coordinate-ascent tuned; scripts/comp_sweep.py)
COMMIT_TURN = 5            # earliest turn a direction may be committed
COMMIT_MIN_BOARD = 3       # board minions of the tribe needed to commit
W_AFFINITY = 3.0           # weight of board affinity
W_DENSITY = 3.0            # weight of catalog engine density (normalised)
W_HERO = 1.5               # hero-text affinity nudge

_ENGINE_KW = ("whenever", "after you", "each turn", "gains +", "has +", "start of your turn")


def _norm(race: str) -> str:
    r = (race or "").upper()
    return {"MECHANICAL": "MECH"}.get(r, r)


@lru_cache(maxsize=1)
def engine_density() -> dict:
    """Pool minions of tier 3+ with scaling-engine text, per tribe."""
    import taverngym
    dens = {t: 0 for t in TRIBES}
    for c in json.loads(taverngym.catalog_json()):
        if (c.get("kind") != "minion" or not c.get("in_pool") or not c.get("implemented")
                or c["id"].endswith("_G")):
            continue
        if not 3 <= c.get("tier", 0) <= 6:
            continue
        t = (c.get("text") or "").lower()
        if not any(k in t for k in _ENGINE_KW):
            continue
        for r in c.get("races") or []:
            tr = _norm(r)
            if tr in dens:
                dens[tr] += 1
    return dens


def decide(view: dict, facts: dict) -> str | None:
    """The committed tribe, or None while the board shows no direction.

    Board affinity dominates (commit to what we already have), the catalog's
    engine density breaks ties between equal boards, hero text is a nudge.
    """
    tribes = facts.get("tribes") or {}
    dens = engine_density()
    dmax = max(dens.values()) or 1
    hero_text = ((view["me"].get("hero") or {}).get("text") or "").lower()

    best, best_s = None, 0.0
    for t in TRIBES:
        s = W_AFFINITY * tribes.get(t, 0) + W_DENSITY * dens[t] / dmax
        if t.lower() in hero_text:
            s += W_HERO
        if t == facts.get("comp"):        # sticking costs nothing
            s += 1.0
        if s > best_s:
            best, best_s = t, s
    # a direction needs at least a 2-minion board affinity to mean anything
    if best and tribes.get(best, 0) >= COMMIT_MIN_BOARD:
        return best
    return None


def engine_text_bonus(card: dict) -> float:
    """Scaling-engine text value, valid only inside the committed tribe."""
    t = (card.get("text") or "").lower()
    n = sum(1 for k in _ENGINE_KW if k in t)
    return min(n, 3) * 4.0
