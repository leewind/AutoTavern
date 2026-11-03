"""View -> facts (exact, code-checked) and the compact state text Nimble sees.

`when` prefiltering runs on facts only; the rendered text carries just enough
context for the semantic residue. Validated against the 2048-token per-pass cap
with <=16 slim candidates + <=8 questions.
"""

from __future__ import annotations

# Canonical short tribe names used in `when.tribe_min` / bias vocabulary.
_TRIBE_ALIASES = {"MECHANICAL": "MECH"}


def norm_tribe(race: str) -> str:
    r = (race or "").upper()
    return _TRIBE_ALIASES.get(r, r)


def extract_facts(view: dict) -> dict:
    me = view["me"]
    board = me.get("board") or []
    hand = me.get("hand") or []
    shop = me.get("shop") or []

    tribes: dict[str, int] = {}
    keywords: set[str] = set()
    for m in board:
        for r in m.get("races") or []:
            t = norm_tribe(r)
            tribes[t] = tribes.get(t, 0) + 1
        for k in m.get("keywords") or []:
            keywords.add(k)
    shop_tribes: dict[str, int] = {}
    for m in shop:
        for r in m.get("races") or []:
            t = norm_tribe(r)
            shop_tribes[t] = shop_tribes.get(t, 0) + 1

    # triple availability: two copies in hand of a card the shop also offers
    hand_ids = {}
    for c in hand:
        if c.get("id"):
            hand_ids[c["id"]] = hand_ids.get(c["id"], 0) + 1
    shop_ids = {c.get("id") for c in shop}
    hand_dup_in_shop = any(n >= 2 and cid in shop_ids for cid, n in hand_ids.items())

    board_texts = [m.get("text") or "" for m in board]

    # the next opponent's scouted board (what the client showed of them)
    nxt = me.get("next_opponent")
    opp_entry = next((o for o in view.get("opponents") or [] if o.get("id") == nxt), None)
    opp_seen = (opp_entry or {}).get("seen_board") or []
    opp_seen_board = len(opp_seen) if opp_entry else None
    opp_seen_keywords = sorted({k for m in opp_seen for k in (m.get("keywords") or [])})

    hand_limit = me.get("hand_limit") or 10
    alive_raw = view.get("alive")
    # the debug view reports the alive count as an int
    num_alive = alive_raw if isinstance(alive_raw, int) else sum(1 for a in alive_raw or [] if a)

    return {
        "turn": view["turn"],
        "health": me["health"],
        "armor": me.get("armor") or 0,
        "tier": me["tier"],
        "hero_id": (me.get("hero") or {}).get("id"),
        "gold": me["gold"],
        "gold_cap": me.get("max_gold") or 10,
        "hand_count": len(hand),
        "hand_limit": hand_limit,
        "hand_full": len(hand) >= hand_limit,
        "board_count": len(board),
        "board_full": len(board) >= 7,
        "shop_count": len(shop),
        "upgrade_price": me.get("upgrade_price"),
        "tribes": tribes,
        "keywords": sorted(keywords),
        "shop_tribes": shop_tribes,
        "hand_dup_in_shop": hand_dup_in_shop,
        "board_texts": board_texts,
        "opp_seen_board": opp_seen_board,
        "opp_seen_more": (opp_seen_board or -1) > len(board),
        "opp_seen_keywords": opp_seen_keywords,
        "num_alive": num_alive or 0,
        "next_is_ghost": bool(me.get("next_is_ghost")),
        "next_opponent": me.get("next_opponent"),
        "win_streak": me.get("win_streak") or 0,
        "pending": bool(me.get("pending")),
    }


_KW = {
    "DIVINE_SHIELD": "Divine Shield", "TAUNT": "Taunt", "VENOMOUS": "Venomous",
    "POISONOUS": "Poisonous", "REBORN": "Reborn", "WINDFURY": "Windfury",
    "MEGA_WINDFURY": "Mega-Windfury", "CLEAVE": "Cleave", "STEALTH": "Stealth",
    "MAGNETIC": "Magnetic",
}


def _kw(k: str) -> str:
    return _KW.get(k, k.replace("_", " ").title())


def _minion_line(m: dict, i: int) -> str:
    if m.get("type") == "spell":
        return f"  {i}. {m['name']} (Tavern spell)"
    races = "/".join(norm_tribe(r).title() for r in m.get("races", [])) or "No tribe"
    kws = ", ".join(_kw(k) for k in m.get("keywords", []))
    gold = "Golden " if m.get("golden") else ""
    s = f"  {i}. {gold}{m['name']} ({races}, tier {m['tier']}) {m['atk']}/{m['hp']}"
    if kws:
        s += f" [{kws}]"
    att = m.get("attached") or []
    if att:
        s += " (attached: " + ", ".join(a.get("name", "?") for a in att) + ")"
    return s


def _zone(title: str, minions: list) -> str:
    lines = [f"{title}:"]
    if not minions:
        lines.append("  (empty)")
    lines += [_minion_line(m, i) for i, m in enumerate(minions)]
    return "\n".join(lines)


def render_state(view: dict) -> str:
    """The compact player view sent to Nimble (adapted from tavernbench.render).

    Carries the fields the remaining semantic situations depend on: win streak
    and the scouted next-opponent board summary (full texts stay out of budget).
    """
    me = view["me"]
    header = (f"Turn {view['turn']}. Your health {me['health']}. Tavern tier {me['tier']}. "
              f"Gold {me['gold']}. Upgrade price {me.get('upgrade_price', '?')}. "
              f"Win streak {me.get('win_streak') or 0}.")
    parts = [header,
             _zone("Your warband", me.get("board") or []),
             _zone("Your hand", me.get("hand") or []),
             _zone("Tavern", me.get("shop") or [])]
    nxt = me.get("next_opponent")
    entry = next((o for o in view.get("opponents") or [] if o.get("id") == nxt), None)
    seen = (entry or {}).get("seen_board") or []
    if entry is not None:
        if seen:
            atk = sum(m.get("atk", 0) for m in seen)
            kws = sorted({k for m in seen for k in (m.get("keywords") or [])})
            kws_s = f", keywords: {', '.join(_kw(k) for k in kws)}" if kws else ""
            parts.append(f"Next opponent's scouted board ({len(seen)} minions, "
                         f"total attack {atk}{kws_s}): "
                         + "; ".join(f"{m.get('name')} {m.get('atk')}/{m.get('hp')}"
                                     for m in seen))
        else:
            parts.append("Next opponent's board: not scouted yet.")
    return "\n".join(parts)
