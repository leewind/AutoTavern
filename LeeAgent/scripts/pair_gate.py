"""Forced-pair experiments: measure a two-card package by intervention.

The observational synergy table only nominates candidates (its lifts lost
the gate); this script measures them the trinket-table way — intervene on
availability, let the policy decide at real cost, compare final placements
on paired seeds.

  screen  stage 1: top synergy-table pairs, ON (inject core C, then support
          S once C is owned) vs OFF (vanilla), 50 paired seeds per pair.
          delta_place on assembled games <= -0.25 with n_assembled >= 15
          advances (multiplicity filter #1).
  repro   stage 2: winners re-run on fresh seeds; a pair enters
          data/fixed_pairs.json only if it replicates (delta < 0 again and
          combined <= -0.15) — the false-positive lesson from the 9 memory
          candidates.
  adopt   final arbiter: policy with fixed-pair bias ON vs OFF (no
          injections anywhere), dev 300-399 + holdout 400-499; a fresh
          repro set confirms before anything is reported.

Construction seeds only (100000+/110000+); dev/holdout stay untouched
until the adopt stage.

    ../.venv/bin/python scripts/pair_gate.py --stage screen
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from leeagent import memory as M                    # noqa: E402
from leeagent.config import ROOT as CFG_ROOT        # noqa: E402

BASE_BANK = M.load(CFG_ROOT / "memories" / "seed.jsonl")
SCREEN_SEED0, N_SCREEN = 100_000, 50
REPRO_SEED0, N_REPRO = 110_000, 50
TOPK = 64


def norm_cid(cid: str | None) -> str | None:
    if not cid:
        return None
    return cid[:-2] if cid.endswith("_G") else cid


def play_pair(job):
    """One seat-0 game, arms:
      on   persistent injection of core, then support once core is owned
      core persistent injection of the core only (the control that separates
           pair value from generic always-an-extra-option value)
      off  vanilla
    The policy still buys at real cost or declines."""
    core, support, tribe, arm, seed = job
    import taverngym
    from leeagent import gate
    from leeagent.config import thresholds

    g = taverngym.Game(seed=seed)
    agent = gate.LeeAgent(BASE_BANK, th=thresholds(), use_nimble=False)
    agent.reset()
    agent._turn_seen = -1
    inj_c_turn = inj_s_turn = -1
    owned_core = owned_sup = False
    guard = 0
    while not g.is_over() and guard < 100000:
        for p in range(g.num_players):
            if not g.needs_action(p):
                continue
            if p == 0:
                if ((arm == "on" and not (owned_core and owned_sup))
                        or (arm == "core" and not owned_core)):
                    view = json.loads(g.view(0))
                    me = view["me"]
                    turn = view["turn"]
                    owned = {norm_cid(c.get("id")) for c in
                             (me.get("board") or []) + (me.get("hand") or [])}
                    # persistent offer from turn 4: the shop refreshes each
                    # turn, so a one-shot injection vanishes unless bought
                    # immediately. Re-inject until bought — the screening
                    # question is "is this package worth always having on
                    # the menu"; realized value is the adoption gate's job
                    # (no injections there).
                    if not owned_core:
                        if core in owned:
                            owned_core = True
                        elif turn >= 4 and inj_c_turn != turn:
                            g.debug(json.dumps({"cmd": "add_minion", "p": 0,
                                                "zone": "shop", "card": core}))
                            inj_c_turn = turn
                    elif arm == "on" and not owned_sup:
                        if support in owned:
                            owned_sup = True
                        elif inj_s_turn != turn:
                            g.debug(json.dumps({"cmd": "add_minion", "p": 0,
                                                "zone": "shop", "card": support}))
                            inj_s_turn = turn
                g.step(p, agent.choose(g, 0))
            else:
                g.step(p, g.bot_action(p))
        guard += 1
    if not g.is_over():
        return None
    return {"pair": [core, support, tribe], "arm": arm, "seed": seed,
            "place": int(list(g.placements())[0]),
            "assembled": owned_core and (owned_sup or arm == "core")}


def run_stage(pairs, seed0, n, arms=("on", "off")):
    """-> {pair_key: {arm: {seed: place}, "assembled": [seeds]}}"""
    jobs = [(c, s, t, arm, seed0 + i)
            for c, s, t in pairs for arm in arms for i in range(n)]
    with mp.Pool(96) as pool:
        recs = [r for r in pool.imap_unordered(play_pair, jobs, chunksize=8)
                if r is not None]
    out = {}
    for r in recs:
        k = tuple(r["pair"])
        d = out.setdefault(k, {a: {} for a in arms} | {"assembled": []})
        d[r["arm"]][r["seed"]] = r["place"]
        if r["arm"] == "on" and r["assembled"]:
            d["assembled"].append(r["seed"])
    return out


def summarize(res):
    """-> [(pair, stats)] sorted by assembled delta (best first)."""
    rows = []
    for k, d in res.items():
        seeds = sorted(d["assembled"])
        if not seeds:
            rows.append((k, {"n_asm": 0}))
            continue
        deltas = [d["on"][s] - d["off"][s] for s in seeds]
        m = sum(deltas) / len(deltas)
        var = sum((x - m) ** 2 for x in deltas) / max(len(deltas) - 1, 1)
        t = m / (var / len(deltas)) ** 0.5 if var else 0.0
        rows.append((k, {
            "n_asm": len(seeds), "delta_asm": round(m, 3), "t": round(t, 2),
            "better/worse": [sum(1 for x in deltas if x < 0),
                             sum(1 for x in deltas if x > 0)],
            "places_on": [d["on"][s] for s in seeds],
            "places_off": [d["off"][s] for s in seeds]}))
    rows.sort(key=lambda kv: kv[1].get("delta_asm", 99))
    return rows


def shortlist() -> list:
    """Top positive sig synergy edges as (core, support, tribe) pairs."""
    table = json.loads((ROOT / "data" / "synergy_table.json").read_text())
    import taverngym
    pool_ids = {c["id"] for c in json.loads(taverngym.catalog_json())
                if c.get("kind") == "minion" and c.get("in_pool")
                and c.get("implemented") and not c["id"].endswith("_G")}
    seen, cands = set(), []
    for tribe, sups in table.items():
        if tribe == "_meta":
            continue
        for s, edges in sups.items():
            for c, e in edges.items():
                if (e.get("sig") and e["lift"] >= 0.15 and e.get("n1", 0) >= 12
                        and s != c and s in pool_ids and c in pool_ids
                        and frozenset((s, c)) not in seen):
                    seen.add(frozenset((s, c)))
                    cands.append((c, s, tribe, e["lift"]))   # core, support
    cands.sort(key=lambda x: -x[3])
    return [(c, s, t) for c, s, t, _ in cands[:TOPK]]


def stage_screen():
    pairs = shortlist()
    print(f"{len(pairs)} candidate pairs x {N_SCREEN} paired seeds", flush=True)
    res = run_stage(pairs, SCREEN_SEED0, N_SCREEN)
    rows = summarize(res)
    winners = []
    for (core, sup, tribe), st in rows:
        ok = st.get("n_asm", 0) >= 15 and st["delta_asm"] <= -0.25
        if ok:
            winners.append([core, sup, tribe])
        print(f"  {core[:16]}+{sup[:16]} [{tribe[:4]}] asm={st.get('n_asm', 0):2d} "
              f"delta={st.get('delta_asm', float('nan')):+.3f} "
              f"t={st.get('t', float('nan')):+.1f} {'WIN' if ok else ''}",
              flush=True)
    out = {"seed0": SCREEN_SEED0, "n": N_SCREEN, "winners": winners,
           "rows": [{"pair": list(k), **st} for k, st in rows]}
    (ROOT / "runs" / "pair_screen.json").write_text(json.dumps(out, indent=1))
    print(f"{len(winners)} winners -> runs/pair_screen.json", flush=True)


def stage_repro():
    """Three arms on fresh seeds: on / core-only / off. The support's
    marginal value (on vs core-only, paired seeds) is what earns a pair a
    place in fixed_pairs.json — the screen's on-vs-off delta conflates pair
    value with the generic value of an always-available extra shop option."""
    screen = json.loads((ROOT / "runs" / "pair_screen.json").read_text())
    pairs = [tuple(p) for p in screen["winners"]]
    if not pairs:
        print("no screen winners; nothing to repro")
        return
    print(f"repro {len(pairs)} pairs x 3 arms on fresh seeds {REPRO_SEED0}+",
          flush=True)
    res = run_stage(pairs, REPRO_SEED0, N_REPRO, arms=("on", "core", "off"))
    adopted = []
    rows_out = []
    for k, d in res.items():
        core, sup, tribe = k
        seeds = [s for s in d["assembled"]
                 if s in d.get("core", {}) and s in d.get("off", {})]
        if not seeds:
            rows_out.append({"pair": list(k), "n": 0})
            continue
        sup_marg = [d["on"][s] - d["core"][s] for s in seeds]      # support's edge
        total = [d["on"][s] - d["off"][s] for s in seeds]          # package vs vanilla
        m_sup = sum(sup_marg) / len(sup_marg)
        m_tot = sum(total) / len(total)
        var = sum((x - m_sup) ** 2 for x in sup_marg) / max(len(sup_marg) - 1, 1)
        t = m_sup / (var / len(sup_marg)) ** 0.5 if var else 0.0
        ok = len(seeds) >= 20 and m_sup <= -0.15 and m_tot <= -0.10 and t <= -1.5
        if ok:
            adopted.append({"core": core, "support": sup, "tribe": tribe,
                            "gain": round(m_sup, 3), "n": len(seeds)})
        rows_out.append({"pair": list(k), "n": len(seeds),
                         "sup_marginal": round(m_sup, 3),
                         "total": round(m_tot, 3), "t": round(t, 2),
                         "adopt": ok})
        print(f"  {core[:14]}+{sup[:14]} n={len(seeds):2d} "
              f"sup={m_sup:+.3f} total={m_tot:+.3f} t={t:+.1f} "
              f"{'ADOPT' if ok else ''}", flush=True)
    (ROOT / "data" / "fixed_pairs.json").write_text(json.dumps(
        {"pairs": adopted, "screen_seed0": SCREEN_SEED0,
         "repro_seed0": REPRO_SEED0,
         "criterion": "n>=20, support marginal <= -0.15 (t<=-1.5), "
                      "total <= -0.10, fresh repro seeds"}, indent=1))
    (ROOT / "runs" / "pair_repro.json").write_text(json.dumps(rows_out, indent=1))
    print(f"{len(adopted)} pairs -> data/fixed_pairs.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["screen", "repro"], required=True)
    a = ap.parse_args()
    {"screen": stage_screen, "repro": stage_repro}[a.stage]()


if __name__ == "__main__":
    main()
