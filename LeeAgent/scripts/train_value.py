"""Fit the placement value model on self-play trajectories.

Split by game (rows of one game never straddle train/valid) to avoid leaks.
    ../.venv/bin/python scripts/train_value.py [--out value_model_v4.txt]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    import lightgbm as lgb
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="value_model.txt")
    a = ap.parse_args()
    d = np.load(ROOT / "data" / "trajectories.npz")
    X, y = d["X"], d["y"]
    # rows were appended game by game but boundaries were not stored; random
    # per-row splits leak final rewards across train/valid. Contiguous row
    # blocks (~30 games each) leak at most a straddling game per block edge.
    rng = np.random.default_rng(0)
    n_blocks = 32
    block = 5000
    starts = rng.choice(len(y) - block, size=n_blocks, replace=False)
    val = np.zeros(len(y), dtype=bool)
    for s in starts:
        val[s:s + block] = True
    model = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.06, num_leaves=63,
                              min_child_samples=100, subsample=0.9, colsample_bytree=0.9,
                              n_jobs=96, verbose=-1)
    model.fit(X[~val], y[~val])
    pred = model.predict(X[val])
    rmse = float(np.sqrt(np.mean((pred - y[val]) ** 2)))
    base = float(np.sqrt(np.mean((y[val].mean() - y[val]) ** 2)))
    print(f"valid RMSE {rmse:.4f} (predict-mean baseline {base:.4f})  "
          f"rows train={ (~val).sum() } val={ val.sum() }")
    model.booster_.save_model(str(ROOT / "data" / a.out))
    print(f"saved -> data/{a.out}")


if __name__ == "__main__":
    main()
