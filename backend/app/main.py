from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import csv
import io
import json
from typing import Annotated, Literal
from fastapi import FastAPI, Depends, Header, Query, Request, UploadFile, File
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from app.config import settings
from app.db import Base,engine,Session,Snapshot,WatchlistItem,CacheEpoch,transaction,load_snapshot,save_snapshot,uid
from app.errors import AppError
from app.services import jobs,prompts
from app.services.data import DataService
from app.services.research import build_valuation,save_valuation
from app.services.exports import report_markdown,valuation_csv,csv_safe
from app.valuation.engine import DCFInputs,calculate_suite
from app.adapters import demo
from app.adapters.deepseek import DeepSeek

Mode=Literal['demo','live']


@asynccontextmanager
async def lifespan(app):
    from alembic import command
    from alembic.config import Config
    from app.config import ROOT
    command.upgrade(Config(str(ROOT/'backend/alembic.ini')),'head')
    with transaction() as session:
        seeded=session.get(Snapshot,'installation-v1')
        if not seeded:
            session.add_all(WatchlistItem(mode='demo',symbol=c['symbol']) for c in demo.COMPANIES[:3])
            session.add(Snapshot(id='installation-v1',kind='installation',mode='demo',symbol='',payload={'version':1}))
    await jobs.start()
    yield
    await jobs.stop()


app=FastAPI(title='沪讯 Research API',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=['http://127.0.0.1:3000','http://localhost:3000'],
                   allow_methods=['GET','POST','DELETE'],allow_headers=['Content-Type','Idempotency-Key'])


@app.exception_handler(AppError)
async def app_error(request,exc):
    return JSONResponse(status_code=exc.status,content={**exc.as_dict(),'request_id':uid('req_')})


@app.exception_handler(RequestValidationError)
async def validation_error(request,exc):
    # Do not echo input values (possibly credentials or large article text).
    fields={'.'.join(map(str,e['loc'])):e['msg'] for e in exc.errors()}
    return JSONResponse(status_code=422,content={'code':'validation_error','message':'输入校验未通过','field_errors':fields,'retryable':False,'request_id':uid('req_')})


@app.get('/api/health')
def health():
    cfg=settings()
    with Session() as session:
        session.execute(select(1))
    return {'status':'ok','database':'connected','model_configured':cfg.key_configured,
            'model_id':cfg.deepseek_model,'default_mode':cfg.data_mode,'time':datetime.now(timezone.utc).isoformat()}


@app.post('/api/settings/test-model')
async def test_model():
    response=await DeepSeek().chat([{'role':'user','content':'Output JSON {"connected":true} only.'}],
                                   response_format={'type':'json_object'},max_tokens=32)
    return {'connected':json.loads(response['content']).get('connected') is True,'model_id':settings().deepseek_model}


@app.get('/api/companies')
async def companies(query:str='',mode:Mode='demo'):
    return {'items':(await DataService(mode).companies(query))[:50]}


@app.get('/api/companies/{symbol}/overview')
async def overview(symbol:str,mode:Mode='demo'):
    return await DataService(mode).overview(symbol)


@app.get('/api/companies/{symbol}/prices')
async def prices(symbol:str,range:Literal['1M','3M','1Y']='1M',mode:Mode='demo'):
    return await DataService(mode).prices(symbol,range)


@app.get('/api/companies/{symbol}/news')
async def news(symbol:str,mode:Mode='demo',query:str='',days:int=Query(30,ge=1,le=365),category:str='',scope:Literal['company','watchlist']='company'):
    symbols=[symbol]
    if scope=='watchlist':
        with Session() as session:
            symbols=list(session.scalars(select(WatchlistItem.symbol).where(WatchlistItem.mode==mode)))
    results=await asyncio.gather(*(DataService(mode).news(s) for s in symbols),return_exceptions=True)
    seen=set(); rows=[]; errors=[]
    anchor=datetime(2026,9,19,tzinfo=timezone.utc) if mode=='demo' else datetime.now(timezone.utc)
    for result in results:
        if isinstance(result,Exception):
            errors.append(result.as_dict() if isinstance(result,AppError) else {'message':'新闻源读取失败'})
            continue
        for item in result['items']:
            if item['id'] in seen: continue
            seen.add(item['id'])
            if query and query.casefold() not in (item['title']+' '+item['content']).casefold(): continue
            if category and item['category']!=category: continue
            try:
                timestamp=datetime.fromisoformat(item['published_at'].replace('Z','+00:00'))
                if (anchor-timestamp).days>days: continue
            except (TypeError,ValueError): pass
            rows.append(item)
    rows.sort(key=lambda row:row.get('published_at') or '',reverse=True)
    return {'items':rows,'errors':errors}


@app.get('/api/articles/{article_id}')
def article(article_id:str,mode:Mode='demo'):
    value=load_snapshot(article_id,mode,'article')
    if not value: raise AppError('not_found','文章不存在',404)
    return value


@app.post('/api/articles/{article_id}/analyze',status_code=202)
def analyze_article(article_id:str,mode:Mode='demo',idempotency_key:Annotated[str|None,Header()]=None):
    if not load_snapshot(article_id,mode,'article'): raise AppError('not_found','文章不存在',404)
    return jobs.submit('article',mode,'',{'article_id':article_id},idempotency_key or uid())


@app.get('/api/companies/{symbol}/financials')
async def financials(symbol:str,mode:Mode='demo'):
    return await DataService(mode).financials(symbol)


class ManualField(BaseModel):
    value: float | list[float]
    source_ref: str=Field(min_length=3,max_length=1000)
    note: str=Field(min_length=3,max_length=1000)


class ManualCorrection(BaseModel):
    snapshot_id:str
    fields:dict[str,ManualField]=Field(min_length=1)


@app.post('/api/companies/{symbol}/financials/corrections')
async def correct_financial(symbol:str,body:ManualCorrection,mode:Mode='demo'):
    original=load_snapshot(body.snapshot_id,mode,'financial')
    if not original or original.get('symbol')!=symbol: raise AppError('not_found','财务快照不存在',404)
    if original['status'] in ('unsupported_sector','stale_financials'):
        raise AppError('unsupported_correction','不能通过手动输入绕过行业或过期限制',422)
    value=json.loads(json.dumps(original)); value['inputs']=value.get('inputs') or {}
    for field,item in body.fields.items():
        if field not in DCFInputs.model_fields or field=='current_price':
            raise AppError('invalid_field','不允许修改该字段',422)
        value['inputs'][field]=item.value
        value['provenance'][field]={'value':item.value,'origin':'manual','unit':value['provenance'].get(field,{}).get('unit','需核实'), 'source_ref':item.source_ref,'note':item.note}
    try: DCFInputs(**value['inputs'])
    except ValueError as exc: raise AppError('incomplete_correction','补充后仍未通过 DCF 输入校验',422) from exc
    value.update(status='eligible',reason='已手动补充；报告保留来源与假设',missing_fields=[],parent_snapshot_id=body.snapshot_id,quality_status='manual',reviewed_at=datetime.now(timezone.utc).isoformat())
    value['assumptions']=[p['note'] for p in value['provenance'].values() if p['origin'] in ('assumption','manual')]
    sid=save_snapshot('financial',mode,symbol,value)
    return {**value,'snapshot_id':sid}


class ValuationRequest(BaseModel):
    symbol:str
    inputs:DCFInputs|None=None
    financial_snapshot_id:str|None=None
    title:str=Field(default='自定义情景',max_length=60)


async def valuation_request(body,mode):
    financial=None
    if body.financial_snapshot_id:
        financial=load_snapshot(body.financial_snapshot_id,mode,'financial')
        if not financial or financial.get('symbol')!=body.symbol: raise AppError('not_found','财务快照与公司不匹配',404)
        financial={**financial,'snapshot_id':body.financial_snapshot_id}
    result=await build_valuation(mode,body.symbol,financial,body.inputs.model_dump() if body.inputs else None,body.title)
    if body.inputs:
        for key,value in body.inputs.model_dump().items():
            prior=result['provenance'].get(key,{})
            if prior.get('value')!=value and key!='current_price':
                result['provenance'][key]={**prior,'value':value,'origin':'manual','note':'用户情景假设；原来源仅用于对照','source_ref':'用户在估值工作台输入'}
    return result


@app.post('/api/valuations/calculate')
async def preview_valuation(body:ValuationRequest,mode:Mode='demo'):
    return await valuation_request(body,mode)


@app.post('/api/valuations')
async def persist_valuation(body:ValuationRequest,mode:Mode='demo'):
    return save_valuation(await valuation_request(body,mode))


@app.get('/api/valuations')
def valuations(symbol:str,mode:Mode='demo'):
    with Session() as session:
        rows=session.scalars(select(Snapshot).where(Snapshot.kind=='valuation',Snapshot.mode==mode,Snapshot.symbol==symbol).order_by(Snapshot.created_at.desc()).limit(20))
        return {'items':[r.payload for r in rows]}


@app.get('/api/valuations/{valuation_id}')
def valuation(valuation_id:str,mode:Mode='demo'):
    value=load_snapshot(valuation_id,mode,'valuation')
    if not value: raise AppError('not_found','估值版本不存在',404)
    return value


@app.post('/api/valuations/{valuation_id}/explain',status_code=202)
def explain(valuation_id:str,mode:Mode='demo',idempotency_key:Annotated[str|None,Header()]=None):
    valuation(valuation_id,mode)
    return jobs.submit('explain',mode,'',{'valuation_id':valuation_id},idempotency_key or uid())


class ResearchRequest(BaseModel):
    symbol:str


@app.post('/api/valuations/{valuation_id}/suggestions',status_code=202)
def suggestions(valuation_id:str,mode:Mode='demo',idempotency_key:Annotated[str|None,Header()]=None):
    valuation(valuation_id,mode)
    return jobs.submit('suggest_assumptions',mode,'',{'valuation_id':valuation_id},idempotency_key or uid())


@app.post('/api/research-runs',status_code=202)
async def create_research(body:ResearchRequest,mode:Mode='demo',idempotency_key:Annotated[str|None,Header()]=None):
    await DataService(mode).company(body.symbol)
    return jobs.submit('research',mode,body.symbol,body.model_dump(),idempotency_key or uid())


@app.get('/api/research-runs')
def research_runs(symbol:str,mode:Mode='demo'):
    with Session() as session:
        rows=session.scalars(select(Snapshot).where(Snapshot.kind=='report',Snapshot.mode==mode,Snapshot.symbol==symbol).order_by(Snapshot.created_at.desc()).limit(10))
        return {'items':[r.payload for r in rows]}


@app.get('/api/research-runs/{report_id}')
def report(report_id:str,mode:Mode='demo'):
    value=load_snapshot(report_id,mode,'report')
    if not value: raise AppError('not_found','研究报告不存在',404)
    return value


class QuestionRequest(BaseModel):
    question:str=Field(min_length=1,max_length=2000)


@app.post('/api/research-runs/{report_id}/questions',status_code=202)
def questions(report_id:str,body:QuestionRequest,mode:Mode='demo',idempotency_key:Annotated[str|None,Header()]=None):
    value=report(report_id,mode)
    return jobs.submit('question',mode,value['symbol'],{'report_id':report_id,'question':body.question},idempotency_key or uid())


@app.get('/api/jobs/{job_id}')
def job(job_id:str,mode:Mode='demo'):
    return jobs.get_job(job_id,mode)


@app.post('/api/jobs/{job_id}/cancel')
def cancel_job(job_id:str,mode:Mode='demo'):
    return jobs.cancel(job_id,mode)


@app.get('/api/jobs/{job_id}/events')
async def events(job_id:str,request:Request,mode:Mode='demo'):
    jobs.get_job(job_id,mode)
    async def stream():
        previous=''
        while not await request.is_disconnected():
            current=jobs.get_job(job_id,mode)
            value=json.dumps(current,ensure_ascii=False)
            if value!=previous:
                yield 'data: '+value+'\n\n'; previous=value
            if current['status'] not in ('queued','running'): break
            await asyncio.sleep(.5)
    return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})


@app.get('/api/watchlist')
async def watchlist(mode:Mode='demo'):
    with Session() as session:
        symbols=list(session.scalars(select(WatchlistItem.symbol).where(WatchlistItem.mode==mode).order_by(WatchlistItem.created_at)))
    results=await asyncio.gather(*(DataService(mode).overview(s) for s in symbols),return_exceptions=True)
    return {'items':[r for r in results if not isinstance(r,Exception)],'symbols':symbols}


@app.post('/api/watchlist')
async def add_watchlist(body:ResearchRequest,mode:Mode='demo'):
    await DataService(mode).company(body.symbol)
    with transaction() as session:
        if not session.scalar(select(WatchlistItem).where(WatchlistItem.mode==mode,WatchlistItem.symbol==body.symbol)):
            session.add(WatchlistItem(mode=mode,symbol=body.symbol))
    return {'added':True}


@app.delete('/api/watchlist/{symbol}')
def remove_watchlist(symbol:str,mode:Mode='demo'):
    with transaction() as session:
        session.execute(delete(WatchlistItem).where(WatchlistItem.mode==mode,WatchlistItem.symbol==symbol))
    return {'removed':True}


class PromptRequest(BaseModel):
    content:str=Field(min_length=1,max_length=6000)


@app.get('/api/prompts')
def get_prompts():
    return {'items':[prompts.latest(k) for k in prompts.DEFAULTS]}


@app.get('/api/prompt-presets')
def prompt_presets():
    return {'items':prompts.PRESETS}


@app.get('/api/presentations/latest')
def presentation_latest(symbol:str='600519.SH',mode:Mode='live'):
    with Session() as session:
        row=session.scalar(select(Snapshot).where(Snapshot.kind=='presentation',Snapshot.mode==mode,Snapshot.symbol==symbol).order_by(Snapshot.created_at.desc()).limit(1))
        if not row: raise AppError('presentation_missing','还没有准备好的演示快照',404)
        return row.payload


@app.get('/api/presentations/{presentation_id}')
def presentation_snapshot(presentation_id:str,mode:Mode='live'):
    value=load_snapshot(presentation_id,mode,'presentation')
    if not value: raise AppError('not_found','演示快照不存在',404)
    return value


@app.post('/api/presentations/{presentation_id}/calculate')
def presentation_calculate(presentation_id:str,body:DCFInputs,mode:Mode='live'):
    pack=presentation_snapshot(presentation_id,mode)
    # Presentation calculations intentionally use its historical quote, never a live feed.
    inputs=body.model_dump()
    inputs['current_price']=pack['report']['valuation']['inputs']['current_price']
    return {**calculate_suite(DCFInputs(**inputs)),'historical_snapshot':True,'as_of':pack['report']['quote']['market_as_of']}


@app.get('/api/prompts/{kind}/versions')
def prompt_versions(kind:str): return {'items':prompts.versions(kind)}


@app.post('/api/prompts/{kind}')
def save_prompt(kind:str,body:PromptRequest): return prompts.save(kind,body.content)


@app.post('/api/prompts/{kind}/reset')
def reset_prompt(kind:str):
    prompts.latest(kind)
    return prompts.save(kind,prompts.DEFAULTS[kind])


class ImportedArticle(BaseModel):
    title:str=Field(min_length=1,max_length=300)
    content:str=Field(min_length=1,max_length=20000)
    source:str=Field(default='用户提供',max_length=300)
    published_at:str|None=None


class BatchRequest(BaseModel):
    articles:list[ImportedArticle]=Field(min_length=1,max_length=20)


@app.post('/api/news-batches',status_code=202)
def news_batch(body:BatchRequest,mode:Mode='demo',idempotency_key:Annotated[str|None,Header()]=None):
    return jobs.submit('news_batch',mode,'',body.model_dump(),idempotency_key or uid())


@app.post('/api/news-batches/import',status_code=202)
async def import_csv(file:UploadFile=File(...),mode:Mode='demo'):
    content=await file.read(2*1024*1024+1)
    if len(content)>2*1024*1024: raise AppError('file_too_large','文件不能超过 2MB',422)
    try:
        reader=csv.DictReader(io.StringIO(content.decode('utf-8-sig')))
        items=[]
        for row in reader:
            if len(items)>=20: raise ValueError('Too many rows')
            items.append(ImportedArticle(title=row.get('title') or row.get('标题') or '',content=row.get('content') or row.get('内容') or '',source=row.get('source') or row.get('来源') or '用户提供',published_at=row.get('published_at') or row.get('时间')))
        body=BatchRequest(articles=items)
    except (ValueError,UnicodeDecodeError) as exc: raise AppError('invalid_csv','CSV 需为 UTF-8，包含标题和内容，最多 20 篇',422) from exc
    return jobs.submit('news_batch',mode,'',body.model_dump(),uid())


@app.get('/api/research-runs/{report_id}/export')
def export_report(report_id:str,mode:Mode='demo',format:Literal['md']='md'):
    return Response(report_markdown(report(report_id,mode)),media_type='text/markdown; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="{report_id}.md"'})


@app.get('/api/valuations/{valuation_id}/export')
def export_valuation(valuation_id:str,mode:Mode='demo',format:Literal['csv']='csv'):
    return Response(valuation_csv(valuation(valuation_id,mode)),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="{valuation_id}.csv"'})


@app.get('/api/news-batches/{job_id}/export')
def export_batch(job_id:str,mode:Mode='demo'):
    value=jobs.get_job(job_id,mode)
    if value['kind']!='news_batch' or not value['result']: raise AppError('not_ready','批量分析尚未产生结果',409)
    stream=io.StringIO(); writer=csv.writer(stream)
    writer.writerow(['title','status','summary','sentiment','source','mode'])
    for row in value['result']['items']:
        result=row.get('result',{})
        writer.writerow([csv_safe(row['title']),row['status'],csv_safe(result.get('summary','')),result.get('sentiment',''),'用户提供',mode])
    return Response('\ufeff'+stream.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="{job_id}.csv"'})


@app.post('/api/news-batches/{job_id}/retry/{index}',status_code=202)
def retry_batch_item(job_id:str,index:int,mode:Mode='demo',idempotency_key:Annotated[str|None,Header()]=None):
    from app.db import Job
    with Session() as session:
        parent=session.get(Job,job_id)
        if not parent or parent.mode!=mode or parent.kind!='news_batch': raise AppError('not_found','批量任务不存在',404)
        articles=parent.payload['articles']
        if index<0 or index>=len(articles): raise AppError('invalid_index','文章序号无效',422)
        if parent.status in ('queued','running'): raise AppError('not_ready','请等待批量任务结束后重试',409)
        return jobs.submit('news_batch',mode,'',{'articles':[articles[index]]},idempotency_key or uid())


@app.post('/api/settings/clear-cache')
def clear_cache(mode:Mode='demo'):
    # Invalidate cache selection without changing historical snapshot identities.
    with transaction() as session:
        epoch=session.get(CacheEpoch,mode)
        if epoch: epoch.invalidated_at=datetime.now(timezone.utc)
        else: session.add(CacheEpoch(mode=mode))
    return {'cleared':True,'reports_preserved':True}
