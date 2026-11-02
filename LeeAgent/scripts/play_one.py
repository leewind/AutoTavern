"""Play one full game: LeeAgent in seat 0, scripted bots elsewhere.

    ../.venv/bin/python scripts/play_one.py --seed 1 [--no-nimble] [--distill]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from leeagent import memory                      # noqa: E402
from leeagent.agent import LeeAgent              # noqa: E402
from leeagent.config import thresholds           # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seat", type=int, default=0)
    ap.add_argument("--memories", default=str(ROOT / "memories" / "seed.jsonl"))
    ap.add_argument("--no-nimble", action="store_true", help="code-only prefilter (baseline)")
    ap.add_argument("--distill", action="store_true", help="cold path: generate candidates after")
    a = ap.parse_args()

    store = memory.load(a.memories)
    agent = LeeAgent(store, th=thresholds(), use_nimble=not a.no_nimble)
    t0 = time.time()
    result = agent.run_game(a.seed, seat=a.seat)
    wall = time.time() - t0

    print(f"\nseed={a.seed} seat={a.seat}  ->  placement {result['placement']}/8  "
          f"(reward {result['reward']:+.2f})  {wall:.1f}s")
    s = result["stats"]
    mode = "nimble" if agent.use_nimble else "code-only"
    print(f"mode={mode}  turns={s['turns']}  actions={s['actions']}  "
          f"nimble={s['nimble_ms'] / 1000:.1f}s/{s['nimble_tokens']}tok  "
          f"positionings={s['positionings']}")
    print("\n回合  金币 血量  部族              命中记忆")
    board_tribes = ""
    for t in result["turns"]:
        if t["matched"] or t["turn"] % 2 == 0:
            hit = " ".join(f"{mid}({p})" for mid, p in t["matched"]) or "-"
            print(f"  {t['turn']:>3}  {t['gold']:>3} {t['health']:>3}  {hit}")

    out = ROOT / "runs" / f"game_seed{a.seed}{'_nonimble' if a.no_nimble else ''}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1))
    print(f"\nlog -> {out}")

    if a.distill:
        from leeagent.generate import distill
        cands = distill(result, store)
        print(f"\n冷路径蒸馏出 {len(cands)} 条候选:")
        for c in cands:
            print(f"  {c['id']} [{c['kind']}] {c['situation']}")
        if cands:
            cpath = ROOT / "memories" / "candidates.jsonl"
            with cpath.open("a") as f:
                for c in cands:
                    f.write(json.dumps(c, ensure_ascii=False) + "\n")
            print(f"appended -> {cpath}(跑 scripts/run_gate.py 过门)")


if __name__ == "__main__":
    main()
