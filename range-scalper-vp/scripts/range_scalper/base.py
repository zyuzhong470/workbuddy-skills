"""策略抽象基类与配置数据类。"""
from dataclasses import dataclass
from typing import Literal

import pandas as pd


@dataclass
class StrategyConfig:
    name:         str
    take_profit:  float
    stop_loss:    float
    direction:    Literal["both", "short_only"]


class BaseStrategy:
    def __init__(self, config: StrategyConfig):
        self.config = config

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError
