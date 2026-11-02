"""LeeAgent: plays one seat of TavernGym — memory retrieval once per turn,
scored actions in between, engine lookahead before EndTurn. The other seven
seats are the built-in scripted bots (the Phase-0 ladder).
"""

from __future__ import annotations

import json

import taverngym

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

    # -- one decision ------------------------------------------------------
    def choose(self, game, seat: int) -> int:
        view = json.loads(game.view(seat))
        facts = extract_facts(view)
        legal = policy.legal_actions(game, seat)

        if facts["pending"]:
            act = policy.choose_pending(legal)
            self._turn_actions.append(f"pending:{taverngym.action_name(act)}")
            return act

        if view["turn"] != self._turn_seen:
            self._on_turn(game, seat, view, facts)

        scored = policy.score_actions(view, self._retrieval.matched, legal)
        best = scored[0]
        if (best[2] == "end" and self.th["fix_positioning"] and not self._positioned
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
