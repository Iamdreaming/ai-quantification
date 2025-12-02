from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Type

from vnpy.app.cta_strategy import CtaTemplate
from vnpy.app.cta_strategy.backtesting import BacktestingEngine
from vnpy.trader.constant import Interval

from strategies import AshareMomentumStrategy, BollingerReversionStrategy, DoubleMaStrategy

STRATEGIES: Dict[str, Type[CtaTemplate]] = {
    "double_ma": DoubleMaStrategy,
    "bollinger": BollingerReversionStrategy,
    "ashare_momentum": AshareMomentumStrategy,
}

DEFAULT_SETTINGS = {
    "double_ma": {
        "fast_window": 10,
        "slow_window": 60,
        "atr_window": 20,
        "atr_multiplier": 2.0,
        "fixed_size": 1,
    },
    "bollinger": {
        "boll_window": 20,
        "entry_dev": 2.0,
        "exit_dev": 0.8,
        "stop_multiplier": 3.0,
        "fixed_size": 1,
    },
    "ashare_momentum": {
        "fast_window": 20,
        "slow_window": 60,
        "breakout_window": 30,
        "atr_window": 14,
        "atr_multiplier": 2.5,
        "limit_pct": 0.095,
        "limit_buffer": 0.002,
        "fixed_size": 100,
    },
}

INTERVAL_CHOICES = {"minute": Interval.MINUTE, "hour": Interval.HOUR, "daily": Interval.DAILY}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run vn.py CTA strategy backtests")
    parser.add_argument("--strategy", choices=STRATEGIES.keys(), default="double_ma")
    parser.add_argument("--vt-symbol", default="rb888.SHFE", help="Contract to backtest, e.g. IF88.CFFEX")
    parser.add_argument("--start", default="2022-01-01T09:00:00", help="Backtest start time, ISO format")
    parser.add_argument("--end", default="2022-12-31T15:00:00", help="Backtest end time, ISO format")
    parser.add_argument("--interval", choices=INTERVAL_CHOICES.keys(), default="minute")
    parser.add_argument("--capital", type=float, default=1_000_000)
    parser.add_argument("--rate", type=float, default=0.0001, help="Commission rate")
    parser.add_argument("--slippage", type=float, default=1.0)
    parser.add_argument("--size", type=int, default=10, help="Contract size or multiplier")
    parser.add_argument("--pricetick", type=float, default=1.0)
    parser.add_argument("--inverse", action="store_true", help="Set for inverse contracts such as crypto perpetuals")
    parser.add_argument("--risk-free", dest="risk_free", type=float, default=0.0)
    parser.add_argument("--config", type=str, help="Path to JSON file with strategy settings")
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        help="Override individual strategy parameters, e.g. --param fast_window=30",
    )
    return parser.parse_args()


def cast_value(raw_value: str):
    lowered = raw_value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"

    try:
        return int(raw_value)
    except ValueError:
        pass

    try:
        return float(raw_value)
    except ValueError:
        return raw_value


def parse_interval(name: str) -> Interval:
    try:
        return INTERVAL_CHOICES[name]
    except KeyError as exc:
        raise ValueError(f"Unsupported interval: {name}") from exc


def build_strategy_setting(args: argparse.Namespace) -> dict:
    setting = dict(DEFAULT_SETTINGS[args.strategy])

    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        override_setting = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(override_setting, dict):
            raise ValueError("Config file must contain a JSON object")
        setting.update(override_setting)

    for raw in args.param:
        if "=" not in raw:
            raise ValueError(f"Invalid parameter override: {raw}")
        key, value = raw.split("=", 1)
        setting[key.strip()] = cast_value(value.strip())

    return setting


def main() -> None:
    args = parse_args()

    strategy_cls = STRATEGIES[args.strategy]
    start = datetime.fromisoformat(args.start)
    end = datetime.fromisoformat(args.end) if args.end else None

    engine = BacktestingEngine()
    engine.set_parameters(
        vt_symbol=args.vt_symbol,
        interval=parse_interval(args.interval),
        start=start,
        end=end,
        rate=args.rate,
        slippage=args.slippage,
        size=args.size,
        pricetick=args.pricetick,
        capital=args.capital,
        inverse=args.inverse,
        risk_free=args.risk_free,
    )

    setting = build_strategy_setting(args)
    engine.add_strategy(strategy_cls, setting)

    engine.load_data()
    engine.run_backtesting()

    engine.calculate_result()
    statistics = engine.calculate_statistics()

    print("\n===== 回测指标（Backtest Statistics） =====")
    for key, value in statistics.items():
        print(f"{key:20s}: {value}")

    engine.show_chart()


if __name__ == "__main__":
    main()
