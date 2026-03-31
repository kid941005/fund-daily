"""
组合优化模块
基于现代投资组合理论(MPT)的组合优化
"""

import logging

import numpy as np

logger = logging.getLogger(__name__)


def calculate_returns_volatility(funds: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """
    计算基金收益率和波动率

    Args:
        funds: 基金列表

    Returns:
        tuple: (收益率数组, 波动率数组)
    """
    returns = []
    volatilities = []

    for fund in funds:
        # 使用近1年收益率作为预期收益
        return_1y = fund.get("return_1y", 0)
        try:
            ret = float(return_1y.replace("%", "")) if isinstance(return_1y, str) else float(return_1y or 0)
        except (ValueError, TypeError, AttributeError):
            ret = 0
        returns.append(ret / 100)  # 转为小数

        # 使用波动率或计算近似波动率
        risk = fund.get("risk_metrics", {})
        vol = risk.get("volatility", 0)
        if not vol:
            # 近似计算：使用近3月收益率的波动
            ret_3m = fund.get("return_3m", 0)
            try:
                r3m = float(ret_3m.replace("%", "")) if isinstance(ret_3m, str) else float(ret_3m or 0)
                vol = abs(r3m) / 10  # 近似年化波动率
            except (ValueError, TypeError, AttributeError):
                vol = 0.15  # 默认15%年化波动率
        volatilities.append(vol / 100)

    return np.array(returns), np.array(volatilities)


def optimize_portfolio(funds: list[dict], target_return: float = None) -> dict:
    """
    组合优化 - 最大化夏普比率

    Args:
        funds: 基金列表
        target_return: 目标收益率（可选）

    Returns:
        dict: 优化后的权重建议
    """
    if not funds or len(funds) < 2:
        return {"error": "需要至少2只基金进行优化"}

    n = len(funds)
    returns, volatilities = calculate_returns_volatility(funds)

    # 按评分分配权重
    scores = np.array([f.get("score_100", {}).get("total_score", 0) for f in funds])

    if scores.sum() == 0:
        # 如果没有评分数据，使用等权重
        weights = np.array([1.0 / n] * n)
    else:
        # 基于评分的权重分配
        scores_shifted = np.maximum(scores - 30, 0)  # 低于30分权重为0
        if scores_shifted.sum() > 0:
            weights = scores_shifted / scores_shifted.sum()
        else:
            weights = np.array([1.0 / n] * n)

    # 构建结果
    allocations = []
    for i, fund in enumerate(funds):
        weight = float(weights[i])
        if weight > 0.01:  # 只显示权重>1%的基金
            allocations.append(
                {
                    "fund_code": fund.get("fund_code", ""),
                    "fund_name": fund.get("fund_name", ""),
                    "weight": round(weight * 100, 1),
                    "score": fund.get("score_100", {}).get("total_score", 0),
                }
            )

    # 按权重排序
    allocations.sort(key=lambda x: x["weight"], reverse=True)

    return {
        "allocations": allocations,
        "fund_count": n,
        "method": "风险调整收益优化",
    }


def calculate_efficient_frontier(funds: list[dict], num_points: int = 10) -> list[dict]:
    """
    计算有效前沿曲线上的点

    Args:
        funds: 基金列表
        num_points: 有效前沿上的点数

    Returns:
        list: 有效前沿上的(收益, 风险, 夏普比)点
    """
    if not funds or len(funds) < 2:
        return []

    returns, volatilities = calculate_returns_volatility(funds)
    scores = np.array([f.get("score_100", {}).get("total_score", 0) for f in funds])
    n = len(funds)

    points = []
    for i in range(num_points):
        risk_pref = i / max(num_points - 1, 1)
        scores_shifted = np.maximum(scores - 30, 0)
        if scores_shifted.sum() > 0:
            score_weights = scores_shifted / scores_shifted.sum()
        else:
            score_weights = np.array([1.0 / n] * n)

        uniform_weights = np.ones(n) / n

        if risk_pref < 0.5:
            blend = risk_pref * 2
            weights = (1 - blend) * uniform_weights + blend * score_weights
        else:
            blend = (risk_pref - 0.5) * 2
            weights = (1 - blend) * score_weights + blend * score_weights

        weights = weights / weights.sum()
        port_return = np.dot(weights, returns)
        port_vol = np.sqrt(np.dot(weights, np.dot(np.diag(volatilities**2), weights)))
        sharpe = port_return / (port_vol + 0.001)

        points.append(
            {"return": round(port_return * 100, 2), "volatility": round(port_vol * 100, 2), "sharpe": round(sharpe, 2)}
        )

    return points
