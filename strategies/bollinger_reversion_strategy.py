from __future__ import annotations

from vnpy.app.cta_strategy import CtaTemplate
from vnpy.trader.object import BarData, TickData, TradeData, OrderData
from vnpy.trader.utility import ArrayManager, BarGenerator


class BollingerReversionStrategy(CtaTemplate):
    """Mean-reversion CTA strategy based on Bollinger bands and adaptive stops."""

    author = "cto.new"

    boll_window: int = 20
    entry_dev: float = 2.0
    exit_dev: float = 0.8
    stop_multiplier: float = 3.0
    fixed_size: int = 1

    parameters = [
        "boll_window",
        "entry_dev",
        "exit_dev",
        "stop_multiplier",
        "fixed_size",
    ]

    variables = [
        "boll_mid",
        "boll_upper",
        "boll_lower",
        "pos",
    ]

    def __init__(self, cta_engine, strategy_name: str, vt_symbol: str, setting: dict) -> None:
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.bg = BarGenerator(self.on_bar)
        self.am = ArrayManager()

        self.boll_mid: float = 0.0
        self.boll_upper: float = 0.0
        self.boll_lower: float = 0.0

        self.long_stop: float = float("-inf")
        self.short_stop: float = float("inf")

    def on_init(self) -> None:
        self.write_log("Bollinger reversion strategy initialized")
        self.load_bar(30)

    def on_start(self) -> None:
        self.write_log("Bollinger reversion strategy started")
        self.put_event()

    def on_stop(self) -> None:
        self.write_log("Bollinger reversion strategy stopped")
        self.put_event()

    def on_tick(self, tick: TickData) -> None:
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData) -> None:
        self.am.update_bar(bar)

        if not self.am.inited:
            return

        std = self.am.std(self.boll_window)
        if std == 0:
            return

        self.boll_mid = self.am.sma(self.boll_window)
        self.boll_upper = self.boll_mid + std * self.entry_dev
        self.boll_lower = self.boll_mid - std * self.entry_dev

        exit_upper = self.boll_mid + std * self.exit_dev
        exit_lower = self.boll_mid - std * self.exit_dev

        self.cancel_all()

        if self.pos == 0:
            if bar.close_price < self.boll_lower:
                self.buy(bar.close_price, self.fixed_size)
                self.long_stop = bar.close_price - std * self.stop_multiplier
            elif bar.close_price > self.boll_upper:
                self.short(bar.close_price, self.fixed_size)
                self.short_stop = bar.close_price + std * self.stop_multiplier

        elif self.pos > 0:
            new_long_stop = bar.close_price - std * self.stop_multiplier
            if self.long_stop == float("-inf"):
                self.long_stop = new_long_stop
            else:
                self.long_stop = max(self.long_stop, new_long_stop)

            if bar.close_price >= exit_upper or bar.close_price <= self.long_stop:
                self.sell(bar.close_price, abs(self.pos))
                self.long_stop = float("-inf")

        elif self.pos < 0:
            new_short_stop = bar.close_price + std * self.stop_multiplier
            if self.short_stop == float("inf"):
                self.short_stop = new_short_stop
            else:
                self.short_stop = min(self.short_stop, new_short_stop)

            if bar.close_price <= exit_lower or bar.close_price >= self.short_stop:
                self.cover(bar.close_price, abs(self.pos))
                self.short_stop = float("inf")

        if self.pos == 0:
            self.long_stop = float("-inf")
            self.short_stop = float("inf")

        self.put_event()

    def on_order(self, order: OrderData) -> None:
        self.put_event()

    def on_trade(self, trade: TradeData) -> None:
        self.put_event()

    def on_stop_order(self, stop_order) -> None:
        self.put_event()
