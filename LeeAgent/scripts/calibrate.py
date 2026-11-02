"""Nimble judgment calibration: labeled ground truth for the semantic memories.

The seed memories with an empty `when` are judged by Nimble alone, and Phase-0
showed overfiring (M011 "buy the triple" at p=1.0 with no triple in sight).
This script builds the missing measurement:

  1. sample real recruit states from bot games (states, not LeeAgent games:
     the judgment is about state->situation, not about who played it);
  2. label each state with code checkers (the part that IS checkable);
  3. ask Nimble exactly as retrieval.py does;
  4. report per-memory separation and a threshold sweep for min_apply_prob.

    ../.venv/bin/python scripts/calibrate.py --games 12 [--turn-min 3]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import taverngym                                # noqa: E402

from leeagent import memory, nimble             # noqa: E402
from leeagent.facts import render_state         # noqa: E402
from leeagent.config import thresholds          # noqa: E402

# Ground-truth checkers: situation -> True/False from the view alone.
# Approximations are marked; a checker that cannot decide returns None.


def _chk_triple(view) -> bool | None:
    me = view["me"]
    hand = me.get("hand") or []
    shop_ids = {c.get("id") for c in me.get("shop") or []}
    counts = Counter(c.get("id") for c in hand if c.get("id"))
    return any(n >= 2 and cid in shop_ids for cid, n in counts.items())


def _chk_dr_summon(view) -> bool | None:
    for m in view["me"].get("board") or []:
        t = (m.get("text") or "") + (m.get("text_zh") or "")
        if "Deathrattle" in t and "ummon" in t:
            return True
    return False


def _chk_avenge(view) -> bool | None:
    for m in view["me"].get("board") or []:
        if "Avenge" in (m.get("text") or ""):
            return True
    return False


def _chk_win_streak(view) -> bool | None:  # approximation: ignores board size
    ws = view["me"].get("win_streak") or 0
    return ws >= 2 and (view["me"].get("board") and len(view["me"]["board"]) < 6)


def _chk_opp_bigger(view) -> bool | None:
    nxt = view["me"].get("next_opponent")
    if nxt is None:
        return None
    opps = view.get("opponents") or []
    entry = next((o for o in opps if o.get("id") == nxt), None)
    if not entry or not entry.get("seen_board"):
        return None
    return len(entry["seen_board"]) > len(view["me"].get("board") or [])


CHECKERS = {"M011": _chk_triple, "M007": _chk_dr_summon, "M023": _chk_avenge,
            "M019": _chk_win_streak, "M012": _chk_opp_bigger}


def sample_states(seeds, turn_min=3):
    """One (turn, view) per recruit turn of seat 0 from all-bot games."""
    states = []
    for seed in seeds:
        g = taverngym.Game(seed=seed)
        last = -1
        while not g.is_over():
            for seat in range(g.num_players):
                if not g.needs_action(seat):
                    continue
                if seat == 0:
                    view = json.loads(g.view(0))
                    if (view["turn"] != last and view["turn"] >= turn_min
                            and not view["me"].get("pending")):
                        states.append(view)
                        last = view["turn"]
                g.step(seat, g.bot_action(seat))
        # keep games light: ~14 states each
    return states


def probe(state_views, mem_ids, th):
    """Ask Nimble the same applicability questions retrieval.py asks."""
    store = {m["id"]: m for m in memory.load(ROOT / "memories" / "seed.jsonl")}
    cands = [store[mid] for mid in mem_ids]
    rows = []
    for i, view in enumerate(state_views):
        labels = {mid: CHECKERS[mid](view) for mid in mem_ids}
        if all(v is None for v in labels.values()):
            continue
        state = {"game": render_state(view),
                 "candidates": [memory.slim(m) for m in cands]}
        qs = {f"app_{m['id']}": {
            "type": "noul",
            "instructions": (f"Memory candidate {m['id']} is at `candidates[{k}]`. "
                             f"Is its situation present in `game` right now?"),
            "criteria": {"true": "applies to the current game state",
                         "false": "does not apply now"}} for k, m in enumerate(cands)}
        try:
            out = nimble.ask_batch(state, qs)
        except Exception as e:  # keep going; record the failure
            rows.append({"state": i, "error": repr(e)})
            continue
        for mid in mem_ids:
            if labels[mid] is None:
                continue
            a = out["answers"].get(f"app_{mid}")
            if a:
                rows.append({"state": i, "mem": mid, "label": bool(labels[mid]),
                             "prob": round(float(a["noul"]), 4)})
    return rows


def summarize(rows):
    by_mem = {}
    for r in rows:
        if "label" not in r:
            continue
        by_mem.setdefault(r["mem"], []).append(r)
    THRESHOLDS = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    per_mem = {}
    for mid, rs in sorted(by_mem.items()):
        pos = [r["prob"] for r in rs if r["label"]]
        neg = [r["prob"] for r in rs if not r["label"]]
        acc = {}
        for t in THRESHOLDS:
            tp = sum(1 for p in pos if p >= t)
            fn = len(pos) - tp
            fp = sum(1 for p in neg if p >= t)
            tn = len(neg) - fp
            acc[t] = {"acc": round((tp + tn) / max(len(rs), 1), 3),
                      "precision": round(tp / max(tp + fp, 1), 3),
                      "recall": round(tp / max(tp + fn, 1), 3),
                      "fp": fp, "fn": fn}
        per_mem[mid] = {"n": len(rs), "pos": len(pos), "neg": len(neg),
                        "mean_prob|true": round(sum(pos) / max(len(pos), 1), 3),
                        "mean_prob|false": round(sum(neg) / max(len(neg), 1), 3),
                        "thresholds": acc}
    all_rows = [r for rs in by_mem.values() for r in rs if "label" in r]
    sweep = {}
    for t in THRESHOLDS:
        tp = sum(1 for r in all_rows if r["label"] and r["prob"] >= t)
        fp = sum(1 for r in all_rows if not r["label"] and r["prob"] >= t)
        fn = sum(1 for r in all_rows if r["label"] and r["prob"] < t)
        tn = sum(1 for r in all_rows if not r["label"] and r["prob"] < t)
        sweep[t] = {"acc": round((tp + tn) / max(len(all_rows), 1), 3),
                    "precision": round(tp / max(tp + fp, 1), 3),
                    "recall": round(tp / max(tp + fn, 1), 3)}
    best_t = max(sweep, key=lambda t: sweep[t]["acc"])
    return {"n_judgments": len(all_rows), "best_threshold": best_t,
            "sweep": sweep, "per_memory": per_mem}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=12)
    ap.add_argument("--seed0", type=int, default=900)
    ap.add_argument("--turn-min", type=int, default=3)
    ap.add_argument("--out", default=str(ROOT / "runs" / "calibration.json"))
    a = ap.parse_args()
    if not nimble.health():
        sys.exit("nimble service down")
    th = thresholds()
    states = sample_states(range(a.seed0, a.seed0 + a.games), a.turn_min)
    print(f"{len(states)} states sampled", flush=True)
    rows = probe(states, list(CHECKERS), th)
    (ROOT / "runs").mkdir(exist_ok=True)
    Path(ROOT / "runs" / "calibration_rows.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    summary = summarize(rows)
    Path(a.out).write_text(json.dumps(summary, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k != "per_memory"}, indent=1))
    for mid, s in summary["per_memory"].items():
        print(f"  {mid}: n={s['n']} pos={s['pos']} E[p|T]={s['mean_prob|true']} "
              f"E[p|F]={s['mean_prob|false']} best_t="
              f"{max(s['thresholds'], key=lambda t: s['thresholds'][t]['acc'])}")


if __name__ == "__main__":
    main()
