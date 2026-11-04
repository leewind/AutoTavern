"""Pure value-model ranking of bench N1/N2/D4 options (distillation probe).

For every task option: apply the option, build the gen_trajectories feature
row (same one the bridge's value_unit uses), predict final reward, pick the
argmax. No rollouts anywhere -- this measures the model alone, the metric
that decides whether search-strength play is distillable into the GBDT.
Scores via tavernbench.score.score_answer (official logic).

    ../.venv/bin/python scripts/value_model_eval.py data/value_model_oldpolicy.txt
    ../.venv/bin/python scripts/value_model_eval.py data/value_model_v4.txt
"""

from __future__ import annotations

import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO / "tavernbench"))

from tavernbench.score import score_answer          # noqa: E402


def main():
    model_path = Path(sys.argv[1]) if len(sys.argv) > 1 \
        else ROOT / "data" / "value_model.txt"
    import lightgbm as lgb
    from tavernbench import engine as E
    from leeagent.facts import extract_facts
    from scripts.gen_trajectories import feat_row
    model = lgb.Booster(model_file=str(model_path))

    base = REPO / "tavernbench" / "data" / "eval"
    states = {}
    for l in gzip.open(base / "states.jsonl.gz", "rt"):
        r = json.loads(l)
        if r["id"].split("-")[0] in ("N1", "N2", "D4"):
            states[r["id"]] = r
    labels = {d["id"]: d for d in map(json.loads, open(base / "labels.jsonl"))}

    summ = defaultdict(lambda: {"n": 0, "ok": 0, "undecidable": 0})
    picks = {}
    for rid in sorted(states):
        row = states[rid]
        scen = rid.split("-")[0]
        seat = row.get("seat", 0)
        preds = {}
        for k in row["map"]:
            g = E.from_state(row["state"])
            kk = int(k)
            if kk not in E.legal(g, seat):
                continue
            g.step(seat, kk)
            view = E.view(g, seat)
            facts = extract_facts(view)
            if facts["pending"]:
                continue
            preds[kk] = float(model.predict([feat_row(view, facts, None)])[0])
        s = summ[scen]
        s["n"] += 1
        if len(preds) < 2:
            s["undecidable"] += 1
            continue
        best = max(preds, key=lambda kk: (preds[kk], -kk))
        picks[rid] = int(best)
        ok, _sc = score_answer(labels[rid], {"response": json.dumps(
            {"answer": row["map"][str(best)]})})
        s["ok"] += bool(ok)

    out = {"model": str(model_path), "summary": {}, "picks": picks}
    print(f"model: {model_path.name}")
    for scen, s in sorted(summ.items()):
        out["summary"][scen] = {k: s[k] for k in ("n", "ok", "undecidable")}
        acc = s["ok"] / s["n"] if s["n"] else 0
        print(f"  {scen}: {s['ok']}/{s['n']} = {acc:.3f}"
              f"  (undecidable {s['undecidable']})")
    name = model_path.stem
    (ROOT / "runs" / f"value_eval_{name}.json").write_text(json.dumps(out, indent=1))
    print(f"wrote runs/value_eval_{name}.json")


if __name__ == "__main__":
    main()
