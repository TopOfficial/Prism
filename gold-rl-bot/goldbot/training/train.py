"""PPO training on GoldTradingEnv via stable-baselines3."""
from __future__ import annotations

import pandas as pd

from goldbot.env.trading_env import GoldTradingEnv


def train_ppo(
    train_features: pd.DataFrame,
    window_size: int = 24,
    cost_bps: float = 2.0,
    total_timesteps: int = 50_000,
    seed: int = 0,
    policy_kwargs: dict | None = None,
    verbose: int = 0,
):
    """Train a PPO agent on `train_features` and return the fitted model."""
    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env

    def make_env():
        return GoldTradingEnv(train_features, window_size=window_size, cost_bps=cost_bps)

    vec_env = make_vec_env(make_env, n_envs=1, seed=seed)
    model = PPO(
        "MlpPolicy",
        vec_env,
        seed=seed,
        verbose=verbose,
        policy_kwargs=policy_kwargs or {"net_arch": [64, 64]},
    )
    model.learn(total_timesteps=total_timesteps)
    return model
