import pytest

from src.services.quant_service import QuantService, QuantServiceError


class DummyFundService:
    def __init__(self, funds):
        self.funds = funds

    def calculate_holdings_advice(self, holdings):
        return {"funds": self.funds}


@pytest.fixture
def fund_service_minimal():
    return DummyFundService(
        [
            {"fund_code": "000001", "amount": 100.0, "score_100": {"total_score": 60}, "current_pct": 50},
            {"fund_code": "000002", "amount": 50.0, "score_100": {"total_score": 40}, "current_pct": 40},
        ]
    )


@pytest.fixture
def quant_service(fund_service_minimal, monkeypatch):
    qs = QuantService(fund_service=fund_service_minimal)
    monkeypatch.setattr(
        "src.services.quant_service.db.get_holdings",
        lambda user_id: [
            {"code": "000001", "name": "基金A", "amount": 100.0},
            {"code": "000002", "name": "基金B", "amount": 50.0},
        ],
    )
    return qs


def test_optimize_portfolio_success(quant_service):
    result = quant_service.optimize_portfolio("user123")
    assert "allocations" in result


def test_optimize_portfolio_no_holdings(quant_service):
    with pytest.raises(QuantServiceError):
        quant_service.optimize_portfolio(None)


def test_rebalancing_global_when_not_logged(quant_service, monkeypatch):
    monkeypatch.setattr("src.services.quant_service.db.get_db", lambda: _DummyConn())
    monkeypatch.setattr("src.services.quant_service.db.get_cursor", lambda conn: _DummyCursor())
    result = quant_service.rebalancing(None)
    assert "trades" in result


def test_dynamic_weights_simple(quant_service):
    result = quant_service.dynamic_weights()
    assert isinstance(result, dict)


def test_timing_signals_returns_structure(quant_service):
    result = quant_service.timing_signals()
    assert isinstance(result, dict)


def test_portfolio_analysis_requires_holdings(quant_service, monkeypatch):
    # Patch both user and global holdings to be empty
    monkeypatch.setattr(
        "src.services.quant_service.QuantService._fetch_user_holdings",
        lambda self, user_id: [],
    )
    monkeypatch.setattr(
        "src.services.quant_service.QuantService._fetch_all_holdings",
        lambda self: [],
    )
    with pytest.raises(QuantServiceError):
        quant_service.portfolio_analysis(None)


def test_rebalancing_no_amount(monkeypatch, quant_service):
    # Patch both user and global holdings to be empty
    monkeypatch.setattr(
        "src.services.quant_service.QuantService._fetch_user_holdings",
        lambda self, user_id: [],
    )
    monkeypatch.setattr(
        "src.services.quant_service.QuantService._fetch_all_holdings",
        lambda self: [],
    )
    with pytest.raises(QuantServiceError):
        quant_service.rebalancing(None)


class _DummyCursor:
    def execute(self, *args, **kwargs):
        pass

    def fetchall(self):
        return [{"fund_code": "000003", "fund_name": "基金C", "amount": 10.0}]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass


class _DummyConn:
    def cursor(self, *args, **kwargs):
        return _DummyCursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass
