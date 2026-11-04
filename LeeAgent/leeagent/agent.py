"""LeeAgent: plays one seat of TavernGym — memory retrieval once per turn,
scored actions in between, engine lookahead before EndTurn. The other seven
seats are the built-in scripted bots (the Phase-0 ladder).
"""

from __future__ import annotations

import json

import taverngym

from . import comp as comp_mod
from . import lookahead, memory, nimble, policy, scoutsynth
from .config import NIMBLE_BASE, thresholds
from .facts import extract_facts
from .retrieval import Retrieval, retrieve

SYNTH_SCOUT = False       # roadmap 5: danger vs turn-T board distribution
                          # instead of one opponent snapshot (gate switch)
VALUE_GATE = False        # roadmap 7: value model vetoes on-curve upgrades
                          # when E[reward | best buy] beats E[reward | upgrade]
UNIVERSAL_POS = True      # roadmap 4: rule-based arrangement, no opponent info
                          # (windfury left / taunt by carry / summoners right;
                          # fires only when a rule binds — bare reshuffles ablated.
                          # Gate: dev -0.19 / holdout -0.34 / fresh 1700 -0.24,
                          # merged 300 games p~0.045, adopted 2026-11-04)
COMP_ROLLOUT = False      # roadmap-7 search half: at the once-per-game comp
                          # commit, arbitrate the top comp.rank() candidates by
                          # paired reseeded rollouts (seat replayed by this same
                          # policy with its direction pinned, opponents by the
                          # engine bots — the exact future the live game faces)
                          # instead of the heuristic argmax. Gate (2026-11-04,
                          # runs/comp_rollout_gate.json): NO-ADOPT — contact
                          # passed (54% of searched games flipped, first live
                          # mechanism past the injection-surface wall) but the
                          # overturned decisions carry no placement value:
                          # dev +0.01/holdout +0.02 (p 0.46/0.85), median flip
                          # margin 0.15 < the 48-rep SE 0.19, and flipped games
                          # realize +0.02/+0.05. The comp direction is near-
                          # equivalent across top-3 at this play level; search
                          # value is bounded by the continuation policy's
                          # ability to realize direction differences.
COMP_ROLLOUT_REPS = 48    # reseeds per candidate, shared across candidates
COMP_ROLLOUT_TOPK = 3     # candidates from comp.rank(min_board=COMP_ROLLOUT_MINBOARD)
COMP_ROLLOUT_MINBOARD = 1 # contact survey (dev 300-339, pre-outcome): min_board=2
                          # starves the candidate set (23/34 games single-candidate,
                          # 0 with three); =1 gives 2-3 candidates in 32/34 and the
                          # heuristic pick is always rank[0] — pivot directions with
                          # one board minion are real options for the search
LATE_SEARCH = True        # E1 phase-mixed agent (scripts/late_search_gate.py),
                          # ADOPTED 2026-11-04: bot-continuation rollout
                          # arbitration where E0 proved search beats the
                          # heuristic scorer — late recruit turns (N2 analog)
                          # and pending discover/choose decisions at any turn
                          # (D4 analog) — while early turns stay purely
                          # heuristic (N1: heuristic 0.690 vs best search
                          # 0.517). The heuristic remains the nominator
                          # (top-K); search only arbitrates. Gate: dev
                          # -0.36 / holdout -0.47 / fresh 1900 -0.19, merged
                          # 300 games -0.340 place, top4 68.7% -> 75.3%
                          # (+6.7pp), sign 134/94 p=0.0096. ~35s/game.
LATE_SEARCH_TURN = 8      # data-defined phase cut, not tuned: N1 spans turns
                          # 4-7, N2 turns 8-12 (labels meta) — 8 is the smallest
                          # N2 turn and above the largest N1 turn
LATE_SEARCH_REPS = 48     # reseeds per candidate (cost knob, not tuned on
                          # outcomes); salts shared across candidates
LATE_SEARCH_TOPK = 4      # nominees per recruit decision from score_actions
LATE_SEARCH_PENDING_MAX = 4   # pending scope: D4-shaped card picks only (the
                              # bench discovers are 3-option). A smoke census
                              # (seed 1800, pre-outcome) showed the raw pending
                              # surface is 249 fires/game over just 10 distinct
                              # option-sets, dominated by a 12-option repeatable
                              # prompt firing 89x — out of E0's evidence scope.
                              # Bigger prompts keep the heuristic pick.
LATE_SEARCH_MEMO = True   # same (turn, options) pending -> same decision:
                              # repeatable prompts must not re-search per fire

_LGBM = None


def _value_model():
    global _LGBM
    if _LGBM is None:
        import lightgbm as lgb
        from pathlib import Path
        p = Path(__file__).resolve().parents[1] / "data" / "value_model.txt"
        _LGBM = lgb.Booster(model_file=str(p)) if p.is_file() else False
    return _LGBM or None


def _play_out(g, seat: int, agent=None) -> int | None:
    """One reseeded continuation: the seat plays the given agent (pure bot
    when None), everyone else the engine bot — mirroring the bridge's
    rollout_unit, including its rare illegal-bot-action drop (rep
    discarded)."""
    guard = 0
    try:
        while not g.is_over() and guard < 100000:
            for p in range(g.num_players):
                if g.needs_action(p):
                    if p == seat and agent is not None:
                        g.step(p, agent.choose(g, p))
                    else:
                        g.step(p, g.bot_action(p))
            guard += 1
    except ValueError:
        return None
    return int(list(g.placements())[seat]) if g.is_over() else None


def _comp_search(game, seat: int, view: dict, facts: dict, store, th):
    """COMP_ROLLOUT arbitration: snapshot the live game at the commit turn,
    replay it COMP_ROLLOUT_REPS times per candidate tribe — the same reseeds
    for every candidate (paired) — and return the best mean-placement tribe
    (ties keep the heuristic order). None keeps the heuristic choice. The
    continuation seat is this same policy with its direction pinned, so the
    measurement target is E[placement | we keep playing like we play]."""
    import sys as _sys
    from pathlib import Path as _P
    tb = _P(__file__).resolve().parents[2] / "tavernbench"
    if str(tb) not in _sys.path:
        _sys.path.insert(0, str(tb))
    from tavernbench import engine as E

    cands = comp_mod.rank(view, facts, min_board=COMP_ROLLOUT_MINBOARD,
                          k=COMP_ROLLOUT_TOPK)
    info = {"turn": facts["turn"], "candidates": cands}
    if len(cands) < 2:
        return None, info
    st = game.state_json()
    means = {}
    for c in cands:
        pls = []
        for j in range(COMP_ROLLOUT_REPS):
            g2 = E.reseeded(E.from_state(st), j)
            a2 = LeeAgent(store, th=th, use_nimble=False)
            a2._comp = c
            a2._turn_seen = -1
            pl = _play_out(g2, seat, a2)
            if pl is not None:
                pls.append(pl)
        if pls:
            means[c] = sum(pls) / len(pls)
    info["means"] = {c: round(m, 3) for c, m in means.items()}
    if not means:
        return None, info
    best = min(means, key=lambda c: (means[c], cands.index(c)))
    return best, info


def _tb_engine():
    """The tavernbench engine helpers (from_state/reseeded) — same Rust core
    the live game runs on; path set up lazily so the default import graph
    is unchanged."""
    import sys as _sys
    from pathlib import Path as _P
    tb = _P(__file__).resolve().parents[2] / "tavernbench"
    if str(tb) not in _sys.path:
        _sys.path.insert(0, str(tb))
    from tavernbench import engine as E
    return E


def _late_search(game, seat: int, cands: list, kind: str):
    """E1 arbitration: bot-continuation rollouts over heuristic-nominated
    candidate actions. The evaluator is deliberately the all-bot playout —
    the only one that discriminated the N2/D4-style decisions (E0: bot arm
    0.48/0.62 vs heuristic-forced 0.26/0.31); the heuristic stays the
    nominator. Same reseeds for every candidate (paired). Returns the best
    action (ties keep nomination order) or None to keep the heuristic pick."""
    E = _tb_engine()
    st = game.state_json()
    means = {}
    for a in cands:
        pls = []
        for j in range(LATE_SEARCH_REPS):
            g2 = E.reseeded(E.from_state(st), j)
            if a not in E.legal(g2, seat):
                continue
            g2.step(seat, a)
            pl = _play_out(g2, seat)
            if pl is not None:
                pls.append(pl)
        if pls:
            means[a] = sum(pls) / len(pls)
    info = {"kind": kind, "cands": list(cands),
            "means": {a: round(m, 3) for a, m in means.items()}}
    if not means:
        return None, info
    best = min(means, key=lambda a: (means[a], cands.index(a)))
    return best, info


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
        self._late_searched = False
        self._turn_actions: list[str] = []
        self._danger: float | None = None
        self._buy_hint: int | None = None
        self._no_upgrade = False
        self._comp: str | None = None
        self._late_memo: dict = {}

    # -- one decision ------------------------------------------------------
    def choose(self, game, seat: int) -> int:
        view = json.loads(game.view(seat))
        facts = extract_facts(view)
        legal = policy.legal_actions(game, seat)

        if facts["pending"]:
            act = policy.choose_pending(legal, view)
            if LATE_SEARCH and 1 < len(legal) <= LATE_SEARCH_PENDING_MAX:
                memo_key = (view["turn"], tuple(sorted(legal))) \
                    if LATE_SEARCH_MEMO else None
                if memo_key is not None and memo_key in self._late_memo:
                    act = self._late_memo[memo_key]
                    self.stats["late_memo_hits"] = \
                        self.stats.get("late_memo_hits", 0) + 1
                else:
                    pick, info = _late_search(game, seat, list(legal), "pending")
                    info["heuristic"] = act
                    self.stats.setdefault("late_searches", []).append(info)
                    if pick is not None:
                        act = pick
                    if memo_key is not None:
                        self._late_memo[memo_key] = act
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
                                      comp=self._comp,
                                      no_upgrade=self._no_upgrade)
        best = scored[0]
        if (LATE_SEARCH and not self._late_searched
                and view["turn"] >= LATE_SEARCH_TURN and len(scored) > 1):
            self._late_searched = True
            cands = [a for _s, a, _l, _w in scored[:LATE_SEARCH_TOPK]]
            pick, info = _late_search(game, seat, cands, "recruit")
            info["heuristic"] = best[1]
            self.stats.setdefault("late_searches", []).append(info)
            if pick is not None and pick != best[1]:
                best = next(r for r in scored if r[1] == pick)
        if best[2] == "end" and not self._positioned and facts["board_count"] >= 2:
            did = []
            if UNIVERSAL_POS:            # roadmap 4: rule-based, zero panel info
                uo = lookahead.universal_order(view)
                if uo is not None and lookahead.apply_order(game, seat, uo, view):
                    did.append("universal")
            if ((self.th["fix_positioning"] or self._fresh)
                    and facts["next_opponent"] is not None):
                fresh = json.loads(game.view(seat))   # view is stale after moves
                name = lookahead.fix_positioning(game, seat, fresh,
                                                 self.th["positioning_sims"])
                did.append(name)
            if did:
                self._positioned = True
                self.stats["positionings"] += 1
                self._turn_actions.append("position:" + "+".join(did))
                return self.choose(game, seat)  # rescore after the moves

        self._turn_actions.append(best[2])
        return best[1]

    def _on_turn(self, game, seat: int, view: dict, facts: dict) -> None:
        if self.turn_log:  # what the previous turn actually did
            self.turn_log[-1]["actions"] = self._turn_actions
        self._turn_seen = view["turn"]
        self._positioned = False
        self._late_searched = False
        self._turn_actions = []
        self._danger = self._scout(game, seat, facts)
        self._fresh = self._scout_fresh(view, facts)
        self._buy_hint = self._search_buy(game, seat, view, facts)
        self._no_upgrade = self._value_gate(game, seat, view, facts) \
            if VALUE_GATE else False
        if self._comp is None and facts["turn"] >= comp_mod.COMMIT_TURN:
            self._comp = comp_mod.decide(view, facts)
            if self._comp is not None and COMP_ROLLOUT:
                pick, info = _comp_search(game, seat, view, facts,
                                          self.store, self.th)
                info["heuristic"] = self._comp
                self.stats.setdefault("comp_searches", []).append(info)
                if pick:
                    self._comp = pick
        if self.use_nimble and facts["turn"] >= 3:  # early turns: nothing to judge yet
            self._retrieval = retrieve(self.store, view, facts, self.th, base=self.base)
            self.stats["nimble_ms"] += self._retrieval.nimble_ms
            self.stats["nimble_tokens"] += self._retrieval.tokens
            self.stats["splits"] += self._retrieval.splits
        else:
            cands = memory.prefilter(self.store, facts, self.th["max_candidates"])
            self._retrieval = Retrieval(candidates=[m["id"] for m in cands],
                                        matched=[(m, 1.0) for m in cands[:3]])
        # structural memory verbs (roadmap 6): matched memories may carry
        # commit_tribe (earlier direction commitment) or hold_upgrade
        # (this turn's upgrade veto) — score-tweak verbs stay in policy
        for m, _p in self._retrieval.matched:
            b = m.get("bias") or {}
            if self._comp is None and "commit_tribe" in b:
                self._comp = b["commit_tribe"]
            if b.get("hold_upgrade"):
                self._no_upgrade = True
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
        if SYNTH_SCOUT:
            d = scoutsynth.danger(game, seat, facts["turn"])
            if d is not None:
                return d
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
    def _value_gate(self, game, seat: int, view: dict, facts: dict) -> bool:
        """Roadmap 7: veto this turn's on-curve upgrade when the value model
        says the best affordable buy leaves a better expected reward. Pure
        feature prediction on game copies — no combat preview, no stale-panel
        channel (the falsified lookahead traps live there)."""
        model = _value_model()
        if model is None:
            return False
        up_price = facts["upgrade_price"] or 99
        if up_price > facts["gold"] or facts["tier"] >= 6:
            return False
        from scripts.gen_trajectories import feat_row

        def v_after(steps) -> float | None:
            g2 = game.copy()
            try:
                for a in steps:
                    if a not in policy.legal_actions(g2, seat):
                        return None
                    g2.step(seat, a)
                    if g2.is_over():
                        return None
                v2 = json.loads(g2.view(seat))
                f2 = extract_facts(v2)
                if f2["pending"]:
                    return None
                return float(model.predict([feat_row(v2, f2, self._comp)])[0])
            except Exception:
                return None

        v_up = v_after([policy.A_UPGRADE])
        if v_up is None:
            return False
        shop = view["me"].get("shop") or []
        best_buy = max((policy.card_quality(c) for c in shop
                        if c.get("type") != "spell" and 3 <= facts["gold"]), default=-1)
        bi = next((policy.A_BUY + i for i, c in enumerate(shop)
                   if c.get("type") != "spell" and 3 <= facts["gold"]
                   and policy.card_quality(c) == best_buy), None)
        if bi is None:
            return False
        v_buy = v_after([bi])
        if v_buy is None:
            return False
        return v_buy > v_up          # margin-free comparison; gate arbitrates

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
