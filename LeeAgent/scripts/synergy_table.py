"""Empirical card-synergy table: lift of buying S while C is on board.

Per committed direction D and bought card S, each board card C gets
    lift = E[res | S bought, C on board] - E[res | S bought, C absent]
where res is the final-placement reward residualised within the (D, S)
group on [turn, health, board quality]. The covariates absorb the raw
log's dominant confound — "junk still on board at buy time" means a
stuck game and a bad final place, which naively made every edge negative.
Conditioning on (D, S) in both arms cancels S's own strength and the
direction baseline; what remains is still observational — the paired gate
arbitrates adoption.

Edges need n1 >= 10 present-events and n0 >= 10 absent-events; `sig` marks
|lift| >= SIG_SE standard errors (consumption uses sig edges only).

    ../.venv/bin/python scripts/synergy_table.py [--n1 10] [--sig-se 1.5]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TRIBES = ("BEAST", "DRAGON", "MECH", "MURLOC", "UNDEAD",
          "DEMON", "ELEMENTAL", "PIRATE", "QUILBOAR")


def build(n1_min: int, sig_se: float) -> tuple[dict, dict]:
    import numpy as np

    events = {}          # (comp, S) -> [(board set, turn, health, boardq, reward)]
    n_games = 0
    all_r = []
    with (ROOT / "data" / "synergy_games.jsonl").open() as f:
        for line in f:
            g = json.loads(line)
            n_games += 1
            all_r.append(g["reward"])
            for s, board, comp, turn, health, boardq in g["buys"]:
                if not s or comp not in TRIBES:
                    continue
                events.setdefault((comp, s), []).append(
                    ({c for c in board if c}, turn, health, boardq, g["reward"]))

    table = {t: {} for t in TRIBES}
    for (comp, s), evs in events.items():
        if len(evs) < n1_min:
            continue
        # centre the covariates so the intercept is the group mean and the
        # design is well-conditioned even when e.g. every buy came turn 5
        mt = sum(t for _, t, _, _, _ in evs) / len(evs)
        mh = sum(h for _, _, h, _, _ in evs) / len(evs)
        mq = sum(q for _, _, _, q, _ in evs) / len(evs)
        X = np.array([[1.0, t - mt, h - mh, q - mq]
                      for _, t, h, q, _ in evs])
        y = np.array([r for _, _, _, _, r in evs])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        res = y - X @ beta
        boards = [b for b, *_ in evs]
        r1_by_c = {}
        for b, r in zip(boards, res):
            for c in b:
                r1_by_c.setdefault(c, []).append(float(r))
        edges = {}
        for c, r1 in r1_by_c.items():
            if len(r1) < n1_min:
                continue
            r0 = [float(r) for b, r in zip(boards, res) if c not in b]
            if len(r0) < n1_min:
                continue
            m1, m0 = sum(r1) / len(r1), sum(r0) / len(r0)
            lift = m1 - m0
            v1 = sum((x - m1) ** 2 for x in r1) / max(len(r1) - 1, 1)
            v0 = sum((x - m0) ** 2 for x in r0) / max(len(r0) - 1, 1)
            se = math.sqrt(v1 / len(r1) + v0 / len(r0)) or 1e-9
            edges[c] = {"lift": round(lift, 4), "n1": len(r1),
                        "sig": abs(lift) >= sig_se * se}
        if edges:
            table[comp][s] = {c: e for c, e in sorted(
                edges.items(), key=lambda kv: -abs(kv[1]["lift"]))}
    table["_meta"] = {"games": n_games, "n1_min": n1_min, "sig_se": sig_se,
                      "estimator": "lift on reward ~ [turn, health, boardq] "
                                   "residuals within (comp, S)",
                      "mean_reward": round(sum(all_r) / len(all_r), 4)
                      if all_r else 0.0}
    return table, events


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n1", type=int, default=10)
    ap.add_argument("--sig-se", type=float, default=1.5)
    a = ap.parse_args()
    table, _ = build(a.n1, a.sig_se)

    out = ROOT / "data" / "synergy_table.json"
    out.write_text(json.dumps(table, indent=1))
    n_pairs = sum(len(es) for t, v in table.items() if t != "_meta"
                  for s, es in v.items())
    n_sig = sum(1 for t, v in table.items() if t != "_meta"
                for s, es in v.items() for e in es.values() if e["sig"])
    print(f"{table['_meta']['games']} games, {n_pairs} (S -> C) edges, "
          f"{n_sig} sig -> {out}")

    import taverngym
    names = {c["id"]: c.get("name") or c["id"]
             for c in json.loads(taverngym.catalog_json())}
    for t in TRIBES:
        sig_edges = [(s, c, e["lift"]) for s, es in table[t].items()
                     for c, e in es.items() if e["sig"]]
        pos = sorted((x for x in sig_edges if x[2] > 0), key=lambda x: -x[2])
        neg = sorted((x for x in sig_edges if x[2] < 0), key=lambda x: x[2])
        fmt = lambda xs: [(names.get(s, s)[:14], names.get(c, c)[:14], l)
                          for s, c, l in xs[:3]]
        print(f"  {t}: pos {fmt(pos)}  neg {fmt(neg)}")


if __name__ == "__main__":
    main()
