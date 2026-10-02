from __future__ import annotations
import asyncio
from datetime import datetime,timezone
import hashlib
import json
from sqlalchemy import select
from app.config import settings
from app.db import Session, Job, transaction, load_snapshot, save_snapshot
from app.errors import AppError
from app.services import research as research_service
from app.services.prompts import latest
from app.adapters.deepseek import DeepSeek

workers=[]
queue=asyncio.Queue()


def serialize(job):
    return {key:getattr(job,key) for key in ('id','kind','mode','symbol','status','step','result','error')}


def get_job(job_id,mode):
    with Session() as session:
        job=session.get(Job,job_id)
        if not job or job.mode!=mode:
            raise AppError('not_found','任务不存在',404)
        return serialize(job)


def submit(kind,mode,symbol,payload,key):
    unique=hashlib.sha256((mode+kind+key).encode()).hexdigest()
    with transaction() as session:
        old=session.scalar(select(Job).where(Job.idempotency_key==unique))
        if old:
            if old.payload!=payload or old.symbol!=symbol:
                raise AppError('idempotency_conflict','重复请求标识对应不同内容',409)
            return serialize(old)
        job=Job(kind=kind,mode=mode,symbol=symbol,payload=payload,idempotency_key=unique)
        session.add(job); session.flush()
        result=serialize(job)
    queue.put_nowait(result['id'])
    return result


def cancel(job_id,mode):
    with transaction() as session:
        job=session.get(Job,job_id)
        if not job or job.mode!=mode: raise AppError('not_found','任务不存在',404)
        if job.status in ('queued','running'):
            job.status='cancelled'; job.step='已取消，丢弃后续结果'
        return serialize(job)


async def analyze_one(mode,article,preference):
    identity=json.dumps({'mode':mode,'title':article['title'],'content':article['content'],'model':settings().deepseek_model,'prompt':preference},sort_keys=True,ensure_ascii=False)
    cache_id='analysis_'+hashlib.sha256(identity.encode()).hexdigest()
    cached=load_snapshot(cache_id,mode,'article_analysis')
    if cached: return {**cached,'cache_hit':True}
    if mode=='demo':
        content=article['content']
        evidence=content.split('。')[0]+('。' if '。' in content else '')
        return {'summary':content[:160],'event':'演示提取','sentiment':'不确定','evidence':[{'text':evidence,'start':0,'end':len(evidence)}] if evidence else [],'limitations':'预制演示逻辑，未调用模型','model_id':'demo-prepared-content'}
    model=DeepSeek()
    result=await model.analyze_news(article,preference['content'])
    result['model_id']=settings().deepseek_model
    result['prompt_version']=preference['version']
    result['usage']=model.last_usage
    save_snapshot('article_analysis',mode,article.get('symbol',''),result,cache_id)
    return result


async def execute(job,step):
    payload,mode=job['payload'],job['mode']
    if job['kind']=='research':
        return await research_service.research(mode,job['symbol'],step)
    if job['kind']=='explain':
        await step('解释所选估值版本')
        return await research_service.explain(mode,payload['valuation_id'])
    if job['kind']=='suggest_assumptions':
        await step('提出待用户审阅的假设建议')
        return await research_service.suggest_assumptions(mode,payload['valuation_id'])
    if job['kind']=='question':
        await step('核查研究上下文并回答')
        return await research_service.question(mode,payload['report_id'],payload['question'])
    if job['kind']=='article':
        article=load_snapshot(payload['article_id'],mode,'article')
        if not article: raise AppError('not_found','文章不存在',404)
        await step('提取新闻事件与原文证据')
        return await analyze_one(mode,article,latest('news'))
    if job['kind']=='news_batch':
        rows=[]
        for i,article in enumerate(payload['articles']):
            await step(f'分析新闻 {i+1}/{len(payload["articles"])}')
            try:
                result=await analyze_one(mode,article,latest('news'))
                rows.append({'index':i,'title':article['title'],'status':'complete','result':result})
            except AppError as exc:
                rows.append({'index':i,'title':article['title'],'status':'failed','error':exc.as_dict()})
            await step(f'已处理新闻 {i+1}/{len(payload["articles"])}',{'items':list(rows),'mode':mode,'input_source':'用户提供','completed':sum(r['status']=='complete' for r in rows)})
        return {'items':rows,'mode':mode,'input_source':'用户提供','completed':sum(r['status']=='complete' for r in rows)}
    raise AppError('unknown_job','未知任务类型',422)


async def worker():
    while True:
        job_id=await queue.get()
        try:
            with transaction() as session:
                job=session.get(Job,job_id)
                if not job or job.status!='queued': continue
                job.status='running'; job.step='开始处理'; job.updated_at=datetime.now(timezone.utc)
                data={**serialize(job),'payload':job.payload}
            async def step(text,partial=None):
                with transaction() as session:
                    current=session.get(Job,job_id)
                    if not current or current.status=='cancelled':
                        raise AppError('cancelled','任务已取消',409)
                    current.step=text; current.updated_at=datetime.now(timezone.utc)
                    if partial is not None: current.result=partial
            try:
                result=await asyncio.wait_for(execute(data,step),timeout=settings().job_timeout)
                with transaction() as session:
                    current=session.get(Job,job_id)
                    if current.status!='cancelled':
                        current.status='complete'; current.step='已完成'; current.result=result
            except (AppError,TimeoutError,Exception) as exc:
                error=exc.as_dict() if isinstance(exc,AppError) else {'code':'task_timeout' if isinstance(exc,TimeoutError) else 'task_failed','message':'任务超时，可重试' if isinstance(exc,TimeoutError) else '任务未完成，请检查数据或重试','retryable':True}
                with transaction() as session:
                    current=session.get(Job,job_id)
                    if current.status!='cancelled':
                        error['stage']=current.step
                        if error['code']=='task_timeout': error['message']='任务超时：'+current.step+'；已保存的结果仍可查看'
                        current.status='failed'; current.step=error['message']; current.error=error
        finally:
            queue.task_done()


async def start():
    global queue
    queue=asyncio.Queue()
    with transaction() as session:
        for job in session.scalars(select(Job).where(Job.status=='running')):
            job.status='interrupted'; job.step='服务重启中断，可重新提交'
        queued=[job.id for job in session.scalars(select(Job).where(Job.status=='queued'))]
    for job_id in queued: queue.put_nowait(job_id)
    workers.extend(asyncio.create_task(worker()) for _ in range(settings().worker_concurrency))


async def stop():
    for task in workers: task.cancel()
    await asyncio.gather(*workers,return_exceptions=True)
    workers.clear()
