"""Explicit units and period semantics; missing is never a financial zero."""
from __future__ import annotations
import math
from datetime import date
from statistics import median

UNIT_FACTORS = {'元': 1, '万元': 10000, '亿元': 100000000,
                '股': 1, '万股': 10000, '亿股': 100000000, 'ratio': 1, '%': .01}


def normalize_number(value, unit: str) -> float | None:
    if value is None or value in ('', '--', '-', 'N/A'):
        return None
    if isinstance(value, bool):
        raise ValueError('布尔值不是财务数字')
    if unit not in UNIT_FACTORS:
        raise ValueError(f'未知单位 {unit}')
    number = float(str(value).replace(',', ''))
    if not math.isfinite(number):
        return None
    return number * UNIT_FACTORS[unit]


def ttm(current_ytd: float | None, previous_annual: float | None,
        previous_same_ytd: float | None) -> float | None:
    if any(v is None for v in (current_ytd, previous_annual, previous_same_ytd)):
        return None
    return current_ytd + previous_annual - previous_same_ytd


def median_valid(values):
    available = [v for v in values if v is not None and math.isfinite(v)]
    return median(available) if available else None


def financial_eligibility(sector: str, period_end: str | None,
                          missing_fields: list[str], as_of: date | None = None,
                          persistent_losses: bool = False) -> tuple[str, str]:
    if any(term in sector for term in ('银行', '保险', '证券', '券商', '金融')):
        return 'unsupported_sector', '金融企业不适用当前非金融 FCFF 模型'
    if missing_fields:
        return 'insufficient_data', '待补充：' + '、'.join(missing_fields)
    if not period_end:
        return 'insufficient_data', '缺少财务报告期'
    end, today = date.fromisoformat(period_end[:10]), as_of or date.today()
    months = (today.year - end.year) * 12 + today.month - end.month
    if months > 18 or (months == 18 and today.day > end.day):
        return 'stale_financials', '最新财务数据距估值日超过 18 个月'
    if persistent_losses:
        return 'requires_manual_model', '持续经营亏损，需要人工建立正常化模型'
    return 'eligible', '数据支持当前模型；仍需检查所示假设'
