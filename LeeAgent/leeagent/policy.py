"""Turn policy: score every legal action with transparent heuristics + memory biases.

Actions are decoded from the flat index space by arithmetic
(crates/taverngym/src/actions.rs layout), not by parsing names.

v2 (post Phase-1): the base heuristic was the measured bottleneck
(code arm -0.42 vs bot -0.09). This version scores cards by quality
(stat sum / tribe commitment), picks pending options by content, and adds
spend discipline to Upgrade / HeroPower. Every memory contribution records
the memory id, so the game log still shows why each action won.

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


_PREMIUM_KW = {"DIVINE_SHIELD", "TAUNT", "REBORN", "WINDFURY", "VENOMOUS", "POISONOUS"}


def card_quality(card: dict) -> float:
    """Minion value on the scripted bot's proven scale: stats + 3*tier + keywords."""
    if card.get("type") == "spell" or not card.get("tier"):
        return float(2 + (card.get("tier") or 0))
    v = float(card.get("atk", 0)) + float(card.get("hp", 0)) + 3.0 * card.get("tier", 0)
    if card.get("golden"):
        v += 6.0
    v += 3.0 * len(_PREMIUM_KW & set(card.get("keywords") or []))
    return v


def choose_pending(legal: list[int], view: dict) -> int:
    """Pending choice by content: cheap hero powers, strong discover options.

    Hero: prefer the cheaper Hero Power (usable every turn), armor as tiebreak.
    Discover / triple reward: highest stat sum, then tier; spells by tier.
    Deterministic on ties (lowest option index).
    """
    opts = sorted(i for i in legal if A_CHOOSE <= i < A_PLAY)
    if not opts:
        return sorted(legal)[0]
    pending = view["me"].get("pending") or {}
    options = pending.get("options") or []
    if not options:
        return opts[len(opts) // 2]
    if pending.get("kind") == "hero":
        def hero_score(o):
            power = o.get("hero_power") or {}
            return (-2.0 * (power.get("cost") or 0)
                    + 0.1 * (o.get("armor") or 0))
        best = max(range(len(options)), key=lambda k: (hero_score(options[k]), -k))
        idx = A_CHOOSE + best
        return idx if idx in opts else opts[0]

    def opt_score(o):
        if o.get("type") == "spell" or not o.get("tier"):
            return float(2 + (o.get("tier") or 0))
        return card_quality(o)

    # only options with a legal Choose action are candidates (e.g. unaffordable
    # trinkets are masked out), so score the legal indices directly
    best_idx, best_s = opts[0], None
    for idx in opts:
        k = idx - A_CHOOSE
        if 0 <= k < len(options):
            s = opt_score(options[k])
            if best_s is None or s > best_s:
                best_idx, best_s = idx, s
    return best_idx


def score_actions(view: dict, matched: list, legal: list[int], n_turn_actions: int = 0) -> list:
    """-> [(score, action_idx, label, why)], best first.

    Priority bands follow the scripted bot's proven order (play -> upgrade on
    curve -> sell-to-upgrade -> buy best -> power -> activate -> refresh), with
    the bot's value function; on top of that: memory biases, board-tribe
    commitment, and the positioning lookahead (which runs before EndTurn).
    """
    me = view["me"]
    shop = me.get("shop") or []
    hand = me.get("hand") or []
    board = me.get("board") or []
    gold = me.get("gold", 0)

    from .facts import extract_facts, norm_tribe
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

    board_quality = [card_quality(m) for m in board]
    hand_quality = [card_quality(c) for c in hand]
    board_ids = [m.get("id") for m in board]
    hand_ids = [c.get("id") for c in hand]
    minions_owned = sum(1 for c in hand if c.get("type") != "spell") + len(board)
    board_full = len(board) >= 7
    weakest_val = min(board_quality) if board_quality else -1.0
    best_shop_val = max((card_quality(c) for c in shop), default=-1.0)
    commit = {t for t, n in f["tribes"].items() if n >= 2}
    on_curve = (f["upgrade_price"] or 99) <= 3 or (
        f["turn"] > 2 * f["tier"] and gold >= (f["upgrade_price"] or 99))

    def pair_of(card) -> bool:
        cid = card.get("id")
        return bool(cid) and not card.get("golden") and (
            board_ids.count(cid) + hand_ids.count(cid) >= 1)

    scored = []
    for i in legal:
        d = decode(i)
        kind = d[0]
        score, why = 0.0, []
        if kind == "play":
            h, pos = d[1], d[2]
            card = hand[h] if h < len(hand) else {}
            is_spell = card.get("type") == "spell"
            if is_spell and pos > 0:
                score = -1.0
            else:
                score = 40.0 + 0.1 * (hand_quality[h] if h < len(hand_quality) else 0) + play_bonus
                why.append(f"play hand {h}")
                if not is_spell and pos == min(f["board_count"], N_BOARD - 1):
                    score += 1.0       # a new minion joins the right naturally
                elif not is_spell and pos > f["board_count"]:
                    score -= 3.0
        elif kind == "magnetize":
            score = 39.0
            why.append("magnetize")
        elif kind == "upgrade":
            if on_curve and f["tier"] < 6:
                score = 35.0
                why.append("on curve")
            else:
                score = -5.0
            # survival gate (ablated +0.09 dev / +0.08 holdout): levelling at low
            # health was the dominant death mode — buy tempo instead
            if (score > 0 and f["health"] < 20 and f["tier"] >= 3
                    and (f["upgrade_price"] or 99) > 3):
                score = -20.0
                why.append("low health: tempo over tier")
            score += up_bonus
        elif kind == "sell":
            j = d[1]
            is_weakest = board and j == min(range(len(board)), key=lambda k: board_quality[k])
            if (board_full and is_weakest and gold >= 3
                    and best_shop_val > weakest_val + 4):
                score = 34.0
                why.append("sell weakest for a better buy")
            elif allow_sell_trigger and is_weakest:
                score = 2.0
                why.append("trigger value")
            else:
                score = -2.0
        elif kind == "buy":
            slot = d[1]
            card = shop[slot] if slot < len(shop) else {}
            is_spell = card.get("type") == "spell"
            score = 10.0 + 0.5 * card_quality(card)
            why.append("buy")
            if not is_spell and pair_of(card):
                score += 15.0
                why.append("pair")
            t = {norm_tribe(r) for r in card.get("races") or []}
            hit = t & buy_tribe
            if hit:
                score += 8
                why.append(f"tribe bias {sorted(hit)}")
            elif not is_spell and t & commit:
                score += 4
                why.append(f"commit {sorted(t & commit)}")
            score += buy_any
            if not is_spell and minions_owned >= 7 and not pair_of(card):
                score = -1.0          # hand congestion gate (pairs still welcome)
                why.append("hand congested")
        elif kind == "power":
            slot = d[1]
            powers = me.get("hero_powers") or []
            cost = (powers[slot].get("cost", 2) if slot < len(powers) else 2)
            score = 8.0 if gold >= max(cost, 1) else -2.0
            if cost == 0:
                score = 9.0
            why.append(f"power {slot} (cost {cost})")
        elif kind == "activate":
            score = 7.0
            why.append("activate")
        elif kind == "gift":
            score = 7.5 if minions_owned < 7 else 0.0
            why.append("dark gift")
        elif kind == "refresh":
            score = 5.0 if (gold >= 3 and n_turn_actions < 40) else -2.0
            why.append("reroll")
        elif kind == "freeze":
            score = -0.5 + freeze_bonus
            why.append("freeze")
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
