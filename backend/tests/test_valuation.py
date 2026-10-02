import math
from datetime import date
import pytest
from app.valuation.engine import DCFInputs, calculate, calculate_suite, recommendation
from app.valuation.normalization import normalize_number, ttm, financial_eligibility


@pytest.fixture
def golden():
    return dict(revenue_base=1000, revenue_growth=[0]*5, ebit_margin=[.2]*5,
                tax_rate=[.25]*5, da_ratio=[.05]*5, capex_ratio=[.05]*5,
                nwc_ratio=[.1]*5, nwc_base=100, wacc=.1, terminal_growth=0,
                terminal_margin=.2, terminal_tax_rate=.25, terminal_roic=.1,
                excess_cash=100, non_operating_assets=0, interest_bearing_debt=200,
                minority_interest_value=0, preferred_equity_value=0,
                diluted_shares=100, current_price=10)


def test_independent_perpetuity_case(golden):
    result = calculate(DCFInputs(**golden))
    assert result['operating_ev'] == pytest.approx(1500, abs=1e-6)
    assert result['equity_value'] == pytest.approx(1400, abs=1e-6)
    assert result['fair_value'] == pytest.approx(14, abs=1e-6)
    assert result['valuation_gap'] == pytest.approx(.4)
    assert result['discount_to_value'] == pytest.approx(2/7)
    assert all(y['fcff'] == 150 for y in result['years'])
    assert result['recommendation'] == 'recommend'


@pytest.mark.parametrize('field,value', [('wacc', 0), ('wacc', .001), ('diluted_shares', 0),
    ('current_price', -1), ('revenue_base', math.nan), ('excess_cash', math.inf),
    ('terminal_growth', .05), ('revenue_growth', [-1]*5), ('tax_rate', [1.2]*5),
    ('ebit_margin', [.2]*4)])
def test_invalid_inputs(golden, field, value):
    with pytest.raises(ValueError):
        DCFInputs(**{**golden, field: value})


def test_growth_requires_reinvestment(golden):
    result = calculate(DCFInputs(**{**golden, 'terminal_growth': .02}))
    assert result['terminal']['reinvestment_rate'] == pytest.approx(.2)
    assert result['terminal']['fcff'] == pytest.approx(1000 * 1.02 * .2 * .75 * .8)
    with pytest.raises(ValueError):
        DCFInputs(**{**golden, 'terminal_growth': .02, 'terminal_roic': .02})


def test_negative_equity_is_not_a_sell_signal(golden):
    result = calculate(DCFInputs(**{**golden, 'interest_bearing_debt': 10000}))
    assert result['fair_value'] is None
    assert result['raw_fair_value'] < 0
    assert result['recommendation'] == 'unavailable'


def test_boundary_and_missing():
    assert recommendation(10.01, 10) == 'fair_value'
    assert recommendation(9.99, 10) == 'fair_value'
    assert recommendation(10.01001, 10) == 'recommend'
    assert recommendation(9.98, 10) == 'not_recommend'
    assert recommendation(None, 10) == 'unavailable'
    assert recommendation(20, 10, False) == 'unavailable'


def test_suite_and_determinism(golden):
    result = calculate_suite(DCFInputs(**golden))
    assert result == calculate_suite(DCFInputs(**golden))
    assert len(result['sensitivity']['cells']) == 5
    assert result['sensitivity']['cells'][0][0]['status'] == 'invalid'
    assert result['scenarios']['base']['fair_value'] == pytest.approx(14)
    assert calculate(DCFInputs(**{**golden, 'wacc': .12}))['fair_value'] < 14


def test_units_and_cumulative_periods():
    assert normalize_number('1,234', '万元') == 12340000
    assert normalize_number('8', '%') == .08
    assert normalize_number(None, '元') is None
    assert normalize_number(0, '元') == 0
    assert ttm(80, 120, 60) == 140
    assert ttm(None, 120, 60) is None
    with pytest.raises(ValueError):
        normalize_number(1, 'unknown')


def test_eligibility():
    assert financial_eligibility('银行', '2026-06-30', [])[0] == 'unsupported_sector'
    assert financial_eligibility('制造', '2026-06-30', ['shares'])[0] == 'insufficient_data'
    assert financial_eligibility('制造', '2024-01-01', [], date(2026, 9, 19))[0] == 'stale_financials'
    assert financial_eligibility('制造', '2026-06-30', [], date(2026, 9, 19))[0] == 'eligible'
