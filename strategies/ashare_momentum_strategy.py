from __future__ import annotations

from vnpy.app.cta_strategy import CtaTemplate
from vnpy.trader.object import BarData, TickData, TradeData, OrderData
from vnpy.trader.utility import ArrayManager, BarGenerator


class AshareMomentumStrategy(CtaTemplate):
    """Long-only breakout strategy that respects A-share limit rules and uses ATR trailing exits."""

    author = "cto.new"

    fast_window: int = 20
    slow_window: int = 60
    breakout_window: int = 30
    atr_window: int = 14
    atr_multiplier: float = 2.5
    limit_pct: float = 0.095
    limit_buffer: float = 0.002
    fixed_size: int = 100

    parameters = [
        "fast_window",
        "slow_window",
        "breakout_window",
        "atr_window",
        "atr_multiplier",
        "limit_pct",
        "limit_buffer",
        "fixed_size",
    ]

    variables = [
        "fast_ma",
        "slow_ma",
        "atr_value",
        "breakout_high",
        "pullback_low",
        "long_stop",
        "pos",
    ]

    def __init__(self, cta_engine, strategy_name: str, vt_symbol: str, setting: dict) -> None:
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.bg = BarGenerator(self.on_bar)
        self.am = ArrayManager(200)

        self.fast_ma: float = 0.0
        self.slow_ma: float = 0.0
        self.atr_value: float = 0.0
        self.breakout_high: float = 0.0
        self.pullback_low: float = 0.0
        self.long_stop: float = float("-inf")
        self.prev_close: float = 0.0

    def on_init(self) -> None:
        self.write_log("A-share momentum strategy initialized")
        warmup = max(self.slow_window, self.breakout_window) + self.atr_window
        self.load_bar(warmup)

    def on_start(self) -> None:
        self.write_log("A-share momentum strategy started")
        self.put_event()

    def on_stop(self) -> None:
        self.write_log("A-share momentum strategy stopped")
        self.put_event()

    def on_tick(self, tick: TickData) -> None:
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData) -> None:
        self.am.update_bar(bar)

        if not self.am.inited:
            self.prev_close = bar.close_price
            return

        highs = self.am.high_array[-self.breakout_window - 1 : -1]
        lows = self.am.low_array[-self.breakout_window - 1 : -1]
        if len(highs) < self.breakout_window or len(lows) < self.breakout_window:
            self.prev_close = bar.close_price
            return

        self.fast_ma = self.am.sma(self.fast_window)
        self.slow_ma = self.am.sma(self.slow_window)
        self.atr_value = self.am.atr(self.atr_window)
        self.breakout_high = float(highs.max())
        self.pullback_low = float(lows.min())

        prev_close = self.prev_close
        near_limit_up = False
        limit_down_risk = False
        if prev_close > 0:
            upper_limit = prev_close * (1 + self.limit_pct)
            lower_limit = prev_close * (1 - self.limit_pct)
            near_limit_up = bar.close_price >= upper_limit * (1 - self.limit_buffer)
            limit_down_risk = bar.close_price <= lower_limit * (1 + self.limit_buffer)

        self.cancel_all()

        if self.pos == 0:
            long_signal = (
                self.fast_ma > self.slow_ma
                and bar.close_price > self.breakout_high
                and not near_limit_up
            )

            if long_signal:
                self.buy(bar.close_price, self.fixed_size)
                if self.atr_value > 0:
                    self.long_stop = bar.close_price - self.atr_value * self.atr_multiplier
                else:
                    self.long_stop = bar.close_price * 0.97

        elif self.pos > 0:
            if self.atr_value > 0:
                trailing_stop = bar.close_price - self.atr_value * self.atr_multiplier
                if self.long_stop == float("-inf"):
                    self.long_stop = trailing_stop
                else:
                    self.long_stop = max(self.long_stop, trailing_stop)

            exit_signal = limit_down_risk
            exit_signal = exit_signal or bar.close_price <= self.long_stop
            exit_signal = exit_signal or bar.close_price < self.fast_ma
            exit_signal = exit_signal or self.fast_ma < self.slow_ma
            exit_signal = exit_signal or bar.close_price <= self.pullback_low

            if exit_signal:
                self.sell(bar.close_price, abs(self.pos))
                self.long_stop = float("-inf")

        if self.pos == 0:
            self.long_stop = float("-inf")

        self.prev_close = bar.close_price
        self.put_event()

    def on_order(self, order: OrderData) -> None:
        self.put_event()

    def on_trade(self, trade: TradeData) -> None:
        self.put_event()

    def on_stop_order(self, stop_order) -> None:
        self.put_event()
