"""TavernBench bridge: answer the eval set with LeeAgent + the engine.

No prompt parsing: every play scenario's options are executable
(`perms` / `ops` / `states` / `map` in states.jsonl.gz), exactly how the
labels themselves were computed. Answer protocols:

  preview tasks   B/R2 (combat outcome), P (arrangement), O/T/D3/D5/E3
                  (apply the option, simulate the next combat, pick the best)
  rollout tasks   D1 (hero), D2 (trinket), D4 (discover), N1/N2 (turn plans):
                  apply the option, play the game out with the LeeAgent
                  policy, mean placement over reseeded rollouts
  rule tasks      no state (R1, R3-R7, E1, E2, E4, E5): left unanswered

    ../.venv/bin/python scripts/bench_bridge.py [--sims 512] [--rollouts 12]
"""

from __future__ import annotations

import argparse
import gzip
import json
import multiprocessing as mp
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO / "tavernbench"))

S = defaultdict(dict)   # module-level config set before forking


def _load_all():
    base = REPO / "tavernbench" / "data" / "eval"
    states = {}
    for l in gzip.open(base / "states.jsonl.gz", "rt"):
        r = json.loads(l)
        states[r["id"]] = r
    labels = {d["id"]: d for d in map(json.loads, open(base / "labels.jsonl"))}
    return states, labels


# ---------- phase 1: one (task, option) preview unit ----------

def preview_unit(args):
    rid, k, state_str, kind, payload = args
    from tavernbench import engine as E
    g = E.from_state(state_str)
    opp = E.me(g)["next_opponent"]
    if opp is None:
        return rid, k, None
    n = S["sims_prob"] if kind in ("prob",) else S["sims"]
    if kind == "perm":
        board = E.me(g)["board"]
        cur = list(range(len(board)))
        for t, want in enumerate(payload):
            pos = cur.index(want)
            if pos != t:
                a = E.move_index(pos, t)
                if a not in E.legal(g):
                    return rid, k, None
                g.step(0, a)
                cur.pop(pos)
                cur.insert(t, want)
    elif kind == "ops":
        if not E.apply_ops(g, payload):
            return rid, k, None
    out = E.preview(g, 0, opp, n)
    return rid, k, out["win"] + 0.5 * out["tie"]


def combat_unit(args):
    rid, state_str, q, prompt = args
    from tavernbench import engine as E
    import re
    g = E.from_state(state_str)
    me = E.me(g)
    opp = me["next_opponent"]
    if q == "first":
        # the task's own rules: more minions attack first, random on a tie
        # (the opponent's warband exists only in the prompt text)
        sec = prompt.split("Opponent warband")[-1]
        n_opp = len(re.findall(r"^\s+\d+\. \S", sec.split("\n\n")[0], re.M))
        my = len(me["board"])
        return rid, {"answer": "you" if my > n_opp else
                     ("opponent" if my < n_opp else "random")}
    n = 1024 if q in ("prob", "die") else 512
    if q == "die":
        r = E.dbg(g, cmd="combat_preview", a=0, b=opp, n=n, details=True)
        hp = me["health"] + me.get("armor", 0)
        p = sum(1 for t in r["trials"] if t["damage_taken"] >= hp) / max(len(r["trials"]), 1)
        return rid, {"answer": round(p, 4)}
    out = E.preview(g, 0, opp, n)
    if q == "prob":
        return rid, {"win": round(out["win"], 4), "tie": round(out["tie"], 4),
                     "loss": round(out["loss"], 4)}
    if q == "dmg":
        return rid, {"answer": round(out["dmg_taken"], 3)}
    return rid, {"answer": max(("win", "tie", "loss"), key=lambda k: out[k])}


# ---------- phase 2b: value-model scoring (no rollouts) ----------

def value_unit(args):
    rid, k, state_str, seat, first = args
    from tavernbench import engine as E
    from leeagent.facts import extract_facts
    from scripts.gen_trajectories import feat_row
    import lightgbm as lgb
    global _LGB
    if "_LGB" not in globals():
        _LGB = lgb.Booster(model_file=str(ROOT / "data" / "value_model.txt"))
    g = E.from_state(state_str)
    if first is not None:
        if first not in E.legal(g, seat):
            return rid, k, None
        g.step(seat, first)
    view = E.view(g, seat)
    facts = extract_facts(view)
    if facts["pending"]:
        return rid, k, None
    return rid, k, float(_LGB.predict([feat_row(view, facts, None)])[0])


# ---------- phase 2: one (task, option, rollout) unit ----------

def rollout_unit(args):
    rid, k, state_str, seat, first, salt = args
    from tavernbench import engine as E
    from leeagent import gate
    from leeagent.config import thresholds
    g = E.from_state(state_str)
    g = E.reseeded(g, salt)
    if first is not None:
        if first not in E.legal(g, seat):
            return rid, k, None
        g.step(seat, first)
    agent = gate.LeeAgent(S["store"], th=thresholds(), use_nimble=False)
    agent.reset()
    agent._turn_seen = -1
    guard = 0
    while not g.is_over() and guard < 100000:
        for p in range(g.num_players):
            if g.needs_action(p):
                g.step(p, agent.choose(g, p) if p == seat else g.bot_action(p))
        guard += 1
    if g.is_over():
        return rid, k, int(list(g.placements())[seat])
    return rid, k, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=512)
    ap.add_argument("--sims-prob", type=int, default=1024)
    ap.add_argument("--rollouts", type=int, default=24)
    a = ap.parse_args()

    from leeagent import memory
    S["sims"], S["sims_prob"] = a.sims, a.sims_prob
    S["store"] = memory.load(ROOT / "memories" / "seed.jsonl")

    states, labels = _load_all()
    t0 = time.time()
    answers = {}

    # -- direct combat questions --------------------------------------
    prompts = {d["id"]: d for d in map(json.loads,
                open(REPO / "tavernbench" / "data" / "eval" / "prompts.jsonl"))}
    combat_jobs, choice_jobs = [], []
    for rid, row in states.items():
        sc = rid.split("-")[0]
        st = row.get("state")
        if st is None:                          # D1 keeps per-option `states` instead
            continue
        if sc == "B1":
            combat_jobs.append((rid, st, "first", prompts[rid]["prompt"]))
        elif sc in ("B2", "R2"):
            combat_jobs.append((rid, st, "outcome", None))
        elif sc in ("B3", "B6"):
            combat_jobs.append((rid, st, "prob", None))
        elif sc == "B4":
            combat_jobs.append((rid, st, "dmg", None))
        elif sc == "B5":
            combat_jobs.append((rid, st, "die", None))
        elif sc.startswith("P") and "perms" in row:
            for k, perm in enumerate(row["perms"]):
                choice_jobs.append((rid, k, st, "perm", perm))
        elif "options" in row:      # O*, T*, D3, D5, E3
            for k, opt in enumerate(row["options"]):
                choice_jobs.append((rid, k, st, "ops", opt["ops"]))

    with mp.Pool(96) as pool:
        for rid, ans in pool.imap_unordered(combat_unit, combat_jobs):
            answers[rid] = ans
    print(f"combat tasks: {len(combat_jobs)} done ({time.time()-t0:.0f}s)", flush=True)

    vals = defaultdict(dict)
    with mp.Pool(96) as pool:
        for rid, k, v in pool.imap_unordered(preview_unit, choice_jobs):
            if v is not None:
                vals[rid][k] = v
    for rid, vs in vals.items():
        best = max(vs, key=vs.get)
        row = states[rid]
        if "answers" in row:                       # P*: letters
            answers[rid] = {"answer": row["answers"][best]}
        else:                                      # O/T/D3/D5/E3: the option payload
            answers[rid] = {"answer": row["options"][best]["answer"]}
    print(f"choice tasks: {len(vals)} done ({time.time()-t0:.0f}s)", flush=True)

    # -- rollout tasks --------------------------------------------------
    from tavernbench import engine as E
    # D1 (hero offers): answer straight from the empirical hero table
    hero_table = json.loads((ROOT / "data" / "hero_table.json").read_text()) \
        if (ROOT / "data" / "hero_table.json").is_file() else {}
    for rid, row in states.items():
        if rid.split("-")[0] != "D1" or not hero_table:
            continue
        scored = []
        for k, alt in enumerate(row["states"]):
            me = E.me(E.from_state(alt))
            hid = (me.get("hero") or {}).get("id")
            t = hero_table.get(hid)
            if t:
                scored.append((t["mean_place"], k))
        if scored:
            answers[rid] = {"answer": min(scored)[1]}
    roll_jobs = []
    for rid, row in states.items():
        sc = rid.split("-")[0]
        if sc == "D1":
            if rid in answers:                 # answered from the hero table
                continue
            for k, alt in enumerate(row["states"]):
                for j in range(a.rollouts):
                    roll_jobs.append((rid, k, alt, 0, None, 1000 * k + j))
        elif sc == "D2":
            for k in row["map"]:               # keys are action indices already
                for j in range(a.rollouts):
                    roll_jobs.append((rid, int(k), row["state"], 0,
                                      int(k), 1000 * int(k) + j))
        elif sc == "D4":
            for k in row["map"]:
                for j in range(a.rollouts):
                    roll_jobs.append((rid, int(k), row["state"], row["seat"],
                                      int(k), 1000 * int(k) + j))
        elif sc in ("N1", "N2"):
            for k in row["map"]:
                for j in range(a.rollouts):
                    roll_jobs.append((rid, int(k), row["state"], row["seat"],
                                      int(k), 1000 * int(k) + j))

    # value model available: prescreen N/D2/D4 options, verify the top-2 by
    # rollouts (the model's coarse ranking prunes, rollouts discriminate)
    top2 = {}
    if (ROOT / "data" / "value_model.txt").is_file():
        value_jobs = []
        for rid, row in states.items():
            sc = rid.split("-")[0]
            if sc in ("N1", "N2", "D2", "D4") and rid not in answers:
                for k in row["map"]:
                    value_jobs.append((rid, int(k), row["state"],
                                       row.get("seat", 0), int(k)))
        vvals = defaultdict(dict)
        if value_jobs:
            with mp.Pool(96) as pool:
                for rid, k, v in pool.imap_unordered(value_unit, value_jobs):
                    if v is not None:
                        vvals[rid][k] = v
        for rid, vs in vvals.items():
            if len(vs) == len(states[rid]["map"]):   # complete: keep top-2 only
                top2[rid] = sorted(vs, key=vs.get, reverse=True)[:2]
        print(f"value prescreen: {len(top2)} tasks -> top-2 ({time.time()-t0:.0f}s)",
              flush=True)

    places = defaultdict(list)
    if top2:
        keep = []
        for j in roll_jobs:
            rid = j[0]
            if rid in top2 and j[1] not in top2[rid]:
                continue
            keep.append(j)
        roll_jobs = keep
    with mp.Pool(96) as pool:
        for rid, k, pl in pool.imap_unordered(rollout_unit, roll_jobs):
            if pl is not None:
                places[(rid, k)].append(pl)
    best_by_task = {}
    for (rid, k), pls in places.items():
        best_by_task.setdefault(rid, {})[k] = sum(pls) / len(pls)
    for rid, opts in best_by_task.items():
        best = min(opts, key=opts.get)
        row = states[rid]
        if "answers" in row:                       # D1: index
            answers[rid] = {"answer": best}
        elif "map" in row and rid.split("-")[0] in ("N1", "N2"):
            answers[rid] = {"answer": row["map"][str(best)]}
        else:                                      # D2/D4: option index
            answers[rid] = {"answer": row["map"][str(best)]}
    print(f"rollout tasks: {len(best_by_task)} done ({time.time()-t0:.0f}s)", flush=True)

    # -- write answers ----------------------------------------------------
    out = ROOT / "runs" / "bench_answers.jsonl"
    with out.open("w") as f:
        for rid in sorted(labels):
            ans = answers.get(rid)
            f.write(json.dumps({
                "id": rid, "model": "leeagent",
                "response": json.dumps(ans) if ans is not None else None,
                "latency_s": 0.0, "error": None if ans is not None else "no state",
            }, ensure_ascii=False) + "\n")
    print(f"answers -> {out}  (answered {len(answers)}/{len(labels)}, "
          f"{time.time()-t0:.0f}s total)", flush=True)


if __name__ == "__main__":
    main()
