import asyncio
import copy
from app.db import Base, engine, save_snapshot
from app.services import data


def test_review_survives_quote_change_but_not_statement_revision(monkeypatch):
    Base.metadata.create_all(engine)
    raw={'income':[{'revenue':100}], 'balance':[], 'cashflow':[], 'snapshot_id':'raw-test', 'cache_status':'fresh'}
    quote={'snapshot_id':'quote-test-1'}
    async def company(self,symbol): return {'symbol':symbol}
    async def get_quote(self,symbol): return quote.copy()
    async def cached(*args): return copy.deepcopy(raw)
    monkeypatch.setattr(data.DataService,'company',company)
    monkeypatch.setattr(data.DataService,'quote',get_quote)
    monkeypatch.setattr(data,'cached',cached)
    monkeypatch.setattr(data,'normalize_reports',lambda *args:{'quality_status':'missing','inputs':{}})
    service=data.DataService('live')
    first=asyncio.run(service.financials('REVIEW-TEST'))
    reviewed={**first,'quality_status':'manual','inputs':{'debt':123}}
    reviewed.pop('snapshot_id')
    review_id=save_snapshot('financial','live','REVIEW-TEST',reviewed)
    quote['snapshot_id']='quote-test-2'
    reused=asyncio.run(service.financials('REVIEW-TEST'))
    assert reused['snapshot_id']==review_id and reused['inputs']['debt']==123
    raw['income'][0]['revenue']=101
    revised=asyncio.run(service.financials('REVIEW-TEST'))
    assert revised['snapshot_id']!=review_id and revised['quality_status']=='missing'
