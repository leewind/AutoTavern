"""Holdout feature-disable ablation: which accepted feature regresses top-4?

    ../.venv/bin/python scripts/feature_ablation.py
"""
import multiprocessing as mp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from leeagent import memory as M                    # noqa: E402
from leeagent.config import ROOT as CFG_ROOT        # noqa: E402

BASE_BANK = M.load(CFG_ROOT / "memories" / "seed.jsonl")


def run(args):
    seed, disable = args
    import leeagent.policy as P
    import leeagent.agent as AG
    from leeagent import gate
    from leeagent.config import thresholds
    th = thresholds()
    orig_score = P.score_actions
    orig_choose = P.choose_pending

    def resort(out):
        out.sort(key=lambda x: (-x[0], x[1]))
        return out

    if "triple" in disable:
        def no_triple(view, matched, legal, n_turn_actions=0, scout=None, buy_hint=None):
            out = []
            for score, i, label, why in orig_score(view, matched, legal,
                                                   n_turn_actions, scout, buy_hint):
                if "triple!" in why:
                    score -= 25.0
                out.append((score, i, label, why))
            return resort(out)
        P.score_actions = no_triple
    if "hero" in disable:
        def plain_hero(legal, view):
            pend = view["me"].get("pending") or {}
            if pend.get("kind") != "hero":
                return orig_choose(legal, view)
            opts = [i for i in legal if P.A_CHOOSE <= i < P.A_PLAY]
            return opts[len(opts) // 2] if opts else sorted(legal)[0]
        P.choose_pending = plain_hero
    if "scout" in disable:
        AG.LeeAgent._scout = lambda self, g, s, f: None

        def no_scout(view, matched, legal, n_turn_actions=0, scout=None, buy_hint=None):
            return orig_score(view, matched, legal, n_turn_actions, None, buy_hint)
        P.score_actions = no_scout
    if "swap" in disable:
        def no_swap(view, matched, legal, n_turn_actions=0, scout=None, buy_hint=None):
            out = []
            for score, i, label, why in orig_score(view, matched, legal,
                                                   n_turn_actions, scout, buy_hint):
                if "slot upgrade" in why:
                    score = -2.0
                out.append((score, i, label, why))
            return resort(out)
        P.score_actions = no_swap
    if "trinket" in disable:
        def plain_trinket(legal, view):
            pend = view["me"].get("pending") or {}
            if pend.get("kind") != "trinket":
                return orig_choose(legal, view)
            opts = [i for i in legal if P.A_CHOOSE <= i < P.A_PLAY]
            return opts[0] if opts else sorted(legal)[0]
        P.choose_pending = plain_trinket
    a = gate.LeeAgent(BASE_BANK, th=th, use_nimble=False)
    return a.run_game(seed, seat=0)["placement"]


if __name__ == "__main__":
    # one fresh pool per config: workers patch module state, and a reused pool
    # would leak the previous config's patches into the next one
    for disable in ([], ["triple"], ["hero"], ["scout"], ["swap"], ["trinket"]):
        tag = "+".join(disable) or "ALL-ON"
        with mp.Pool(48) as pool:
            places = pool.map(run, [(s, disable) for s in range(400, 500)])
        top4 = sum(1 for p in places if p <= 4)
        rewards = [1 - 2 * (p - 1) / 7 for p in places]
        print(f"holdout minus[{tag}]: top4={top4}%  "
              f"mean={sum(rewards) / 100:+.3f}  place={sum(places) / 100:.2f}",
              flush=True)
