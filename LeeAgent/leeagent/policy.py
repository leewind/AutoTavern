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

# tunable policy constants (coordinate-ascent trained; see scripts/param_sweep.py)
SWAP_MARGIN = 10          # slot-upgrade: best_shop must beat weakest by this
SCOUT_BEHIND = 0.30       # combat-preview win rate below this = all-in tempo
HP_GATE = 20              # no levelling below this health past tier 3
CURVE_MULT = 2.0          # upgrade on curve when turn > CURVE_MULT * tier
COMP_BUY_BASE = 0.0       # comp-race buy bonus (plus engine-text value);
                          # flat race bonus ablated to 0 — engines carry the value
OFFCOMP_TAX = 4.0         # off-comp minion buy penalty (waived when behind)
COMP_SELL_PROTECT = 6.0   # sell-value protection for comp pieces


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

# empirical hero strength (scripts/hero_table.py: 115 heroes x 64 v16 games)
_HERO_TABLE = None


def _hero_table() -> dict:
    global _HERO_TABLE
    if _HERO_TABLE is None:
        import json
        from pathlib import Path
        p = Path(__file__).resolve().parents[1] / "data" / "hero_table.json"
        _HERO_TABLE = json.loads(p.read_text()) if p.is_file() else {}
    return _HERO_TABLE


# empirical trinket strength (scripts/trinket_table.py: window-matched forcing)
_TRINKET_TABLE = None


def _trinket_table() -> dict:
    global _TRINKET_TABLE
    if _TRINKET_TABLE is None:
        import json
        from pathlib import Path
        p = Path(__file__).resolve().parents[1] / "data" / "trinket_table.json"
        _TRINKET_TABLE = json.loads(p.read_text()) if p.is_file() else {}
    return _TRINKET_TABLE


# empirical card-synergy lifts (scripts/synergy_gen.py + synergy_table.py:
# E[reward | S bought with C on board] - E[reward | S bought without C],
# per committed direction; sig edges only)
_SYNERGY_TABLE = None
SYNERGY_W = 0.0          # gate-rejected 2026-11-03 (dev +0.14 / holdout -0.14,
                         # both n.s.; runs/synergy_gate_paired.json) — re-enable
                         # only with a stronger estimator and a fresh paired gate


def _synergy_table() -> dict:
    global _SYNERGY_TABLE
    if _SYNERGY_TABLE is None:
        import json
        from pathlib import Path
        p = Path(__file__).resolve().parents[1] / "data" / "synergy_table.json"
        _SYNERGY_TABLE = json.loads(p.read_text()) if p.is_file() else {}
    return _SYNERGY_TABLE


def synergy_bonus(card_id: str | None, board_ids: list, comp: str | None) -> float:
    """Empirical lift of buying card_id on top of the current board, inside the
    committed direction (the "growth support" signal: strong edges mean the
    card has historically finished better alongside exactly this board)."""
    if not card_id or not comp:
        return 0.0
    edges = _synergy_table().get(comp, {}).get(card_id) or {}
    if not edges:
        return 0.0
    total = sum(e["lift"] for c in board_ids if (e := edges.get(c or ""))
                and e.get("sig"))
    return SYNERGY_W * total


# adopted fixed pairs (scripts/pair_gate.py: forced-availability screen,
# then a fresh-seed three-arm repro where the support's marginal vs a
# core-only control had to be <= -0.15 places; gain is that marginal)
_FIXED_PAIRS = None
FIXED_PAIR_W = 0.0       # adopt-gate rejected 2026-11-03 (dev -0.07 / holdout
                         # -0.06, both n.s., 97%/94% of games decision-unchanged;
                         # runs/pair_adopt_gate.json). The 6 pairs are real
                         # knowledge (1-place support marginals under forced
                         # availability) — see the freeze/anchor re-open paths
                         # in the roadmap before re-wiring this weight.


def _fixed_pairs() -> list:
    global _FIXED_PAIRS
    if _FIXED_PAIRS is None:
        import json
        from pathlib import Path
        p = Path(__file__).resolve().parents[1] / "data" / "fixed_pairs.json"
        d = json.loads(p.read_text()) if p.is_file() else {}
        _FIXED_PAIRS = d.get("pairs") or []
    return _FIXED_PAIRS


def fixed_pair_bonus(card_id: str | None, owned_ids: set) -> float:
    """Buy bias for a support card whose adopted fixed-pair core is already
    owned. The pair was measured under forced availability; here we only
    steer — availability stays natural, and the paired adopt gate is the
    arbiter of realized value."""
    if not card_id:
        return 0.0
    bonus = 0.0
    for pr in _fixed_pairs():
        if pr["support"] == card_id and pr["core"] in owned_ids:
            bonus += FIXED_PAIR_W * min(abs(pr["gain"]), 0.5)
    return bonus


FREEZE_FIX = False      # idempotency guard: no freeze bonus while the shop
                         # is already frozen (kills the M020 toggle loop)
FREEZE_BIAS = True      # consume M020's prefer_freeze bonus at all
PAIR_FREEZE = 0.0       # freeze-gate rejected 2026-11-03 (dev +0.00 / holdout
                         # -0.06, 95%/97% of games decision-unchanged;
                         # runs/pair_freeze_gate.json). A 6-pair list x natural
                         # availability is too sparse to move aggregates —
                         # re-open only with a much larger causally-screened
                         # list or comp-level priors.


def pair_partner_unfrozen(shop: list, owned_ids: set) -> bool:
    """An adopted fixed-pair support sitting unfrozen in this shop with its
    core already owned — the freeze-worthy situation. The frozen check keeps
    the freeze button (a whole-shop toggle) from looping."""
    for card in shop:
        cid = card.get("id") or ""
        if not cid or card.get("frozen"):
            continue
        if cid.endswith("_G"):
            cid = cid[:-2]
        for pr in _fixed_pairs():
            if pr["support"] == cid and pr["core"] in owned_ids:
                return True
    return False

_TRIBES = ("beast", "dragon", "mech", "murloc", "undead", "demon",
           "elemental", "pirate", "quilboar")


def trinket_score(o: dict, facts: dict) -> float:
    """Text heuristic for trinket offers (all show tier 0 / 0 stats).

    Rewards ongoing aura/economy effects, penalises conditional triggers and
    tribes the board does not run; cheaper is a little better (tempo).
    """
    t = (o.get("text") or "").lower()
    s = 0.0
    for kw, w in (("divine shield", 4), ("extra time", 4), ("trigger", 2),
                  ("start of each turn", 3), ("start of your turn", 3),
                  ("end of your turn", 2), ("your minions", 3), ("have +", 3),
                  ("gains +", 3), ("golden", 2), ("tier 6", 2), ("tier 5", 1.5),
                  ("gold", 1.5), ("refresh", 1.0), ("venomous", 4), ("reborn", 3)):
        if kw in t:
            s += w
    for kw in ("when you buy", "after you play", "last game", "if you"):
        if kw in t:
            s -= 2
    tribes_have = {tr.lower() for tr in facts.get("tribes", {})}
    for tr in _TRIBES:
        if tr in t and tr not in tribes_have:
            s -= 3
    s -= 0.5 * (o.get("cost") or 0)
    return s


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
        table = _hero_table()

        def hero_score(o):
            t = table.get(o.get("id") or "")
            if t:                      # empirical mean placement: lower is better
                return -t["mean_place"]
            power = o.get("hero_power") or {}   # fallback for unseen heroes
            return (-2.0 * (power.get("cost") or 0)
                    + 0.1 * (o.get("armor") or 0)) / 10.0
        best = max(range(len(options)), key=lambda k: (hero_score(options[k]), -k))
        idx = A_CHOOSE + best
        return idx if idx in opts else opts[0]

    def opt_score(o):
        if pending.get("kind") == "trinket":
            t = _trinket_table().get(o.get("id") or "")
            if t and t.get("n", 0) >= 10:          # empirical beats text heuristics
                return 100.0 - t["mean_place"]
            from .facts import extract_facts
            return trinket_score(o, extract_facts(view))
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


def score_actions(view: dict, matched: list, legal: list[int], n_turn_actions: int = 0,
                  scout: float | None = None, buy_hint: int | None = None,
                  comp: str | None = None, no_upgrade: bool = False) -> list:
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
    own_base = {c[:-2] if c and c.endswith("_G") else c
                for c in board_ids + hand_ids}
    minions_owned = sum(1 for c in hand if c.get("type") != "spell") + len(board)
    board_full = len(board) >= 7
    weakest_val = min(board_quality) if board_quality else -1.0
    best_shop_val = max((card_quality(c) for c in shop), default=-1.0)
    commit = {t for t, n in f["tribes"].items() if n >= 2}
    on_curve = (f["upgrade_price"] or 99) <= 3 or (
        f["turn"] > CURVE_MULT * f["tier"] and gold >= (f["upgrade_price"] or 99))

    def pair_of(card) -> bool:
        cid = card.get("id")
        return bool(cid) and not card.get("golden") and (
            board_ids.count(cid) + hand_ids.count(cid) >= 1)

    def copies_owned(card) -> int:
        cid = card.get("id")
        if not cid or card.get("golden"):
            return 0
        return board_ids.count(cid) + hand_ids.count(cid)

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
            # scouting: clearly behind in the next fight -> tempo over tier;
            # clearly ahead -> keep scaling (the one adaptive edge the bot lacks)
            if scout is not None and score > 0 and (f["upgrade_price"] or 99) > 3:
                if scout < SCOUT_BEHIND:
                    score = -15.0
                    why.append(f"behind (scout {scout:.2f})")
                elif scout > 0.55:
                    score += 6.0
                    why.append(f"ahead (scout {scout:.2f})")
            # survival gate (ablated +0.09 dev / +0.08 holdout): levelling at low
            # health was the dominant death mode — buy tempo instead
            if (score > 0 and f["health"] < HP_GATE and f["tier"] >= 3
                    and (f["upgrade_price"] or 99) > 3):
                score = -20.0
                why.append("low health: tempo over tier")
            if score > 0 and no_upgrade:
                score = -30.0             # value model: best buy beats tier
                why.append("value gate")
            score += up_bonus
        elif kind == "sell":
            j = d[1]
            # comp pieces are protected: the engine the comp runs on is worth
            # more than its stats
            sell_quality = list(board_quality)
            if comp:
                for k, m in enumerate(board):
                    t = {norm_tribe(r) for r in m.get("races") or []}
                    if comp in t:
                        sell_quality[k] += COMP_SELL_PROTECT
            is_weakest = board and j == min(range(len(board)), key=lambda k: sell_quality[k])
            if (board_full and is_weakest and gold >= 3
                    and best_shop_val > weakest_val + 4):
                score = 34.0
                why.append("sell weakest for a better buy")
            elif (is_weakest and len(board) >= 4 and f["turn"] >= 8 and gold >= 3
                    and best_shop_val > weakest_val + SWAP_MARGIN):
                score = 9.0            # mid-game slot upgrade (ablated +0.02/+0.015)
                if scout is not None and scout < SCOUT_BEHIND:
                    score = -2.0       # behind: never trade a body away this turn
                    why.append("behind: keep bodies")
                else:
                    why.append("slot upgrade")
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
            if not is_spell and copies_owned(card) >= 2:
                score += 25.0          # the third copy: golden + triple reward
                if comp and comp in {norm_tribe(r) for r in card.get("races") or []}:
                    score += 5.0
                    why.append("comp triple!")
                why.append("triple!")
            t = {norm_tribe(r) for r in card.get("races") or []}
            if comp and not is_spell:
                if comp in t:
                    from .comp import engine_text_bonus, recipe_core_bonus
                    score += COMP_BUY_BASE + engine_text_bonus(card)
                    why.append(f"comp {comp}")
                    rb = recipe_core_bonus(card.get("id"), own_base, comp)
                    if rb:
                        score += rb
                        why.append(f"recipe {rb:+.0f}")
                elif scout is None or scout >= SCOUT_BEHIND:
                    score -= OFFCOMP_TAX   # off-comp tax (waived when behind)
                    why.append("off-comp")
                syn = synergy_bonus(card.get("id"), board_ids, comp)
                if syn:
                    score += syn
                    why.append(f"synergy {syn:+.1f}")
            if not is_spell:
                # fixed pairs fire regardless of comp state (they were
                # measured that way); goldens count as their base card
                base = card.get("id") or ""
                fp = fixed_pair_bonus(
                    base[:-2] if base.endswith("_G") else base, own_base)
                if fp:
                    score += fp
                    why.append(f"fixed-pair {fp:+.0f}")
            hit = t & buy_tribe
            if hit:
                score += 8
                why.append(f"tribe bias {sorted(hit)}")
            elif not is_spell and t & commit:
                score += 4
                why.append(f"commit {sorted(t & commit)}")
            score += buy_any
            if buy_hint is not None and i == buy_hint:
                score += 6.0
                why.append("lookahead pick")
            if scout is not None and scout < SCOUT_BEHIND and not is_spell:
                score += 4.0           # behind: any body helps the next fight
                why.append("behind: tempo buy")
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
            # freeze toggles the WHOLE shop: the memory bonus only applies
            # while it is unfrozen — without the guard M020 (+6) pressed it
            # ~10x/turn (v18 toggle loop, all arms shared the bug).
            # FREEZE_BIAS=False additionally zeroes the bonus: M020's sticky
            # freeze measurably hurt once the guard made it stick.
            shop_frozen = any(c.get("frozen") for c in shop)
            bonus = freeze_bonus if FREEZE_BIAS else 0.0
            if FREEZE_FIX and shop_frozen:
                score = -1.5
            else:
                score = -0.5 + bonus
            why.append("freeze")
            # fixed-pair availability: freezing is the legal way to keep an
            # adopted support in the shop until it is buyable ("meet it,
            # keep it"). The button toggles ALL cards, so only fire while
            # the partner is unfrozen (no toggle loop) and not buyable now.
            if PAIR_FREEZE and (gold < 3 or f["hand_full"]) \
                    and pair_partner_unfrozen(shop, own_base):
                score = PAIR_FREEZE
                why.append("pair freeze")
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
