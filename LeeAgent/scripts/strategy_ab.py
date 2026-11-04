"""Strategy-arbitration A/B on the eval set (2026-11-04): protocol alignment.

The N1/N2/D4 labels are mean placements over 128 playouts of the option in
its cut game (labels.jsonl meta: mean_place / se / reps=128). The frozen
bridge arbitrates with LeeAgent continuation, 24 reps, and salts that differ
per option (salt = 1000*k + j) -- an unpaired comparison whose per-option SE
(~0.35) exceeds typical adjacent-option gaps, dumping near-ties into the
option-index tiebreak.

This A/B re-arbitrates N1/N2 and D4 with the label measurement protocol,
keeping everything else byte-identical to the frozen 0.742 answers:

  arm "lee"  seat plays LeeAgent (current bridge policy), but salts are
             PAIRED across options (salt = task_idx*10000 + j: every option
             faces the same reseeds) and reps = 128, all options, no
             prescreen. Isolates the variance/pairing factor.
  arm "bot"  seat plays bot_action like the label playouts presumably did
             (natural games are bot games). Same paired salts, same reps.
             Isolates the continuation-policy (口径) factor.

Both arms share one salt schedule, so they are paired with each other too.
Bench-side only: leeagent/ untouched (scripts/live_recheck.py proves the
live policy byte-reproduces runs/freeze_bias_fresh.json).

    ../.venv/bin/python scripts/strategy_ab.py [--reps 128] [--arms lee,bot]
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

FROZEN = ROOT / "bench_answers_eval.jsonl"
SCEN = ("N1", "N2", "D4")


def rollout_unit(args):
    rid, k, state_str, seat, first, salt, arm = args
    from tavernbench import engine as E
    from leeagent import gate
    from leeagent.config import thresholds
    g = E.from_state(state_str)
    g = E.reseeded(g, salt)
    if first is not None:
        if first not in E.legal(g, seat):
            return rid, k, arm, None, "illegal-first"
        g.step(seat, first)
    agent = None
    if arm == "lee":
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
    except ValueError as e:
        # rare reseeded futures reach a state where the engine's bot_action
        # proposes an illegal step; drop this rollout and count it (report
        # shows drops per arm -- a high rate would bias the option means)
        return rid, k, arm, None, f"{type(e).__name__}: {e}"
    if g.is_over():
        return rid, k, arm, int(list(g.placements())[seat]), None
    return rid, k, arm, None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=128)
    ap.add_argument("--arms", default="lee,bot")
    a = ap.parse_args()
    arms = a.arms.split(",")

    from leeagent import memory
    S["store"] = memory.load(ROOT / "memories" / "seed.jsonl")

    base = REPO / "tavernbench" / "data" / "eval"
    states = {}
    for l in gzip.open(base / "states.jsonl.gz", "rt"):
        r = json.loads(l)
        if r["id"].split("-")[0] in SCEN:
            states[r["id"]] = r

    # one stable task index -> paired salt schedule shared by all arms
    task_idx = {rid: i for i, rid in enumerate(sorted(states))}

    jobs = []
    for rid, row in states.items():
        base_salt = task_idx[rid] * 10000
        for k in row["map"]:
            for arm in arms:
                for j in range(a.reps):
                    jobs.append((rid, int(k), row["state"], row["seat"],
                                 int(k), base_salt + j, arm))
    print(f"{len(states)} tasks x {len(arms)} arms x {a.reps} reps "
          f"= {len(jobs)} rollouts", flush=True)

    places = defaultdict(list)
    errors = defaultdict(int)
    t0 = time.time()
    with mp.Pool(96) as pool:
        for rid, k, arm, pl, err in pool.imap_unordered(rollout_unit, jobs):
            if err is not None:
                errors[(arm, err.split(':')[0])] += 1
            if pl is not None:
                places[(arm, rid, k)].append(pl)
    print(f"rollouts done ({time.time()-t0:.0f}s); errors: {dict(errors)}",
          flush=True)

    by_arm = defaultdict(dict)
    for (arm, rid, k), pls in places.items():
        by_arm[arm].setdefault(rid, {})[k] = round(sum(pls) / len(pls), 4)

    frozen = {d["id"]: d for d in map(json.loads, open(FROZEN))}
    out_dir = ROOT / "answers_ab"
    out_dir.mkdir(exist_ok=True)
    report = {}
    for arm in arms:
        chosen = {}
        for rid, opts in by_arm[arm].items():
            best = min(opts, key=lambda k: (opts[k], k))
            chosen[rid] = {"answer": states[rid]["map"][str(best)],
                           "means": opts, "n_opts": len(states[rid]["map"])}
        report[arm] = chosen
        # patch groups separately: N-only (strategy category), D4-only
        for group, scen in (("N", ("N1", "N2")), ("D4", ("D4",))):
            patched = dict(frozen)
            n_patch = 0
            for rid, c in chosen.items():
                if rid.split("-")[0] in scen:
                    patched[rid] = {"id": rid, **c}
                    n_patch += 1
            path = out_dir / f"ab_{arm}_{group}.jsonl"
            with open(path, "w") as f:
                for rid in sorted(patched):
                    row = dict(patched[rid])
                    row.pop("means", None)
                    row.pop("n_opts", None)
                    f.write(json.dumps(row) + "\n")
            print(f"{arm}/{group}: patched {n_patch} -> {path.name}", flush=True)

    (ROOT / "runs" / "strategy_ab.json").write_text(json.dumps(
        {arm: {rid: c for rid, c in ch.items()} for arm, ch in report.items()},
        indent=1))
    print("wrote runs/strategy_ab.json", flush=True)


if __name__ == "__main__":
    main()
