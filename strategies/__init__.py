"""Collection of ready-to-use CTA strategies built on top of vn.py."""

from .double_ma_strategy import DoubleMaStrategy
from .bollinger_reversion_strategy import BollingerReversionStrategy
from .ashare_momentum_strategy import AshareMomentumStrategy

__all__ = ["DoubleMaStrategy", "BollingerReversionStrategy", "AshareMomentumStrategy"]
