"""Fit the placement value model on self-play trajectories.

Split by game (rows of one game never straddle train/valid) to avoid leaks.
    ../.venv/bin/python scripts/train_value.py
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    import lightgbm as lgb
    d = np.load(ROOT / "data" / "trajectories.npz")
    X, y = d["X"], d["y"]
    n_games = 5000
    rows_per_game = len(y) // n_games + 1
    # rows were appended game by game; split index at game boundaries
    game_of_row = np.arange(len(y)) // rows_per_game
    rng = np.random.default_rng(0)
    val_games = rng.choice(n_games, size=500, replace=False)
    val = np.isin(game_of_row, val_games)
    model = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.06, num_leaves=63,
                              min_child_samples=100, subsample=0.9, colsample_bytree=0.9,
                              n_jobs=96, verbose=-1)
    model.fit(X[~val], y[~val])
    pred = model.predict(X[val])
    rmse = float(np.sqrt(np.mean((pred - y[val]) ** 2)))
    base = float(np.sqrt(np.mean((y[val].mean() - y[val]) ** 2)))
    print(f"valid RMSE {rmse:.4f} (predict-mean baseline {base:.4f})  "
          f"rows train={ (~val).sum() } val={ val.sum() }")
    model.booster_.save_model(str(ROOT / "data" / "value_model.txt"))
    print("saved -> data/value_model.txt")


if __name__ == "__main__":
    main()
