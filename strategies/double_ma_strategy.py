from __future__ import annotations

from vnpy.app.cta_strategy import CtaTemplate
from vnpy.trader.object import BarData, TickData, TradeData, OrderData
from vnpy.trader.utility import ArrayManager, BarGenerator


class DoubleMaStrategy(CtaTemplate):
    """Trend following CTA strategy built on double moving-average crossovers with ATR-based trailing stops."""

    author = "cto.new"

    fast_window: int = 10
    slow_window: int = 60
    atr_window: int = 20
    atr_multiplier: float = 2.0
    fixed_size: int = 1

    parameters = [
        "fast_window",
        "slow_window",
        "atr_window",
        "atr_multiplier",
        "fixed_size",
    ]

    variables = [
        "fast_ma",
        "slow_ma",
        "atr_value",
        "trend",
        "pos",
    ]

    def __init__(self, cta_engine, strategy_name: str, vt_symbol: str, setting: dict) -> None:
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.bg = BarGenerator(self.on_bar)
        self.am = ArrayManager()

        self.fast_ma: float = 0.0
        self.slow_ma: float = 0.0
        self.atr_value: float = 0.0
        self.trend: str = ""

        self.long_stop: float = float("-inf")
        self.short_stop: float = float("inf")

    def on_init(self) -> None:
        self.write_log("Double MA strategy initialized")
        self.load_bar(20)

    def on_start(self) -> None:
        self.write_log("Double MA strategy started")
        self.put_event()

    def on_stop(self) -> None:
        self.write_log("Double MA strategy stopped")
        self.put_event()

    def on_tick(self, tick: TickData) -> None:
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData) -> None:
        self.am.update_bar(bar)

        if not self.am.inited:
            return

        previous_fast = self.fast_ma
        previous_slow = self.slow_ma

        self.fast_ma = self.am.sma(self.fast_window)
        self.slow_ma = self.am.sma(self.slow_window)
        self.atr_value = self.am.atr(self.atr_window)

        long_signal = previous_fast <= previous_slow and self.fast_ma > self.slow_ma
        short_signal = previous_fast >= previous_slow and self.fast_ma < self.slow_ma

        self.cancel_all()

        if long_signal and self.pos <= 0:
            if self.pos < 0:
                self.cover(bar.close_price, abs(self.pos))
            self.buy(bar.close_price, self.fixed_size)
            self.trend = "long"
            self.long_stop = bar.close_price - self.atr_value * self.atr_multiplier

        elif short_signal and self.pos >= 0:
            if self.pos > 0:
                self.sell(bar.close_price, self.pos)
            self.short(bar.close_price, self.fixed_size)
            self.trend = "short"
            self.short_stop = bar.close_price + self.atr_value * self.atr_multiplier

        if self.pos > 0 and self.atr_value > 0:
            trailing_stop = bar.close_price - self.atr_value * self.atr_multiplier
            if self.long_stop == float("-inf"):
                self.long_stop = trailing_stop
            else:
                self.long_stop = max(self.long_stop, trailing_stop)

            if bar.close_price <= self.long_stop:
                self.sell(bar.close_price, abs(self.pos))
                self.trend = ""
                self.long_stop = float("-inf")

        elif self.pos < 0 and self.atr_value > 0:
            trailing_stop = bar.close_price + self.atr_value * self.atr_multiplier
            if self.short_stop == float("inf"):
                self.short_stop = trailing_stop
            else:
                self.short_stop = min(self.short_stop, trailing_stop)

            if bar.close_price >= self.short_stop:
                self.cover(bar.close_price, abs(self.pos))
                self.trend = ""
                self.short_stop = float("inf")

        else:
            self.long_stop = float("-inf")
            self.short_stop = float("inf")
            self.trend = ""

        self.put_event()

    def on_order(self, order: OrderData) -> None:
        self.put_event()

    def on_trade(self, trade: TradeData) -> None:
        self.put_event()

    def on_stop_order(self, stop_order) -> None:
        self.put_event()
