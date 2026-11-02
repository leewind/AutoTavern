"""LeeAgent: plays one seat of TavernGym — memory retrieval once per turn,
scored actions in between, engine lookahead before EndTurn. The other seven
seats are the built-in scripted bots (the Phase-0 ladder).
"""

from __future__ import annotations

import json

import taverngym

from . import comp as comp_mod
from . import lookahead, memory, nimble, policy
from .config import NIMBLE_BASE, thresholds
from .facts import extract_facts
from .retrieval import Retrieval, retrieve


class LeeAgent:
    def __init__(self, store: list, th: dict | None = None, use_nimble: bool = True,
                 base: str = NIMBLE_BASE):
        self.store = store
        self.th = th or thresholds()
        self.use_nimble = use_nimble and bool(nimble.health(base))
        self.base = base
        self.reset()

    def reset(self) -> None:
        self.turn_log: list[dict] = []
        self.stats = {"turns": 0, "actions": 0, "nimble_ms": 0.0, "nimble_tokens": 0,
                      "splits": 0, "positionings": 0}
        self._turn_seen = -1
        self._retrieval = Retrieval()
        self._positioned = False
        self._turn_actions: list[str] = []
        self._danger: float | None = None
        self._buy_hint: int | None = None
        self._comp: str | None = None

    # -- one decision ------------------------------------------------------
    def choose(self, game, seat: int) -> int:
        view = json.loads(game.view(seat))
        facts = extract_facts(view)
        legal = policy.legal_actions(game, seat)

        if facts["pending"]:
            act = policy.choose_pending(legal, view)
            self._turn_actions.append(f"pending:{taverngym.action_name(act)}")
            return act

        if view["turn"] != self._turn_seen:
            self._on_turn(game, seat, view, facts)

        # hard stop against pathological action loops (0-cost repeatables):
        # the scripted bot caps at 60 actions per turn; so do we
        if len(self._turn_actions) >= 60:
            for i in legal:
                if policy.decode(i)[0] == "end":
                    self._turn_actions.append("end:cap60")
                    return i
            self._turn_actions.append("cap60:fallback")
            return sorted(legal)[0]

        scored = policy.score_actions(view, self._retrieval.matched, legal,
                                      n_turn_actions=len(self._turn_actions),
                                      scout=self._danger, buy_hint=self._buy_hint,
                                      comp=self._comp)
        best = scored[0]
        if (best[2] == "end" and not self._positioned
                and (self.th["fix_positioning"] or self._fresh)
                and facts["board_count"] >= 2 and facts["next_opponent"] is not None):
            self._positioned = True
            name = lookahead.fix_positioning(game, seat, view, self.th["positioning_sims"])
            self.stats["positionings"] += 1
            self._turn_actions.append(f"position:{name}")
            return self.choose(game, seat)  # rescore after the moves

        self._turn_actions.append(best[2])
        return best[1]

    def _on_turn(self, game, seat: int, view: dict, facts: dict) -> None:
        if self.turn_log:  # what the previous turn actually did
            self.turn_log[-1]["actions"] = self._turn_actions
        self._turn_seen = view["turn"]
        self._positioned = False
        self._turn_actions = []
        self._danger = self._scout(game, seat, facts)
        self._fresh = self._scout_fresh(view, facts)
        self._buy_hint = self._search_buy(game, seat, view, facts)
        if self._comp is None and facts["turn"] >= comp_mod.COMMIT_TURN:
            self._comp = comp_mod.decide(view, facts)
        if self.use_nimble and facts["turn"] >= 3:  # early turns: nothing to judge yet
            self._retrieval = retrieve(self.store, view, facts, self.th, base=self.base)
            self.stats["nimble_ms"] += self._retrieval.nimble_ms
            self.stats["nimble_tokens"] += self._retrieval.tokens
            self.stats["splits"] += self._retrieval.splits
        else:
            cands = memory.prefilter(self.store, facts, self.th["max_candidates"])
            self._retrieval = Retrieval(candidates=[m["id"] for m in cands],
                                        matched=[(m, 1.0) for m in cands[:3]])
        self.stats["turns"] += 1
        self.turn_log.append({
            "turn": facts["turn"], "gold": facts["gold"], "health": facts["health"],
            "tier": facts["tier"], "candidates": self._retrieval.candidates,
            "matched": [(m["id"], round(p, 2)) for m, p in self._retrieval.matched],
            "top": self._retrieval.top,
        })

    def _scout(self, game, seat: int, facts: dict) -> float | None:
        """One combat preview vs the next opponent's scouted board: our win
        rate + half ties, as a coarse ahead/behind signal for this turn.
        None when there is nothing to scout."""
        opp = facts.get("next_opponent")
        if opp is None or facts["board_count"] < 1:
            return None
        try:
            out = game.debug(json.dumps({"cmd": "combat_preview", "a": seat, "b": opp,
                                         "n": 32, "details": True}))
            d = json.loads(out)
            return float(d.get("win_a", 0.0)) + 0.5 * float(d.get("tie", 0.0))
        except Exception:
            return None

    def _search_buy(self, game, seat: int, view: dict, facts: dict) -> int | None:
        """Lookahead over the two best affordable buys: on game copies, apply
        buy + play, then preview the combat. The stale scouted opponent is the
        same constant for both candidates, so the comparison is fair.

        Returns the winning buy action index, or None (keep the static choice).
        Ablated harmful (dev 57 / holdout 45, same stale-info trap as
        positioning): disabled by default.
        """
        if not self.th.get("buy_lookahead"):
            return None
        if facts["turn"] < 4 or facts["gold"] < 3 or facts["next_opponent"] is None:
            return None
        legal = policy.legal_actions(game, seat)
        cands = []
        for i in legal:
            d = policy.decode(i)
            if d[0] != "buy":
                continue
            card = (view["me"].get("shop") or [])[d[1]] if d[1] < len(view["me"].get("shop") or []) else {}
            if card.get("type") == "spell":
                continue
            cands.append((policy.card_quality(card), i))
        cands.sort(reverse=True)
        if len(cands) < 2 or cands[0][0] - cands[1][0] > 4:
            return None                      # clear winner already, or no choice
        best_s, best_i = -1.0, None
        for _q, i in cands[:2]:
            g2 = game.copy()
            try:
                g2.step(seat, i)
                v2 = json.loads(g2.view(seat))
                h = len(v2["me"].get("hand") or []) - 1
                if h >= 0 and not v2["me"].get("pending"):
                    pos = min(len(v2["me"].get("board") or []), policy.N_BOARD - 1)
                    g2.step(seat, policy.A_PLAY + h * policy.N_POS + pos)
                out = g2.debug(json.dumps({"cmd": "combat_preview", "a": seat,
                                           "b": facts["next_opponent"], "n": 24,
                                           "details": True}))
                d = json.loads(out)
                s = float(d.get("win_a", 0.0)) + 0.5 * float(d.get("tie", 0.0))
                if s > best_s:
                    best_s, best_i = s, i
            except Exception:
                continue
        return best_i
    def _scout_fresh(self, view: dict, facts: dict) -> bool:
        """Is the next opponent's scouted board fresh enough to act on
        (seen within the last two turns)?"""
        nxt = facts.get("next_opponent")
        if nxt is None:
            return False
        entry = next((o for o in view.get("opponents") or [] if o.get("id") == nxt), None)
        if not entry or not entry.get("seen_board"):
            return False
        return (entry.get("seen_turn") or -9) >= view["turn"] - 2

    # -- a full game -------------------------------------------------------
    def run_game(self, seed: int, seat: int = 0) -> dict:
        self.reset()
        game = taverngym.Game(seed=seed)
        while not game.is_over():
            for s in range(game.num_players):
                if game.needs_action(s):
                    act = self.choose(game, s) if s == seat else game.bot_action(s)
                    game.step(s, act)
                    if s == seat:
                        self.stats["actions"] += 1
        if self.turn_log:
            self.turn_log[-1]["actions"] = self._turn_actions
        placement = list(game.placements())[seat]  # 1..8, 1 = champion
        reward = 1.0 - 2.0 * (placement - 1) / 7.0
        return {"seed": seed, "seat": seat, "placement": int(placement),
                "reward": round(reward, 4), "stats": dict(self.stats),
                "turns": self.turn_log}
