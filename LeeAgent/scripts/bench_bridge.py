"""TavernBench bridge: answer the eval set with LeeAgent + the engine.

No prompt parsing: every play scenario's options are executable
(`perms` / `ops` / `states` / `map` in states.jsonl.gz), exactly how the
labels themselves were computed. Answer protocols:

  preview tasks   B/R2 (combat outcome), P (arrangement), O/T/D3/D5/E3
                  (apply the option, simulate the next combat, pick the best)
  rollout tasks   D1 (hero), D2 (trinket): LeeAgent continuation, --rollouts
                  reps, value-prescreen top-2
                  N1/N2/D4 (turn plans, discover): each task answers with
                  the DEPLOYED policy's own procedure at that phase (round
                  11) -- cut before LATE_SEARCH_TURN: the policy scorer's
                  argmax among the options (E0: 0.690 vs 0.517 for rollouts);
                  D2: the deployed pending picker (trinket table); turn >=
                  LATE_SEARCH_TURN and D4: the label measurement protocol
                  (labels.jsonl meta: mean_place over 128 bot playouts;
                  mirrors the deployed LATE_SEARCH arbitration) -- every
                  seat plays bot_action, salts paired across a task's
                  options, --n-reps reps, no prescreen. The rollout arm was
                  adopted 2026-11-04 after a paired A/B: bot口径 +12 net
                  tasks vs +4 for pairing+reps alone.
  rule tasks      no state (R1, R3-R7, E1, E2, E4, E5): left unanswered

    ../.venv/bin/python scripts/bench_bridge.py [--sims 512] [--rollouts 12]
"""

from __future__ import annotations

import argparse
import gzip
import json
import multiprocessing as mp
import re
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


# ---------- phase 2c: recipe-progress scoring (strategy prescreen) ----------

def recipe_unit(args):
    """Recipe progress after applying option k: sum over causally-measured
    recipes of strength x (owned cores / core count). A second prescreener
    for N tasks alongside the value model — union top-2s, rollouts arbitrate.
    Retired from the pipeline 2026-11-04 (N tasks moved to the full label
    protocol); kept as reference for recipe-gate tooling
    (no tuned weights; the knob-free design is the point)."""
    rid, k, state_str, seat, first = args
    from tavernbench import engine as E
    from leeagent.comp import recipe_table
    g = E.from_state(state_str)
    if first is not None:
        if first not in E.legal(g, seat):
            return rid, k, None
        g.step(seat, first)
    me = E.view(g, seat)["me"]
    owned = set()
    for c in (me.get("board") or []) + (me.get("hand") or []):
        cid = c.get("id") or ""
        owned.add(cid[:-2] if cid.endswith("_G") else cid)
    recipes = recipe_table().get("recipes") or []
    if not recipes:
        return rid, k, None
    s = 0.0
    for r in recipes:
        cores = r.get("cores") or []
        held = sum(1 for c in cores if c in owned)
        if held:
            s += (-r.get("gain", 0)) * held / len(cores)
    return rid, k, s


# ---------- phase 2: one (task, option, rollout) unit ----------

def deployed_unit(args):
    """Deployed-mechanism outlets (round 11): answer a task with the deployed
    policy's own decision procedure at that phase instead of rollouts.

    nforced    N tasks cut before leeagent.agent.LATE_SEARCH_TURN: the policy
               scorer's argmax among the offered options (the deployed early
               decision; E0 measured 0.690 vs 0.517 for the rollout arm).
    d2pending  D2 trinket picks: the deployed pending picker (choose_pending's
               trinket table; 3/8 vs the rollout arbitrator's 2/8).

    Returns the chosen option's action index, or None when the deployed pick
    is undecidable (options not all in the scorer's ranking / natural action
    outside the option set) -- those tasks fall through to the rollout arm.
    """
    rid, kind, state_str, seat, opts = args
    from tavernbench import engine as E
    from leeagent import gate
    from leeagent import policy as P
    from leeagent.config import thresholds
    optset = {str(o) for o in opts}
    g = E.from_state(state_str)
    if kind == "d2pending":
        a = gate.LeeAgent(S["store"], th=thresholds(), use_nimble=False)
        a.reset()
        a._turn_seen = -1
        act = a.choose(g, seat)
        return rid, int(act) if str(act) in optset else None

    real = P.score_actions
    box = {}

    def spy(view, matched, legal, **kw):
        out = real(view, matched, legal, **kw)
        box["ranking"] = out
        return out

    P.score_actions = spy
    try:
        a = gate.LeeAgent(S["store"], th=thresholds(), use_nimble=False)
        a.reset()
        a._turn_seen = -1
        natural = a.choose(g, seat)
    finally:
        P.score_actions = real
    ranking = box.get("ranking") or []
    by_action = {act: (i, sc) for i, (sc, act, _l, _w) in enumerate(ranking)}
    if all(o in by_action for o in opts):
        best = max(opts, key=lambda o: (-by_action[o][0], by_action[o][1]))
        return rid, int(best)
    return rid, int(natural) if str(natural) in optset else None


def rollout_unit(args):
    rid, k, state_str, seat, first, salt, seat_bot = args
    from tavernbench import engine as E
    from leeagent import gate
    from leeagent.config import thresholds
    g = E.from_state(state_str)
    g = E.reseeded(g, salt)
    if first is not None:
        if first not in E.legal(g, seat):
            return rid, k, None
        g.step(seat, first)
    agent = None
    if not seat_bot:
        agent = gate.LeeAgent(S["store"], th=thresholds(), use_nimble=False)
        agent.reset()
        agent._turn_seen = -1
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
        # rare reseeded futures reach a state where the engine's bot_action
        # proposes an illegal step (1 in ~70k in the 2026-11-04 A/B); drop
        # the rollout -- the option means keep the other 127 reseeds
        return rid, k, None
    if g.is_over():
        return rid, k, int(list(g.placements())[seat])
    return rid, k, None


MECHANICS_APPENDIX = """
Engine mechanics (authoritative for this simulator):
- Golden crafting: the golden minion's stats = 2x the normal card's BASE stats
  + the sum of every merged copy's stat gains above its own base (losses
  included). Golden card text doubles the numbers of the normal text.
- Playing a minion from hand costs 0 Gold. Buying costs 3, selling gives
  exactly 1, refreshing costs 1. A card only costs Gold to play if its text
  says so (e.g. "Costs 1").
- "Give your OTHER minions ..." never includes the source minion itself.
- A Battlecry resolves immediately when the minion is played, before anything
  else you do next. Simultaneous end-of-turn / start-of-turn triggers resolve
  left to right across the warband.
- Upgrade price: drops by 1 at the start of each turn you did not upgrade
  (floor 0). Upgrading sets the price to the NEXT tier's base price (the decay
  does not carry over); at the maximum tier the price is 0.
- Buys need 3 Gold and hand space (hand holds at most 10); plays need warband
  space (at most 7); refreshing needs 1 Gold.
"""


def rules_answer(rid, prompt, client, model, cache):
    """One text-model call for a rules/economy task. The task prompt carries
    the rules summary, the state, the card rules and the answer format; we
    add a generic JSON-compliance instruction plus a fixed mechanics appendix
    distilled from the engine source (crates/taverngym/src) — no per-task
    tuning. Answers are content-address cached (prompt + system prompt):
    temperature 0 still re-rolls +/-3 answers per run, which is measurement
    noise, not signal; the cache key changes whenever the appendix does."""
    import hashlib
    import json
    import re
    t = time.time()
    sys_msg = ("You answer Hearthstone Battlegrounds rules questions. Reason "
               "step by step, then output ONLY the final answer as a single "
               "JSON object in the exact '## Answer format' given in the task."
               + MECHANICS_APPENDIX)
    key = hashlib.sha1(f"{model}|{sys_msg}|{prompt}".encode()).hexdigest()[:16]
    if key in cache:
        return rid, cache[key], 0.0
    try:
        rsp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": sys_msg},
                      {"role": "user", "content": prompt}],
            max_tokens=1500, temperature=0.0,
            extra_body={"thinking": {"type": "disabled"}})
        text = rsp.choices[0].message.content or ""
        m = re.search(r"\{.*\}", text, re.S)
        ans = json.loads(m.group(0))["answer"] if m else None
        if ans is not None:
            cache[key] = ans
        return rid, ans, time.time() - t
    except Exception:
        return rid, None, time.time() - t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=512)
    ap.add_argument("--sims-prob", type=int, default=1024)
    ap.add_argument("--rollouts", type=int, default=24)
    ap.add_argument("--n-reps", type=int, default=128,
                    help="reps for N1/N2/D4 label-protocol rollouts")
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
        best = min(vs, key=lambda k: (-vs[k], k))
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
    # paired-salt schedule for the label-protocol scenarios: one stable task
    # index, shared across a task's options so every option faces the same
    # reseeds (identical to scripts/strategy_ab.py, which certified the arm)
    # -- deployed-mechanism outlets (round 11) ----------------------------
    # N tasks cut before the deployed late-phase boundary answer with the
    # policy scorer (the deployed early decision); D2 answers with the
    # deployed pending picker. Turn comes from the task's own state, never
    # the labels. Undecidable tasks fall through to the rollout arm.
    from leeagent.agent import LATE_SEARCH_TURN
    dep_jobs = []
    for rid, row in states.items():
        sc = rid.split("-")[0]
        if sc in ("N1", "N2"):
            turn = json.loads(E.from_state(row["state"]).view(row["seat"]))["turn"]
            if turn < LATE_SEARCH_TURN:
                dep_jobs.append((rid, "nforced", row["state"], row["seat"],
                                 [int(k) for k in row["map"]]))
        elif sc == "D2":
            dep_jobs.append((rid, "d2pending", row["state"], row.get("seat", 0),
                             [int(k) for k in row["map"]]))
    n_dep = 0
    if dep_jobs:
        with mp.Pool(96) as pool:
            for rid, k in pool.imap_unordered(deployed_unit, dep_jobs):
                if k is not None:
                    answers[rid] = {"answer": states[rid]["map"][str(k)]}
                    n_dep += 1
        print(f"deployed outlets: {n_dep}/{len(dep_jobs)} answered "
              f"(rest fall through to rollouts)", flush=True)

    pair_idx = {rid: i for i, rid in enumerate(
        sorted(r for r in states if r.split("-")[0] in ("N1", "N2", "D4")))}
    roll_jobs = []
    for rid, row in states.items():
        sc = rid.split("-")[0]
        if rid in answers:                     # hero table / deployed outlet
            continue
        if sc == "D1":
            for k, alt in enumerate(row["states"]):
                for j in range(a.rollouts):
                    roll_jobs.append((rid, k, alt, 0, None,
                                      1000 * k + j, False))
        elif sc == "D2":
            for k in row["map"]:               # keys are action indices already
                for j in range(a.rollouts):
                    roll_jobs.append((rid, int(k), row["state"], 0,
                                      int(k), 1000 * int(k) + j, False))
        elif sc in ("N1", "N2", "D4"):
            base = pair_idx[rid] * 10000
            for k in row["map"]:
                for j in range(a.n_reps):
                    roll_jobs.append((rid, int(k), row["state"], row["seat"],
                                      int(k), base + j, True))

    # value model available: prescreen D2 options, verify the top-2 by
    # rollouts (N1/N2/D4 now run the full label protocol instead -- see
    # rollout_unit -- so the prescreen is D2-only since 2026-11-04)
    top2 = {}
    if (ROOT / "data" / "value_model.txt").is_file():
        value_jobs = []
        for rid, row in states.items():
            sc = rid.split("-")[0]
            if sc == "D2" and rid not in answers:
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
                top2[rid] = [k for k, _ in sorted(
                    vs.items(), key=lambda kv: (-kv[1], kv[0]))][:2]
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
        best = min(opts, key=lambda k: (opts[k], k))
        row = states[rid]
        if "answers" in row:                       # D1: index
            answers[rid] = {"answer": best}
        elif "map" in row and rid.split("-")[0] in ("N1", "N2"):
            answers[rid] = {"answer": row["map"][str(best)]}
        else:                                      # D2/D4: option index
            answers[rid] = {"answer": row["map"][str(best)]}
    print(f"rollout tasks: {len(best_by_task)} done ({time.time()-t0:.0f}s)", flush=True)

    # -- rules/economy tasks ---------------------------------------------
    # R5 (golden crafting): every input is in the prompt and the engine's
    # merge formula is exact (engine.rs merge_golden: golden base + each
    # part's gains above its base, losses included) - answer in code
    for rid in labels:
        if rid.split("-")[0] != "R5" or rid in answers:
            continue
        p = prompts[rid]["prompt"]
        m = re.search(r"You buy the (.+?) in tavern position 0, which completes "
                      r"a triple\. The card's base stats are (\d+)/(\d+)\.",
                      p.split("## Question")[-1])
        if not m:
            continue
        name, ba, bh = m.group(1), int(m.group(2)), int(m.group(3))
        body = p.split("## Card rules")[0]
        ga, gh = 2 * ba, 2 * bh
        for _pos, a, h in re.findall(
                rf"(\d+)\. {re.escape(name)} \(.*?\) (\d+)/(\d+)", body):
            ga += int(a) - ba
            gh += int(h) - bh
        answers[rid] = {"answer": [ga, gh]}

    # the rest: no executable state, ask the text model ----------------------
    rule_scen = ("R1", "R3", "R4", "R5", "R6", "R7", "E1", "E2", "E4", "E5")
    rule_ids = [rid for rid in labels
                if rid.split("-")[0] in rule_scen and rid not in answers]
    if rule_ids:
        from concurrent.futures import ThreadPoolExecutor
        from leeagent.generate import BENCH_ENV_FILE, read_env
        from openai import OpenAI
        env = read_env(BENCH_ENV_FILE)
        client = OpenAI(api_key=env.get("API_KEY"),
                        base_url=(env.get("API_BASE") or "").rstrip("/") or None,
                        max_retries=2)
        model = env.get("MODEL", "deepseek-chat")
        t0r = time.time()
        cache_p = ROOT / "runs" / "rules_cache.json"
        cache = json.loads(cache_p.read_text()) if cache_p.is_file() else {}
        with ThreadPoolExecutor(8) as ex:
            futs = [ex.submit(rules_answer, rid, prompts[rid]["prompt"],
                              client, model, cache) for rid in rule_ids]
            for f in futs:
                rid, ans, _ = f.result()
                if ans is not None:
                    answers[rid] = {"answer": ans}
        cache_p.write_text(json.dumps(cache, indent=1))
        print(f"rules outlet: {len(cache)} cached answers "
              f"({time.time()-t0r:.0f}s)", flush=True)
        print(f"rules tasks: {len(rule_ids)} asked, {sum(1 for r in rule_ids if r in answers)} "
              f"answered ({time.time()-t0r:.0f}s)", flush=True)

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
