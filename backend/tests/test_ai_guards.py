import pytest
from app.adapters.deepseek import ResearchNarrative,check_narrative


def narrative(text='基准估值 {{fair_value}}，结论 {{recommendation}}。'):
    return ResearchNarrative(summary=text,business_overview='',valuation_explanation='',
        supporting_factors=[],risks=[],news_insights=[],assumptions_to_review=[])


def test_numeric_and_label_control():
    assert check_narrative(narrative(),[])['summary']
    for bad in ('预计上涨 20%', '强烈推荐这家公司', '查看 https://invented.example', '{{unknown}}'):
        with pytest.raises(ValueError): check_narrative(narrative(bad),[])


def test_source_whitelist_and_factual_citations():
    for ids in ([],['invented']):
        value=narrative().model_dump()
        value['supporting_factors']=[{'text':'公司发布公告','kind':'fact','source_ids':ids}]
        with pytest.raises(ValueError):
            check_narrative(ResearchNarrative.model_validate(value),[{'id':'news-1'}])
