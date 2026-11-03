"""Comp recipes (HSReplay archetypes mapped onto this pool) + causal tier list.

Phase A: 14 (tribe, mechanism) recipes, cores curated from the catalog's
card texts (hsreplay.net/battlegrounds/comps archetype list as the
reference; card identities are pool-specific, mechanisms transfer).
Phase B: forced-assembly measurement — from turn 4 every un-owned core is
persistently injected into the shop (policy still buys at real cost, may
decline), vs vanilla on paired seeds. Output = the engine's own tier list
of what actually wins here.

Text priors never ship directly: only recipes that measurably win advance
to integration (and then the paired adopt gate decides).

    ../.venv/bin/python scripts/recipe_gate.py [--n 50] [--seed0 130000]
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from leeagent import memory as M                    # noqa: E402
from leeagent.config import ROOT as CFG_ROOT        # noqa: E402

BASE_BANK = M.load(CFG_ROOT / "memories" / "seed.jsonl")

# (name, tribe) with cores resolved by card name below — curated from
# catalog texts against the HSReplay archetype mechanisms
TRIBES = {
    "beast_summons": "BEAST", "beast_rally": "BEAST",
    "dragon_spells": "DRAGON", "dragon_battlecry": "DRAGON",
    "mech_magnetics": "MECH", "mech_divine_shield": "MECH",
    "mech_deathrattle": "MECH", "murloc_hand": "MURLOC",
    "undead_reborn": "UNDEAD", "undead_spells": "UNDEAD",
    "demon_consume": "DEMON", "demon_hero_damage": "DEMON",
    "elemental_refresh": "ELEMENTAL", "pirate_bounty": "PIRATE",
    "pirate_gold_spend": "PIRATE", "quilboar_gems": "QUILBOAR",
    "quilboar_gem_econ": "QUILBOAR",
}

CORES = {
    "beast_summons": ["Lurking Leviathan", "Banana Slamma",
                      "Hoarding Hyena", "Deathstrider"],
    "beast_rally": ["Wolf Pup", "Cage Gnawer", "Goldrinn, the Great Wolf"],
    "dragon_spells": ["Timecap'n Hooktail", "Blue Whelp",
                      "Felfire Conjurer"],
    "dragon_battlecry": ["Kalecgos, Arcane Aspect", "Draconic Warden"],
    "mech_magnetics": ["Utility Drone", "Spark Snapper",
                       "Resourceful Robot", "Auto Reveille"],
    "mech_divine_shield": ["Relentless Deflector", "Charging Czarina"],
    "mech_deathrattle": ["Rescue Bot", "Falling Sky Golem"],
    "murloc_hand": ["Bream Counter", "Choral Mrrrglr",
                    "Shamanic Tidecaller"],
    "undead_reborn": ["Eternal Summoner", "Barrier Banshee",
                      "Snazzy Phantom", "Plaguerunner"],
    "undead_spells": ["Forsaken Weaver", "Friendly Geist"],
    "demon_consume": ["Flaming Enforcer", "Insatiable Ur'zul",
                      "Felboar", "Soulkeeping Jailer"],
    "demon_hero_damage": ["Tichondrius", "Ashen Corruptor",
                          "Devout Hellcaller"],
    "elemental_refresh": ["Waveling", "En-Djinn Blazer",
                          "Refreshing Anomaly", "Living Azerite"],
    "pirate_bounty": ["Proud Privateer", "Sky Admiral Rogers",
                      "Bigwig Bandit", "Shipwrecked Rascal"],
    "pirate_gold_spend": ["Gunpowder Courier", "Enterprising Escapee"],
    "quilboar_gems": ["Hot-Air Surveyor", "Geomagus Roogug",
                      "Sanguine Champion", "Bonker"],
    "quilboar_gem_econ": ["Gem Rat", "Trench Fighter", "Mangled Bandit"],
}


def resolve_ids() -> list:
    """Attach card ids by name so the recipe table stays reviewable."""
    import taverngym
    by_name = {c["name"]: c["id"] for c in json.loads(taverngym.catalog_json())}
    out = []
    for name, tribe in TRIBES.items():
        ids = []
        for n in CORES[name]:
            cid = by_name.get(n)
            if not cid:
                print(f"  !! {name}: '{n}' not in catalog, dropped")
                continue
            ids.append(cid[:-2] if cid.endswith("_G") else cid)
        if len(ids) >= 2:
            out.append((name, tribe, ids))
        else:
            print(f"  !! {name}: <2 cores, dropped")
    return out


def norm_cid(cid: str | None) -> str | None:
    if not cid:
        return None
    return cid[:-2] if cid.endswith("_G") else cid


def play_recipe(job):
    """One seat-0 game. ON arm persistently offers every un-owned recipe
    core from turn 4 (real cost, policy may decline)."""
    name, cores, arm, seed = job
    import taverngym
    from leeagent import gate
    from leeagent.config import thresholds

    g = taverngym.Game(seed=seed)
    agent = gate.LeeAgent(BASE_BANK, th=thresholds(), use_nimble=False)
    agent.reset()
    agent._turn_seen = -1
    owned: set[str] = set()
    inj_turn = -1
    guard = 0
    while not g.is_over() and guard < 100000:
        for p in range(g.num_players):
            if not g.needs_action(p):
                continue
            if p == 0:
                if arm == "on" and len(owned) < len(cores):
                    view = json.loads(g.view(0))
                    me = view["me"]
                    turn = view["turn"]
                    have = {norm_cid(c.get("id")) for c in
                            (me.get("board") or []) + (me.get("hand") or [])}
                    owned |= {c for c in cores if c in have}
                    if turn >= 4 and turn != inj_turn:
                        for c in cores:
                            if c not in owned:
                                g.debug(json.dumps(
                                    {"cmd": "add_minion", "p": 0,
                                     "zone": "shop", "card": c}))
                        inj_turn = turn
                g.step(p, agent.choose(g, 0))
            else:
                g.step(p, g.bot_action(p))
        guard += 1
    if not g.is_over():
        return None
    return {"name": name, "arm": arm, "seed": seed,
            "place": int(list(g.placements())[0]), "owned": len(owned)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed0", type=int, default=130_000)
    a = ap.parse_args()
    recipes = resolve_ids()
    print(f"{len(recipes)} recipes x {a.n} paired seeds x 2 arms", flush=True)
    jobs = [(name, ids, arm, a.seed0 + i)
            for name, _t, ids in recipes for arm in ("on", "off")
            for i in range(a.n)]
    with mp.Pool(96) as pool:
        recs = [r for r in pool.imap_unordered(play_recipe, jobs,
                                               chunksize=8)
                if r is not None]
    out = []
    for name, tribe, ids in recipes:
        on = {r["seed"]: r for r in recs
              if r["arm"] == "on" and r["name"] == name}
        off = {r["seed"]: r for r in recs
               if r["arm"] == "off" and r["name"] == name}
        # evaluable = the ON arm actually assembled most of the recipe
        asm = {s for s in on if s in off
               and on[s]["owned"] >= max(2, len(ids) - 1)}
        if not asm:
            out.append({"name": name, "tribe": tribe, "n_asm": 0})
            continue
        d = [on[s]["place"] - off[s]["place"] for s in asm]
        m = sum(d) / len(d)
        var = sum((x - m) ** 2 for x in d) / max(len(d) - 1, 1)
        t = m / (var / len(d)) ** 0.5 if var else 0.0
        out.append({"name": name, "tribe": tribe, "cores": ids,
                    "n_asm": len(asm), "owned_avg": round(
                        sum(on[s]["owned"] for s in asm) / len(asm), 2),
                    "delta": round(m, 3), "t": round(t, 2),
                    "better/worse": [sum(1 for x in d if x < 0),
                                     sum(1 for x in d if x > 0)]})
    out.sort(key=lambda r: r.get("delta", 9))
    for r in out:
        print(f"  {r['name']:<22} {r['tribe'][:4]:<5} asm={r.get('n_asm', 0):2d} "
              f"delta={r.get('delta', float('nan')):+.3f} "
              f"t={r.get('t', float('nan')):+.1f}", flush=True)
    p = ROOT / "runs" / "recipe_tier.json"
    p.write_text(json.dumps(out, indent=1))
    print(f"-> {p}")


if __name__ == "__main__":
    main()
