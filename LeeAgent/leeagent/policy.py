"""Turn policy: score every legal action with transparent heuristics + memory biases.

Actions are decoded from the flat index space by arithmetic
(crates/taverngym/src/actions.rs layout), not by parsing names — names are
Rust-Debug formatted and easy to mis-pattern-match.

The Phase-0 baseline is deliberately simple and readable: the point is a
measurable starting point the memory bank and the gate improve on. Every memory
contribution records the memory id, so the game log shows why each action won.

Bias vocabulary (what a memory's `bias` may ask the policy to do):
  prefer_buy_tribe: TRIBE        bonus for buying that tribe
  prefer_buy_any: N              flat bonus for any buy
  prefer_upgrade: N              bonus for Upgrade
  prefer_freeze: N               bonus for Freeze
  prefer_endturn: N              bonus for EndTurn (nothing left to do)
  prefer_play: N                 bonus for playing hand cards
  penalize_endturn_with_gold: N  penalty for EndTurn while gold >= 4
  sell_to_trigger: true          sells allowed for deathrattle/avenge value
"""

from __future__ import annotations

# flat action space layout (N_ACTIONS = 245)
A_END, A_REFRESH, A_FREEZE, A_UPGRADE = 0, 1, 2, 3
A_HERO_POWER, N_POWERS, A_DARK_GIFT, A_CANCEL = 4, 2, 6, 7
A_BUY, N_SHOP = 8, 8
A_SELL, N_BOARD = 16, 7
A_ACTIVATE = 23
A_CHOOSE, N_CHOICE = 30, 16
A_PLAY, N_POS = 46, 8          # + hand * 8 + pos   (spells: pos 0 only)
A_MAGNETIZE = 126              # + hand * 7 + board
A_MOVE = 196                   # + from * 7 + to
N_ACTIONS = 245


def legal_actions(game, seat: int) -> list[int]:
    mask = game.legal_mask(seat)
    return [i for i in range(N_ACTIONS) if mask[i]]


def decode(i: int):
    if i == A_END:
        return ("end",)
    if i == A_REFRESH:
        return ("refresh",)
    if i == A_FREEZE:
        return ("freeze",)
    if i == A_UPGRADE:
        return ("upgrade",)
    if A_HERO_POWER <= i < A_DARK_GIFT:
        return ("power", i - A_HERO_POWER)
    if i == A_DARK_GIFT:
        return ("gift",)
    if i == A_CANCEL:
        return ("cancel",)
    if A_BUY <= i < A_SELL:
        return ("buy", i - A_BUY)
    if A_SELL <= i < A_ACTIVATE:
        return ("sell", i - A_SELL)
    if A_ACTIVATE <= i < A_CHOOSE:
        return ("activate", i - A_ACTIVATE)
    if A_CHOOSE <= i < A_PLAY:
        return ("choose", i - A_CHOOSE)
    if A_PLAY <= i < A_MAGNETIZE:
        k = i - A_PLAY
        return ("play", k // N_POS, k % N_POS)
    if A_MAGNETIZE <= i < A_MOVE:
        k = i - A_MAGNETIZE
        return ("magnetize", k // N_BOARD, k % N_BOARD)
    k = i - A_MOVE
    return ("move", k // N_BOARD, k % N_BOARD)


def choose_pending(legal: list[int]) -> int:
    """Pending choice: deterministic middle option (Phase-0 placeholder)."""
    opts = sorted(i for i in legal if A_CHOOSE <= i < A_PLAY)
    if opts:
        return opts[len(opts) // 2]
    return sorted(legal)[0]


def score_actions(view: dict, matched: list, legal: list[int]) -> list:
    """-> [(score, action_idx, label, why)], best first."""
    me = view["me"]
    shop = me.get("shop") or []
    hand = me.get("hand") or []
    board = me.get("board") or []
    gold = me.get("gold", 0)
    health = me.get("health", 30)
    hand_full = len(hand) >= (me.get("hand_limit") or 10)
    board_full = len(board) >= 7

    from .facts import extract_facts, norm_tribe  # local import avoids a cycle at load
    f = extract_facts(view)

    biases = [m.get("bias") or {} for m, _p in matched]
    buy_tribe = {b["prefer_buy_tribe"] for b in biases if "prefer_buy_tribe" in b}
    buy_any = max((b.get("prefer_buy_any", 0) for b in biases), default=0)
    up_bonus = max((b.get("prefer_upgrade", 0) for b in biases), default=0)
    freeze_bonus = max((b.get("prefer_freeze", 0) for b in biases), default=0)
    play_bonus = max((b.get("prefer_play", 0) for b in biases), default=0)
    end_bonus = max((b.get("prefer_endturn", 0) for b in biases), default=0)
    et_gold_pen = max((b.get("penalize_endturn_with_gold", 0) for b in biases), default=0)
    allow_sell_trigger = any(b.get("sell_to_trigger") for b in biases)

    scored = []
    for i in legal:
        d = decode(i)
        kind = d[0]
        score, why = 0.0, []
        if kind == "buy":
            slot = d[1]
            card = shop[slot] if slot < len(shop) else {}
            score = 10.0
            why.append("buy")
            t = {norm_tribe(r) for r in card.get("races") or []}
            hit = t & buy_tribe
            if hit:
                score += 8
                why.append(f"tribe {sorted(hit)}")
            if card.get("tier", 9) <= f["tier"] + 1:
                score += 2
            score += buy_any
            if hand_full and card.get("type") != "spell":
                score -= 5
                why.append("hand full")
        elif kind == "play":
            h = d[1]
            card = hand[h] if h < len(hand) else {}
            score = 9.0 + play_bonus
            why.append(f"play hand {h}")
            if card.get("type") == "spell" and d[2] > 0:
                score = -1.0  # spells only play at pos 0; illegal variants score low
        elif kind == "sell":
            j = d[1]
            weakest = board and j == min(range(len(board)),
                                         key=lambda k: board[k]["atk"] + board[k]["hp"])
            if board_full:
                score = 3.0 if weakest else 1.0
                why.append("make room")
            elif allow_sell_trigger and weakest:
                score = 2.0
                why.append("trigger value")
            else:
                score = -2.0
        elif kind == "upgrade":
            price = me.get("upgrade_price") or 99
            score = 6.0 if health > 20 else 2.0
            if gold < price:
                score = -5.0
            score += up_bonus
            why.append("upgrade")
        elif kind == "power":
            score = 4.0 if gold >= 2 else -2.0
            why.append(f"power {d[1]}")
        elif kind == "refresh":
            score = 0.5 if gold >= 4 else -2.0
            why.append("reroll")
        elif kind == "freeze":
            score = -0.5 + freeze_bonus
            why.append("freeze")
        elif kind == "magnetize":
            score = 6.0
            why.append("magnetize")
        elif kind == "activate":
            score = 3.0
            why.append("activate")
        elif kind == "gift":
            score = 1.0
            why.append("dark gift")
        elif kind == "end":
            score = float(end_bonus)
            if gold >= 4 and et_gold_pen:
                score -= et_gold_pen
                why.append("unspent gold")
        elif kind == "move":
            score = -1.0  # reordering is handled by the lookahead, not greedily
        elif kind == "cancel":
            score = -3.0
        else:  # choose handled elsewhere
            score = 0.0
        label = kind if len(d) == 1 else f"{kind}:{','.join(map(str, d[1:]))}"
        scored.append((score, i, label, why))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return scored
