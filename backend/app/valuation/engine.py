"""Deterministic rolling-year FCFF model. No networking or model calls."""
from __future__ import annotations

from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, model_validator

VERSION = 'fcff-rolling-1.0'
Ratio = Annotated[float, Field(allow_inf_nan=False)]
Five = Annotated[list[Ratio], Field(min_length=5, max_length=5)]


class DCFInputs(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    revenue_base: float = Field(gt=0)
    revenue_growth: Five
    ebit_margin: Five
    tax_rate: Five
    da_ratio: Five
    capex_ratio: Five
    nwc_ratio: Five
    nwc_base: float
    wacc: float = Field(gt=0, le=1)
    terminal_growth: float = Field(ge=0, le=0.04)
    terminal_margin: float = Field(gt=0, le=1)
    terminal_tax_rate: float = Field(ge=0, le=1)
    terminal_roic: float = Field(gt=0, le=1)
    excess_cash: float = Field(ge=0)
    non_operating_assets: float = Field(ge=0)
    interest_bearing_debt: float = Field(ge=0)
    minority_interest_value: float = Field(ge=0)
    preferred_equity_value: float = Field(ge=0)
    diluted_shares: float = Field(gt=0)
    current_price: float = Field(gt=0)

    @model_validator(mode='after')
    def validate_economics(self):
        if self.wacc - self.terminal_growth < 0.005 - 1e-12:
            raise ValueError('WACC 必须至少高于永续增长率 0.5 个百分点')
        if self.terminal_growth >= self.terminal_roic:
            raise ValueError('终值增长/ROIC 必须小于 1')
        limits = {
            'revenue_growth': (-1, 3), 'ebit_margin': (-1, 1),
            'tax_rate': (0, 1), 'da_ratio': (0, 1),
            'capex_ratio': (0, 2), 'nwc_ratio': (-2, 2),
        }
        for name, (lo, hi) in limits.items():
            for value in getattr(self, name):
                if value < lo or value > hi or (name == 'revenue_growth' and value == -1):
                    raise ValueError(f'{name} 超出支持范围 {lo} 至 {hi}')
        return self


def recommendation(fair_value: float | None, price: float | None,
                   eligible: bool = True) -> str:
    if not eligible or fair_value is None or price is None or fair_value <= 0 or price <= 0:
        return 'unavailable'
    difference = fair_value - price
    if abs(difference) <= 0.01 + 1e-12:
        return 'fair_value'
    return 'recommend' if difference > 0 else 'not_recommend'


def calculate(inputs: DCFInputs) -> dict:
    revenue, nwc_prev = inputs.revenue_base, inputs.nwc_base
    years = []
    for i in range(5):
        revenue *= 1 + inputs.revenue_growth[i]
        ebit = revenue * inputs.ebit_margin[i]
        tax = max(ebit, 0) * inputs.tax_rate[i]
        nopat = ebit - tax
        da, capex = revenue * inputs.da_ratio[i], revenue * inputs.capex_ratio[i]
        nwc = revenue * inputs.nwc_ratio[i]
        delta_nwc = nwc - nwc_prev
        fcff = nopat + da - capex - delta_nwc
        discount_factor = (1 + inputs.wacc) ** (i + 1)
        years.append(dict(year=i + 1, label=f'未来 {(i+1)*12} 个月', revenue=revenue,
                          ebit=ebit, tax=tax, nopat=nopat, da=da, capex=capex,
                          nwc=nwc, delta_nwc=delta_nwc, fcff=fcff,
                          discount_factor=discount_factor, pv_fcff=fcff / discount_factor))
        nwc_prev = nwc
    revenue6 = revenue * (1 + inputs.terminal_growth)
    nopat6 = revenue6 * inputs.terminal_margin * (1 - inputs.terminal_tax_rate)
    reinvestment = inputs.terminal_growth / inputs.terminal_roic
    fcff6 = nopat6 * (1 - reinvestment)
    terminal_value = fcff6 / (inputs.wacc - inputs.terminal_growth)
    pv_terminal = terminal_value / (1 + inputs.wacc) ** 5
    pv_flows = sum(y['pv_fcff'] for y in years)
    ev = pv_flows + pv_terminal
    equity = (ev + inputs.excess_cash + inputs.non_operating_assets
              - inputs.interest_bearing_debt - inputs.minority_interest_value
              - inputs.preferred_equity_value)
    fair = equity / inputs.diluted_shares
    valid = equity > 0 and ev > 0
    weight = pv_terminal / ev if ev > 0 else None
    warnings = []
    if weight is not None and weight > .75:
        warnings.append('估值对长期假设较敏感：终值现值占比超过 75%')
    if abs(fcff6 - years[-1]['fcff']) > max(abs(years[-1]['fcff']) * .25, 1):
        warnings.append('终值现金流与第 5 年存在明显变化，请复核稳态利润和再投资假设')
    if not valid:
        warnings.append('股权价值或企业经营价值非正，当前模型需人工复核')
    return dict(model_version=VERSION, status='valid' if valid else 'requires_manual_model',
                years=years, terminal=dict(revenue=revenue6, nopat=nopat6,
                reinvestment_rate=reinvestment, fcff=fcff6, value=terminal_value,
                present_value=pv_terminal, weight=weight),
                operating_ev=ev, equity_value=equity, pv_flows=pv_flows,
                fair_value=fair if valid else None, raw_fair_value=fair,
                current_price=inputs.current_price,
                valuation_gap=fair / inputs.current_price - 1 if valid else None,
                discount_to_value=1 - inputs.current_price / fair if valid else None,
                recommendation=recommendation(fair, inputs.current_price, valid),
                warnings=warnings)


def calculate_suite(inputs: DCFInputs) -> dict:
    base = calculate(inputs)
    scenarios = {}
    for name, sign in [('bear', -1), ('base', 0), ('bull', 1)]:
        data = inputs.model_dump()
        data['revenue_growth'] = [v + sign * .02 for v in data['revenue_growth']]
        data['ebit_margin'] = [v + sign * .01 for v in data['ebit_margin']]
        data['wacc'] -= sign * .01
        try:
            scenarios[name] = {'inputs': data, **calculate(DCFInputs(**data))}
        except ValueError as exc:
            scenarios[name] = {'status': 'invalid', 'fair_value': None, 'reason': str(exc)}
    waccs = [round(inputs.wacc + v, 8) for v in [-.02, -.01, 0, .01, .02]]
    growths = [round(inputs.terminal_growth + v, 8) for v in [-.01, -.005, 0, .005, .01]]
    cells = []
    for wacc in waccs:
        row = []
        for growth in growths:
            try:
                case = DCFInputs(**{**inputs.model_dump(), 'wacc': wacc, 'terminal_growth': growth})
                result = calculate(case)
                row.append({'wacc': wacc, 'growth': growth, 'fair_value': result['fair_value'],
                            'status': result['status']})
            except ValueError:
                row.append({'wacc': wacc, 'growth': growth, 'fair_value': None, 'status': 'invalid'})
        cells.append(row)
    return {**base, 'inputs': inputs.model_dump(), 'scenarios': scenarios,
            'sensitivity': {'waccs': waccs, 'growths': growths, 'cells': cells}}
