"""
技术指标计算模块
提供 MA、MACD、RSI 等技术分析工具
"""



def calculate_ma(closes: list[float], period: int) -> float | None:
    """计算移动平均线"""
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def calculate_macd(closes: list[float]) -> dict:
    """计算 MACD 指标"""
    if len(closes) < 26:
        return {"macd": 0, "signal": 0, "histogram": 0, "trend": "unknown"}

    def ema(data: list[float], period: int) -> list[float]:
        ema_values = []
        multiplier = 2 / (period + 1)
        for i, price in enumerate(data):
            if i < period - 1:
                ema_values.append(sum(data[:period]) / period)
            else:
                ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
        return ema_values

    ema_12 = ema(closes, 12)
    ema_26 = ema(closes, 26)
    macd_line = [ema_12[i] - ema_26[i] for i in range(len(closes))]
    signal_line = ema(macd_line, 9)
    histogram = macd_line[-1] - signal_line[-1] if signal_line else 0

    if histogram > 0:
        trend = "bullish"
    elif histogram < 0:
        trend = "bearish"
    else:
        trend = "neutral"

    return {
        "macd": macd_line[-1],
        "signal": signal_line[-1],
        "histogram": histogram,
        "trend": trend,
    }


def calculate_rsi(closes: list[float], period: int = 14) -> float | None:
    """计算 RSI 指标"""
    if len(closes) < period + 1:
        return None

    gains = []
    losses = []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
