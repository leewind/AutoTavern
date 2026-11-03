"""Comp commitment: pick a tribe direction once per game, then play into it.

The direction decision is code-scored (catalog engine density + board
affinity + hero affinity); the policy consumes the committed tribe through
score_actions' `comp` parameter. Scaling-engine text value only counts
INSIDE the committed direction — the global version was ablated harmful.

Recipe layer (USE_RECIPES): HSReplay archetype comps mapped onto this
pool's cards, then causally measured by forced assembly
(scripts/recipe_gate.py). When on, direction density comes from measured
recipe strength instead of keyword counts, and buying a missing core of
the tribe's best recipe earns a checklist bonus.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

TRIBES = ("BEAST", "DRAGON", "MECH", "MURLOC", "UNDEAD",
          "DEMON", "ELEMENTAL", "PIRATE", "QUILBOAR")

USE_RECIPES = False      # recipe gate switch; runs/recipe_gate.json arbitrates


@lru_cache(maxsize=1)
def recipe_table() -> dict:
    p = Path(__file__).resolve().parents[1] / "data" / "recipes.json"
    return json.loads(p.read_text()) if p.is_file() else {}

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


def _recipe_strength() -> dict:
    """tribe -> strength of its best measured recipe, normalised to 0..1."""
    best: dict[str, float] = {}
    for r in recipe_table().get("recipes", []):
        s = -r.get("gain", 0)
        if s > best.get(r["tribe"], 0.0):
            best[r["tribe"]] = s
    m = max(best.values(), default=0) or 1
    return {t: v / m for t, v in best.items()}


def recipe_core_bonus(card_id: str | None, owned_ids: set,
                      comp: str | None) -> float:
    """Buying a missing core of the committed tribe's best recipe earns a
    checklist bonus (4..10 pts, scaled by measured recipe strength)."""
    if not USE_RECIPES or not card_id or not comp:
        return 0.0
    recipes = [r for r in recipe_table().get("recipes", [])
               if r["tribe"] == comp]
    if not recipes:
        return 0.0
    best = max(recipes, key=lambda r: -r.get("gain", 0))
    strength = -best.get("gain", 0)
    m = max((-r.get("gain", 0) for r in recipe_table().get("recipes", [])),
            default=1) or 1
    cid = card_id[:-2] if card_id.endswith("_G") else card_id
    if cid not in best.get("cores", []) or cid in owned_ids:
        return 0.0
    return 4.0 + 6.0 * strength / m


def decide(view: dict, facts: dict) -> str | None:
    """The committed tribe, or None while the board shows no direction.

    Board affinity dominates (commit to what we already have), the catalog's
    engine density breaks ties between equal boards, hero text is a nudge.
    With USE_RECIPES the tie-break density is the measured recipe strength.
    """
    tribes = facts.get("tribes") or {}
    if USE_RECIPES and recipe_table():
        dens = _recipe_strength()
        dmax = 1
    else:
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
