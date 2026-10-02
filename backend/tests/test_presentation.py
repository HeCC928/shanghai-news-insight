import asyncio
import uuid
from app.db import Base,engine,save_snapshot
from app.services import data
from app.errors import AppError


def test_valuation_explanation_accepts_full_lists_and_checks_every_item():
    from app.adapters.deepseek import DeepSeek,ValuationExplanation
    import pytest
    model=DeepSeek()
    content={'text':'每股估值 {{fair_value}}','drivers':['经营驱动']*4,'risks':['假设风险']*4,'checks':['核查财报']*4}
    async def structured(schema,system,context,validator):
        return validator(ValuationExplanation(**content))
    model.structured=structured
    result=asyncio.run(model.explain_valuation({},''))
    assert len(result['checks'])==4
    content['checks'][-1]='编造数值 999'
    with pytest.raises(ValueError): asyncio.run(model.explain_valuation({},''))


def test_failed_refresh_is_shared_by_waiters():
    Base.metadata.create_all(engine)
    symbol='cooldown-'+uuid.uuid4().hex
    save_snapshot('quote','live',symbol,{'price':123})
    calls=[]
    async def producer():
        calls.append(1)
        raise AppError('source_failed','测试数据源不可用')
    async def scenario():
        return await asyncio.gather(*(data.cached('quote','live',symbol,-1,producer) for _ in range(5)))
    rows=asyncio.run(scenario())
    assert len(calls)==1
    assert all(row['cache_status']=='stale' and row['price']==123 for row in rows)


def test_snapshot_calculation_never_fetches_live_or_trusts_client_quote():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        original=client.post('/api/valuations',json={'symbol':'DEMO:HCM'}).json()
        pid='presentation_'+uuid.uuid4().hex
        save_snapshot('presentation','demo','DEMO:HCM',{'id':pid,'report':{'valuation':original,'quote':original['quote']}},pid)
        response=client.post('/api/presentations/'+pid+'/calculate?mode=demo',json={**original['inputs'],'current_price':.01,'wacc':.15})
        assert response.status_code==200,response.text
        result=response.json()
        assert result['historical_snapshot'] is True
        assert result['current_price']==original['current_price']
        assert result['fair_value']<original['fair_value']
        assert client.get('/api/presentations/'+pid+'?mode=live').status_code==404
        assert client.get('/api/presentations/latest?mode=demo&symbol=DEMO:HCM').json()['id']==pid
        presets=client.get('/api/prompt-presets').json()['items']
        assert len(presets)==9 and len({p['id'] for p in presets})==9
