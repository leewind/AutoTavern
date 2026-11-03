"""Engine lookahead: choose the warband arrangement by simulated combats.

Uses the engine's own combat_preview debug command (fights on copies, the live
game is untouched by the simulation itself). Arrangements are applied for real
with Move actions; after trying the candidates the best one is restored, so the
net effect is one deterministic re-arrange per turn.
"""

from __future__ import annotations

import json

from .policy import A_MOVE, N_BOARD, legal_actions


def _move_idx(frm: int, to: int) -> int:
    return A_MOVE + frm * N_BOARD + to


def _move_legal(game, seat, frm, to) -> bool:
    mask = game.legal_mask(seat)
    i = _move_idx(frm, to)
    return 0 <= i < 245 and mask[i]


def _board_eids(view: dict) -> list:
    return [m.get("eid") for m in view["me"].get("board") or []]


def _preview(game, seat: int, opp: int, n: int) -> float:
    out = game.debug(json.dumps({"cmd": "combat_preview", "a": seat, "b": opp,
                                 "n": n, "details": True}))
    d = json.loads(out)
    # win + half a tie; ties neither deal nor take placement damage
    return float(d.get("win_a", 0.0)) + 0.5 * float(d.get("tie", 0.0))


def candidate_orders(view: dict) -> list:
    """Named arrangements as permutations of current board indices."""
    board = view["me"].get("board") or []
    n = len(board)
    if n < 2:
        return []
    orders = {}
    orders["current"] = list(range(n))
    by_atk = sorted(range(n), key=lambda i: -board[i]["atk"])
    orders["atk_desc"] = by_atk
    taunts = [i for i in range(n) if "TAUNT" in (board[i].get("keywords") or [])]
    if taunts:
        carry = max((i for i in range(n) if i not in taunts), key=lambda i: board[i]["atk"],
                    default=None)
        if carry is not None:
            rest = [i for i in by_atk if i != taunts[0] and i != carry]
            orders["shield_carry"] = [taunts[0], carry] + rest
        orders["taunt_first"] = taunts + [i for i in by_atk if i not in taunts]
    # anti-cleave: interleave so no two top-attack minions sit adjacent
    if n >= 4:
        half = (n + 1) // 2
        evens, odds = by_atk[:half], by_atk[half:]
        spread = [i for pair in zip(evens, odds) for i in pair] + evens[len(odds):]
        if spread != by_atk:
            orders["spread"] = spread
    uniq, seen = [], set()
    for name, o in orders.items():
        if tuple(o) not in seen and o != list(range(n)):
            seen.add(tuple(o))
            uniq.append((name, o))
        elif o == list(range(n)) and "current" not in seen:
            seen.add("current")  # keep the identity only once, named "current"
            uniq.insert(0, ("current", o))
    return uniq


def universal_order(view: dict) -> list | None:
    """Roadmap 4: opponent-independent arrangement rules — no panel, no preview.

    windfury leftmost (attack early, attack often), then taunts (weakest first,
    so the strongest sits right beside the carry), then plain attackers by
    attack with aura/buff carriers pushed behind them, deathrattle summoners
    rightmost (their tokens flood in at the far end).
    """
    board = view["me"].get("board") or []
    n = len(board)
    if n < 2:
        return None

    def is_summoner(m) -> bool:
        t = (m.get("text") or "").lower()
        return "deathrattle" in t and "summon" in t

    def is_buffer(m) -> bool:
        t = (m.get("text") or "").lower()
        return any(k in t for k in ("your minions", "your other minions",
                                    "friendly minions"))

    kw = lambda i: board[i].get("keywords") or []
    windfury = [i for i in range(n) if "WINDFURY" in kw(i)]
    taunts = sorted((i for i in range(n) if "TAUNT" in kw(i)),
                    key=lambda i: (board[i]["atk"], i))     # strongest last
    summoners = [i for i in range(n) if is_summoner(board[i])]
    taken = set(windfury) | set(taunts) | set(summoners)
    rest = [i for i in range(n) if i not in taken]
    plain = sorted((i for i in rest if not is_buffer(board[i])),
                   key=lambda i: (-board[i]["atk"], i))
    buffers = sorted((i for i in rest if is_buffer(board[i])),
                     key=lambda i: (-board[i]["atk"], i))
    # no binding rule -> leave the arrangement alone (bare atk-desc reshuffles
    # were part of the ablated preview positioning; they are speculation here)
    if not (windfury or taunts or summoners or buffers):
        return None
    return windfury + taunts + plain + buffers + summoners


def apply_order(game, seat: int, order: list, view: dict) -> bool:
    """Move minions into `order` (a permutation of current indices); False if blocked."""
    board = view["me"].get("board") or []
    if len(board) != len(order):
        return False
    cur = list(range(len(board)))          # positions of indices, tracking shifts
    for target, src_want in enumerate(order):
        cur_pos = cur.index(src_want)
        if cur_pos == target:
            continue
        if not _move_legal(game, seat, cur_pos, target):
            return False
        game.step(seat, _move_idx(cur_pos, target))
        cur.pop(cur_pos)
        cur.insert(target, src_want)
    return True


def fix_positioning(game, seat: int, view: dict, sims: int) -> str:
    """Try the candidate arrangements, keep the best; returns the chosen name."""
    opp = view["me"].get("next_opponent")
    board = view["me"].get("board") or []
    if opp is None or len(board) < 2:
        return "skip"
    orders = candidate_orders(view)
    if not orders:
        return "skip"
    best_name, best_score, best_order = "current", -1.0, list(range(len(board)))
    for name, order in orders:
        fresh = json.loads(game.view(seat))
        if apply_order(game, seat, order, fresh):
            score = _preview(game, seat, opp, sims)
            if score > best_score:
                best_name, best_score, best_order = name, score, order
    fresh = json.loads(game.view(seat))
    apply_order(game, seat, best_order, fresh)
    return best_name
