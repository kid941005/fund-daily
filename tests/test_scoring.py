"""
Tests for scoring module - 8 dimensions + calculator + weights + config + models
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestScoreInputModel:
    """Test ScoreInput dataclass"""

    def test_score_input_creation(self):
        from src.scoring.models import ScoreInput

        inp = ScoreInput(
            fund_detail={"name": "test"},
            risk_metrics={"sharpe_ratio": 1.5},
            market_sentiment="乐观",
            market_score=80,
            news=[],
            hot_sectors=[],
            commodity_sentiment="偏多",
            fund_manager={"star": 5, "workTime": "5年"},
            fund_type="股票型",
            fund_scale=10.0,
            daily_change=1.5,
            fund_data={"return_1m": 5.0, "return_3m": 10.0},
            fund_code="000001",
        )
        assert inp.fund_code == "000001"
        assert inp.market_sentiment == "乐观"
        assert inp.fund_scale == 10.0

    def test_score_input_from_dict(self):
        from src.scoring.models import ScoreInput

        data = {
            "fund_detail": {"name": "test"},
            "risk_metrics": {},
            "market_sentiment": "平稳",
            "market_score": 50,
            "news": [],
            "hot_sectors": [],
            "commodity_sentiment": "平稳",
            "fund_manager": None,
            "fund_type": "混合型",
            "fund_scale": 5.0,
            "daily_change": -1.0,
            "fund_data": {"return_1m": -3.0, "return_3m": 5.0},
            "fund_code": "000002",
        }
        inp = ScoreInput.from_dict(data)
        assert inp.fund_code == "000002"
        assert inp.market_sentiment == "平稳"


class TestWeights:
    """Test weights.py"""

    def test_validate_weights_valid(self):
        from src.scoring.weights import validate_weights

        valid, msg = validate_weights()
        assert valid is True
        assert msg == "权重配置有效"

    def test_get_weight_existing(self):
        from src.scoring.weights import get_weight

        assert get_weight("valuation") == 25
        assert get_weight("performance") == 20
        assert get_weight("risk_control") == 15
        assert get_weight("momentum") == 15
        assert get_weight("sentiment") == 10
        assert get_weight("sector") == 8
        assert get_weight("manager") == 4
        assert get_weight("liquidity") == 3

    def test_get_weight_missing(self):
        from src.scoring.weights import get_weight

        assert get_weight("nonexistent") == 0

    def test_get_all_weights(self):
        from src.scoring.weights import get_all_weights

        weights = get_all_weights()
        assert isinstance(weights, dict)
        assert len(weights) == 8
        assert "valuation" in weights
        assert "performance" in weights

    def test_get_total_weight(self):
        from src.scoring.weights import get_total_weight

        total = get_total_weight()
        assert total == 100


class TestConfigCompat:
    """Test config.py validate_weights_compat"""

    def test_validate_weights_compat_valid(self):
        from src.scoring.config import validate_weights_compat

        valid, msg = validate_weights_compat()
        assert valid is True
        assert msg == "权重配置有效"


class TestValuationScore:
    """Test valuation.py"""

    def test_calculate_valuation_score_positive(self):
        from src.scoring.valuation import calculate_valuation_score

        fund_detail = {}
        fund_data = {"return_1y": 35.0, "return_3m": 12.0}
        result = calculate_valuation_score(fund_detail, fund_data)
        assert "score" in result
        assert isinstance(result["score"], (int, float))
        assert result["score"] >= 0

    def test_calculate_valuation_score_zero(self):
        from src.scoring.valuation import calculate_valuation_score

        fund_detail = {}
        fund_data = {"return_1y": 0, "return_3m": 0}
        result = calculate_valuation_score(fund_detail, fund_data)
        assert result["score"] >= 0

    def test_calculate_valuation_score_no_data(self):
        from src.scoring.valuation import calculate_valuation_score

        result = calculate_valuation_score({}, None)
        assert "score" in result


class TestPerformanceScore:
    """Test performance.py"""

    def test_calculate_performance_score_positive(self):
        from src.scoring.performance import calculate_performance_score

        fund_data = {"return_3m": 20.0, "return_1m": 8.0}
        result = calculate_performance_score(fund_data)
        assert "score" in result
        assert isinstance(result["score"], (int, float))

    def test_calculate_performance_score_negative(self):
        from src.scoring.performance import calculate_performance_score

        fund_data = {"return_3m": -10.0, "return_1m": -8.0}
        result = calculate_performance_score(fund_data)
        assert "score" in result
        assert result["score"] >= 0

    def test_calculate_performance_score_no_data(self):
        from src.scoring.performance import calculate_performance_score

        result = calculate_performance_score(None)
        assert result["score"] == 6


class TestRiskControlScore:
    """Test risk_control.py"""

    def test_calculate_risk_control_score_good(self):
        from src.scoring.risk_control import calculate_risk_control_score

        risk_metrics = {"sharpe_ratio": 2.0, "estimated_max_drawdown": 8.0, "volatility": 8.0}
        fund_data = {}
        result = calculate_risk_control_score(risk_metrics, fund_data)
        assert "score" in result
        assert isinstance(result["score"], (int, float))

    def test_calculate_risk_control_score_poor(self):
        from src.scoring.risk_control import calculate_risk_control_score

        risk_metrics = {"sharpe_ratio": -0.5, "estimated_max_drawdown": 35.0, "volatility": 25.0}
        fund_data = {}
        result = calculate_risk_control_score(risk_metrics, fund_data)
        assert "score" in result


class TestMomentumScore:
    """Test momentum.py"""

    def test_calculate_momentum_score_up(self):
        from src.scoring.momentum import calculate_momentum_score

        fund_data = {"return_1m": 12.0, "return_3m": 15.0, "daily_change": 3.0}
        result = calculate_momentum_score(fund_data)
        assert "score" in result

    def test_calculate_momentum_score_down(self):
        from src.scoring.momentum import calculate_momentum_score

        fund_data = {"return_1m": -15.0, "return_3m": -10.0, "daily_change": -3.0}
        result = calculate_momentum_score(fund_data)
        assert "score" in result

    def test_calculate_momentum_score_no_data(self):
        from src.scoring.momentum import calculate_momentum_score

        result = calculate_momentum_score(None)
        assert result["score"] == 5


class TestSentimentScore:
    """Test sentiment.py"""

    def test_calculate_sentiment_score_bullish(self):
        from src.scoring.sentiment import calculate_sentiment_score

        result = calculate_sentiment_score("乐观", 80)
        assert result["score"] == 10

    def test_calculate_sentiment_score_bearish(self):
        from src.scoring.sentiment import calculate_sentiment_score

        result = calculate_sentiment_score("恐慌", 20)
        assert result["score"] == 0

    def test_calculate_sentiment_score_neutral(self):
        from src.scoring.sentiment import calculate_sentiment_score

        result = calculate_sentiment_score("平稳", 50)
        assert result["score"] == 5

    def test_calculate_sentiment_score_unknown(self):
        from src.scoring.sentiment import calculate_sentiment_score

        result = calculate_sentiment_score("未知", 50)
        assert result["score"] == 5  # default


class TestSectorScore:
    """Test sector.py"""

    def test_calculate_sector_score_match(self):
        from src.scoring.sector import calculate_sector_score

        hot_sectors = [{"name": "新能源", "change": 2.5}]
        fund_data = {}
        result = calculate_sector_score("新能源股票", hot_sectors, "乐观", fund_data)
        assert "score" in result

    def test_calculate_sector_score_no_match(self):
        from src.scoring.sector import calculate_sector_score

        hot_sectors = [{"name": "医药", "change": 1.0}]
        fund_data = {}
        result = calculate_sector_score("消费", hot_sectors, "平稳", fund_data)
        assert "score" in result


class TestManagerScore:
    """Test manager.py"""

    def test_calculate_manager_score_top(self):
        from src.scoring.manager import calculate_manager_score

        fund_manager = {"star": 5, "workTime": "8年"}
        result = calculate_manager_score(fund_manager)
        assert result["score"] == 4

    def test_calculate_manager_score_mid(self):
        from src.scoring.manager import calculate_manager_score

        fund_manager = {"star": 4, "workTime": "4年"}
        result = calculate_manager_score(fund_manager)
        assert result["score"] == 3

    def test_calculate_manager_score_low(self):
        from src.scoring.manager import calculate_manager_score

        fund_manager = {"star": 2, "workTime": "1年"}
        result = calculate_manager_score(fund_manager)
        assert result["score"] == 1

    def test_calculate_manager_score_none(self):
        from src.scoring.manager import calculate_manager_score

        result = calculate_manager_score(None)
        assert result["score"] == 1


class TestLiquidityScore:
    """Test liquidity.py"""

    def test_calculate_liquidity_score_normal(self):
        from src.scoring.liquidity import calculate_liquidity_score

        result = calculate_liquidity_score(1.5, 100.0)
        assert result["score"] == 3

    def test_calculate_liquidity_score_high_volatility(self):
        from src.scoring.liquidity import calculate_liquidity_score

        result = calculate_liquidity_score(6.0, 50.0)
        assert result["score"] == 1


class TestCalculatorGetGrade:
    """Test _get_grade boundary values"""

    def test_grade_boundaries(self):
        from src.scoring.calculator import _get_grade

        assert _get_grade(0) == "D"
        assert _get_grade(39) == "D"
        assert _get_grade(40) == "C"
        assert _get_grade(49) == "C"
        assert _get_grade(50) == "C+"
        assert _get_grade(59) == "C+"
        assert _get_grade(60) == "B"
        assert _get_grade(69) == "B"
        assert _get_grade(70) == "B+"
        assert _get_grade(79) == "B+"
        assert _get_grade(80) == "A"
        assert _get_grade(100) == "A"


class TestCalculatorTotalScore:
    """Test calculate_total_score with mocked dimension functions"""

    def test_calculate_total_score_mocked(self, monkeypatch):
        # Patch dimension functions at their source modules (they're imported inside calculate_total_score)
        import src.scoring.valuation as valuation_mod
        import src.scoring.performance as perf_mod
        import src.scoring.risk_control as rc_mod
        import src.scoring.momentum as mom_mod
        import src.scoring.sentiment as sent_mod
        import src.scoring.sector as sector_mod
        import src.scoring.manager as mgr_mod
        import src.scoring.liquidity as liq_mod
        import src.scoring.calculator as calc_mod

        monkeypatch.setattr(valuation_mod, "calculate_valuation_score", lambda *a, **kw: {"score": 20.0})
        monkeypatch.setattr(perf_mod, "calculate_performance_score", lambda *a, **kw: {"score": 15.0})
        monkeypatch.setattr(rc_mod, "calculate_risk_control_score", lambda *a, **kw: {"score": 12.0})
        monkeypatch.setattr(mom_mod, "calculate_momentum_score", lambda *a, **kw: {"score": 10.0})
        monkeypatch.setattr(sent_mod, "calculate_sentiment_score", lambda *a, **kw: {"score": 8.0})
        monkeypatch.setattr(sector_mod, "calculate_sector_score", lambda *a, **kw: {"score": 6.0})
        monkeypatch.setattr(mgr_mod, "calculate_manager_score", lambda *a, **kw: {"score": 3.0})
        monkeypatch.setattr(liq_mod, "calculate_liquidity_score", lambda *a, **kw: {"score": 2.0})

        # Clear cache to avoid cache hits
        monkeypatch.setattr(calc_mod, "_get_cached_score", lambda x: None)

        result = calc_mod.calculate_total_score(
            fund_detail={},
            risk_metrics={},
            market_sentiment="乐观",
            market_score=80,
            news=[],
            hot_sectors=[],
            commodity_sentiment="偏多",
            fund_manager={"star": 5, "workTime": "5年"},
            fund_type="股票型",
            fund_scale=10.0,
            daily_change=1.0,
            fund_data={"return_1m": 5.0, "return_3m": 10.0},
            fund_code="000001",
        )

        assert result["total_score"] == 76.0  # 20+15+12+10+8+6+3+2
        assert result["grade"] == "B+"
        assert "details" in result
        assert len(result["details"]) == 8

    def test_calculate_total_score_with_cache(self, monkeypatch):
        from src.scoring import calculator

        cached_result = {
            "total_score": 85.0,
            "base_score": 85.0,
            "ranking_bonus": 0,
            "max_score": 100,
            "grade": "A",
            "details": {},
        }

        def mock_get_cached(code):
            return cached_result.copy() if code == "000001" else None

        monkeypatch.setattr(calculator, "_get_cached_score", mock_get_cached)

        result = calculator.calculate_total_score(
            fund_detail={},
            risk_metrics={},
            market_sentiment="乐观",
            market_score=80,
            news=[],
            hot_sectors=[],
            commodity_sentiment="偏多",
            fund_manager={},
            fund_type="",
            fund_scale=0,
            daily_change=0,
            fund_data={},
            fund_code="000001",
        )

        assert result["total_score"] == 85.0
        assert result.get("from_cache") is True


class TestFormatScoreReport:
    """Test format_score_report"""

    def test_format_score_report_basic(self):
        from src.scoring.calculator import format_score_report

        result = {
            "total_score": 75.0,
            "grade": "B+",
            "details": {
                "valuation": {"score": 20},
                "performance": {"score": 15},
                "risk_control": {"score": 10},
                "momentum": {"score": 10},
                "sentiment": {"score": 8},
                "sector": {"score": 6},
                "manager": {"score": 3},
                "liquidity": {"score": 2},
            },
        }
        report = format_score_report(result)
        assert "总分" in report
        assert "75" in report
        assert "B+" in report

    def test_format_score_report_with_ranking_bonus(self):
        from src.scoring.calculator import format_score_report

        result = {
            "total_score": 83.0,
            "base_score": 75.0,
            "ranking_bonus": 8,
            "grade": "A",
            "details": {
                "valuation": {"score": 20},
                "performance": {"score": 15},
                "risk_control": {"score": 10},
                "momentum": {"score": 10},
                "sentiment": {"score": 8},
                "sector": {"score": 6},
                "manager": {"score": 3},
                "liquidity": {"score": 2},
            },
        }
        report = format_score_report(result)
        assert "排名加分" in report


class TestApplyRankingBonus:
    """Test apply_ranking_bonus"""

    def test_apply_ranking_bonus_empty(self):
        from src.scoring.calculator import apply_ranking_bonus

        assert apply_ranking_bonus([]) == []
        assert apply_ranking_bonus([]) == []

    def test_apply_ranking_bonus_single(self):
        from src.scoring.calculator import apply_ranking_bonus

        funds = [
            {"code": "000001", "score_100": {"total_score": 80, "grade": "A"}}
        ]
        result = apply_ranking_bonus(funds)
        assert result[0]["score_100"]["total_score"] == 80

    def test_apply_ranking_bonus_multiple(self):
        from src.scoring.calculator import apply_ranking_bonus

        funds = [
            {"code": "000001", "daily_change": 5.0, "return_1m": 10.0,
             "score_100": {"total_score": 80, "grade": "A"}},
            {"code": "000002", "daily_change": 3.0, "return_1m": 8.0,
             "score_100": {"total_score": 75, "grade": "B+"}},
            {"code": "000003", "daily_change": 1.0, "return_1m": 5.0,
             "score_100": {"total_score": 70, "grade": "B"}},
            {"code": "000004", "daily_change": -1.0, "return_1m": 2.0,
             "score_100": {"total_score": 65, "grade": "B"}},
        ]
        result = apply_ranking_bonus(funds)
        # Top performer should get ranking bonus
        assert result[0]["score_100"]["ranking_bonus"] > 0
        assert result[0]["score_100"]["base_score"] == 80


class TestCalculatorScoreInput:
    """Test calculate_score_v2 with ScoreInput"""

    def test_calculate_score_v2(self, monkeypatch):
        from src.scoring import calculator
        from src.scoring.models import ScoreInput

        def mock_total_score(**kwargs):
            return {
                "total_score": 80.0,
                "base_score": 80.0,
                "ranking_bonus": 0,
                "max_score": 100,
                "grade": "A",
                "details": {
                    "valuation": {"score": 20},
                    "performance": {"score": 15},
                    "risk_control": {"score": 10},
                    "momentum": {"score": 10},
                    "sentiment": {"score": 8},
                    "sector": {"score": 6},
                    "manager": {"score": 3},
                    "liquidity": {"score": 2},
                },
            }

        monkeypatch.setattr(calculator, "calculate_total_score", mock_total_score)

        inp = ScoreInput(
            fund_detail={},
            risk_metrics={},
            market_sentiment="乐观",
            market_score=80,
            news=[],
            hot_sectors=[],
            commodity_sentiment="偏多",
            fund_manager={},
            fund_type="股票型",
            fund_scale=10.0,
            daily_change=1.0,
            fund_data={},
            fund_code="000001",
        )

        result = calculator.calculate_score_v2(inp)
        assert result["total_score"] == 80.0
        assert result["grade"] == "A"
