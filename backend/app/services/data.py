import asyncio
from datetime import datetime, timezone
import hashlib
import json
import time
from sqlalchemy import select
from app.adapters import demo, live
from app.db import Session, Snapshot, CacheEpoch, save_snapshot
from app.errors import AppError
from app.valuation.financials import normalize_reports
from app.services.market_clock import quote_quality,session_state

_locks={}
_refresh_failures={}


async def cached(kind,mode,symbol,ttl,producer):
    key=(kind,mode,symbol)
    lock=_locks.setdefault(key,asyncio.Lock())
    async with lock:
        with Session() as session:
            epoch=session.get(CacheEpoch,mode)
            snapshot=session.scalar(select(Snapshot).where(Snapshot.kind==kind,Snapshot.mode==mode,Snapshot.symbol==symbol).order_by(Snapshot.created_at.desc()).limit(1))
            if snapshot:
                created=snapshot.created_at.replace(tzinfo=timezone.utc)
                invalidated=epoch and snapshot.created_at.replace(tzinfo=timezone.utc)<=epoch.invalidated_at.replace(tzinfo=timezone.utc)
                if not invalidated and (datetime.now(timezone.utc)-created).total_seconds()<ttl:
                    return {**snapshot.payload,'snapshot_id':snapshot.id,'cache_status':'cached'}
        failure=_refresh_failures.get(key)
        if failure and time.monotonic()<failure[0]:
            if snapshot: return {**snapshot.payload,'snapshot_id':snapshot.id,'cache_status':'stale'}
            raise failure[1]
        try:
            value=await asyncio.wait_for(producer(),timeout=45)
            _refresh_failures.pop(key,None)
        except (AppError,TimeoutError) as exc:
            error=exc if isinstance(exc,AppError) else AppError('source_timeout','数据源读取超时，请稍后重试',retryable=True)
            _refresh_failures[key]=(time.monotonic()+30,error)
            if snapshot:
                return {**snapshot.payload,'snapshot_id':snapshot.id,'cache_status':'stale'}
            raise error
        sid=save_snapshot(kind,mode,symbol,value)
        return {**value,'snapshot_id':sid,'cache_status':'fresh'}


class DataService:
    def __init__(self,mode):
        if mode not in ('demo','live'):
            raise AppError('invalid_mode','未知数据模式',422)
        self.mode=mode

    async def companies(self,query=''):
        if self.mode=='demo':
            items=[demo.company(c['symbol']) for c in demo.COMPANIES]
        else:
            async def produce():
                return {'items':await live.universe()}
            items=(await cached('universe','live','ALL',86400,produce))['items']
        q=query.casefold().strip()
        return [c for c in items if not q or q in c['name'].casefold() or q in c['symbol'].casefold() or q in c.get('full_name','').casefold()]

    async def company(self,symbol):
        results=await self.companies(symbol)
        result=next((c for c in results if c['symbol']==symbol),None)
        if not result:
            raise AppError('company_not_found','该股票不在当前数据模式的沪市 A 股范围内',404)
        return result

    async def quote(self,symbol):
        c=await self.company(symbol)
        async def produce():
            if self.mode=='demo':
                return dict(symbol=symbol,price=c['price'],change_pct=c['change_pct'],market_cap=c['price']*1e9,
                    market_as_of=demo.AS_OF,fetched_at=demo.AS_OF,source=c['source'],source_url=None,
                    currency='CNY',is_demo=True,adjustment='none',quality_status='demo')
            return await live.quote(symbol)
        ttl=60 if session_state()=='trading' else 900
        result=await cached('quote',self.mode,symbol,ttl if self.mode=='live' else 86400,produce)
        if self.mode=='live': result.update(quote_quality(result.get('market_as_of')))
        else: result.update(market_state='demo',freshness='demo',valid_for_valuation=True)
        return result

    async def overview(self,symbol):
        c=await self.company(symbol)
        try:
            quote=await self.quote(symbol)
            error=None
        except AppError as exc:
            quote,error=None,exc.as_dict()
        return {'company':c,'quote':quote,'quote_error':error,'mode':self.mode}

    async def news(self,symbol):
        company=await self.company(symbol)
        async def produce():
            items=demo.news(symbol) if self.mode=='demo' else await live.ak_news(symbol)
            for item in items:
                item['association']='company' if company['name'] in item['title']+' '+item['content'] or self.mode=='demo' else 'related'
                item['company']=company['name']
            return {'items':items}
        result=await cached('news',self.mode,symbol,900,produce)
        for item in result['items']:
            # Same article can appear in different retrievals. Preserve immutable
            # evidence content with an id independent of the retrieval timestamp.
            article={**item}
            sid='a_'+hashlib.sha256((self.mode+item['id']+item['content']).encode()).hexdigest()[:28]
            article['id']=sid
            with Session() as session:
                existing=session.get(Snapshot,sid)
            if not existing:
                save_snapshot('article',self.mode,symbol,article,sid)
            item['id']=sid
        return result

    async def prices(self,symbol,range_name):
        await self.company(symbol)
        async def produce():
            items=demo.prices(symbol,range_name) if self.mode=='demo' else await live.prices(symbol,range_name)
            return {'items':items,'adjustment':'none','source':'虚构演示' if self.mode=='demo' else '腾讯证券',
                    'is_demo':self.mode=='demo'}
        return await cached('prices',self.mode,symbol+':'+range_name,3600,produce)

    async def financials(self,symbol,include_corrections=True):
        c=await self.company(symbol)
        if self.mode=='demo':
            async def produce(): return demo.financials(symbol)
            return await cached('financial','demo',symbol,86400,produce)
        async def raw_producer(): return await live.financial_reports(symbol)
        raw=await cached('financial_raw','live',symbol,86400,raw_producer)
        quote=await self.quote(symbol)
        value=normalize_reports(symbol,raw,quote,c)
        value['raw_snapshot_id']=raw['snapshot_id']
        value['quote_snapshot_id']=quote['snapshot_id']
        value['cache_status']=raw['cache_status']
        # Corrections attach to the financial statements, not to a moving quote.
        # A new statement or revision invalidates the review automatically.
        statement_body={k:raw[k] for k in ('income','balance','cashflow')}
        value['statement_fingerprint']=hashlib.sha256(json.dumps(statement_body,sort_keys=True).encode()).hexdigest()
        if include_corrections:
            with Session() as session:
                reviewed=session.scalars(select(Snapshot).where(Snapshot.kind=='financial',Snapshot.mode==self.mode,Snapshot.symbol==symbol).order_by(Snapshot.created_at.desc())).all()
                match=next((r for r in reviewed if r.payload.get('quality_status')=='manual' and r.payload.get('statement_fingerprint')==value['statement_fingerprint']),None)
                if match:
                    return {**match.payload,'snapshot_id':match.id,'cache_status':raw['cache_status']}
        body=json.dumps(value,sort_keys=True,ensure_ascii=False)
        sid='financial_'+hashlib.sha256(body.encode()).hexdigest()[:24]
        save_snapshot('financial','live',symbol,value,sid)
        return {**value,'snapshot_id':sid}
