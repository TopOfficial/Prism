"""Leak-free feature scaling: fit mean/std on one split (train), apply to others."""
from __future__ import annotations

import numpy as np
import pandas as pd

# Columns GoldTradingEnv reads as raw economic quantities (price, return used
# for PnL). Never include these in a scaler's column list -- z-scoring them
# would corrupt reward/PnL math even though the rest of the pipeline still runs.
RAW_COLUMNS = ("close", "log_return")


def scalable_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in RAW_COLUMNS]


class FeatureScaler:
    def __init__(self, columns: list[str]):
        self.columns = columns
        self.mean_: pd.Series | None = None
        self.std_: pd.Series | None = None

    def fit(self, df: pd.DataFrame) -> "FeatureScaler":
        self.mean_ = df[self.columns].mean()
        self.std_ = df[self.columns].std().replace(0, 1.0)
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.mean_ is None or self.std_ is None:
            raise RuntimeError("FeatureScaler.fit() must be called before transform()")
        out = df.copy()
        out[self.columns] = (df[self.columns] - self.mean_) / self.std_
        out[self.columns] = out[self.columns].clip(-10, 10)
        return out

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.fit(df).transform(df)
