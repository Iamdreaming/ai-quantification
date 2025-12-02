# AI Quantification (vn.py 策略示例)

基于 [vn.py](https://www.vnpy.com/) 打造的一套轻量化量化策略示例，包含趋势跟随、均值回归以及面向 A 股的趋势突破策略，并提供可直接运行的回测脚本，帮助你快速评估策略表现与参数敏感度。

## 仓库结构

```text
├── backtests/                # 回测脚本
│   └── run_backtest.py
├── strategies/               # 策略源码
│   ├── __init__.py
│   ├── ashare_momentum_strategy.py
│   ├── bollinger_reversion_strategy.py
│   └── double_ma_strategy.py
├── requirements.txt          # 依赖声明
└── README.md
```

## 策略说明

### 1. DoubleMaStrategy —— 趋势跟随
- **核心逻辑**：快/慢双均线金叉开多，死叉开空；结合 ATR 追踪止损控制风险。
- **主要参数**：`fast_window`、`slow_window`、`atr_window`、`atr_multiplier`、`fixed_size`。
- **适用场景**：趋势明显的期货、股票指数或加密资产主力合约。

### 2. BollingerReversionStrategy —— 布林带均值回归
- **核心逻辑**：价格触及布林带上下轨进场，回到中轨附近或触发止损即离场。
- **主要参数**：`boll_window`、`entry_dev`、`exit_dev`、`stop_multiplier`、`fixed_size`。
- **适用场景**：震荡市、区间波动明显的标的。

### 3. AshareMomentumStrategy —— A股趋势突破
- **核心逻辑**：在快慢均线共振的前提下，突破 `breakout_window` 最高价才开仓，避免追高至涨停（`limit_pct`/`limit_buffer`），并用 ATR 追踪止损在恐慌下跌或回撤时平仓。
- **主要参数**：`fast_window`、`slow_window`、`breakout_window`、`atr_window`、`atr_multiplier`、`limit_pct`、`limit_buffer`、`fixed_size`。
- **适用场景**：A股单边上涨或放量突破行情，偏好做多、希望规避涨跌停价格约束的策略。

## 快速开始

1. **安装依赖**（默认你已准备好 Python ≥ 3.9 的环境，并提前安装 vn.py 所需的底层组件与数据采集模块）：
   ```bash
   pip install -r requirements.txt
   ```

2. **运行回测**：
   ```bash
   python backtests/run_backtest.py \
       --strategy double_ma \
       --vt-symbol rb888.SHFE \
       --start 2022-01-01T09:00:00 \
       --end   2022-12-31T15:00:00 \
       --interval minute \
       --capital 1000000 \
       --size 10 \
       --pricetick 1.0
   ```
   执行后脚本会自动：
   - 初始化回测引擎并加载数据（需在 vn.py 中配置好本地数据库或数据服务）；
   - 运行回测、打印核心绩效指标；
   - 弹出 vn.py 自带的收益曲线与回撤曲线。

   针对 A 股的趋势突破策略示例：
   ```bash
   python backtests/run_backtest.py \
       --strategy ashare_momentum \
       --vt-symbol 600000.SH \
       --start 2021-01-01 \
       --end   2022-12-31 \
       --interval daily \
       --capital 500000 \
       --size 100 \
       --pricetick 0.01
   ```
   其中 `size=100` 对应 A 股一手，策略会自动避免追涨停并在跌停附近及时止盈/止损。

## 参数自定义

- **JSON 配置文件**：
  ```bash
  python backtests/run_backtest.py --strategy bollinger --config configs/bollinger.json
  ```
  `config` 文件需为简单的 `key: value` JSON 对象。

- **命令行覆盖**：
  ```bash
  python backtests/run_backtest.py --param fast_window=20 --param slow_window=80
  ```
  传入的值会自动转换为 `bool`、`int`、`float` 或字符串类型。

## 下一步

- 在 vn.py 中接入实时行情，即可直接部署为实盘 CTA 策略；
- 结合 `OptimizationSetting` 扩展参数寻优；
- 增加多品种组合、资金管理以及风险限额模块。

欢迎在此基础上继续扩展更复杂的量化策略或接入私有数据源。
