"""Explicit paid preparation of one Maotai presentation; completed steps resume locally.
Run with the project's Python while the API is up. No credentials are printed.
"""
import json
import sys
import time
from datetime import datetime,timezone
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.db import save_snapshot,uid
from app.services.prompt_library import PRESETS

stamp=datetime.now().strftime('%Y-%m-%d')
directory=ROOT/'.runtime'/('presentation-'+stamp)
directory.mkdir(parents=True,exist_ok=True)
state_file=directory/'progress.json'
state=json.loads(state_file.read_text(encoding='utf-8')) if state_file.exists() else {}
def persist(): state_file.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')

with httpx.Client(base_url='http://127.0.0.1:8010/api',timeout=95) as c:
    def get(path):
        response=c.get(path+('&' if '?' in path else '?')+'mode=live');response.raise_for_status();return response.json()
    def post(path,body):
        response=c.post(path,params={'mode':'live'},json=body,headers={'Idempotency-Key':uid('prep_')});response.raise_for_status();return response.json()
    def run(name,path,body=None):
        old=state.get(name,{})
        if old.get('status')=='complete':
            print(name+': restored',flush=True);return old['result']
        job=get('/jobs/'+old['id']) if old.get('id') and old.get('status') in ('queued','running') else post(path,body or {})
        start=time.monotonic();previous=None
        while True:
            state[name]=job;persist()
            if job['step']!=previous: print(name+': '+job['step'],flush=True);previous=job['step']
            if job['status'] not in ('queued','running'): break
            if time.monotonic()-start>300: raise RuntimeError(name+': preparation poll deadline; rerun resumes same job')
            time.sleep(1);job=get('/jobs/'+job['id'])
        if job['status']!='complete': raise RuntimeError(name+': '+json.dumps(job.get('error'),ensure_ascii=False))
        return job['result']

    for kind in ['research','news','valuation']:
        preset=next(p for p in PRESETS if p['id']==kind+'-maotai')
        current=next(p for p in get('/prompts')['items'] if p['kind']==kind)
        if current['content']!=preset['content']: post('/prompts/'+kind,{'content':preset['content']})
    prompts=get('/prompts')['items']
    # Freshly attempt data collection once. Each saved model result has its own immutable sources.
    overview=get('/companies/600519.SH/overview')
    print('quote: '+str((overview.get('quote') or {}).get('market_as_of')),flush=True)
    financial=get('/companies/600519.SH/financials')
    print('financial: '+financial['status'],flush=True)
    if financial['status']!='eligible': raise RuntimeError('Financial review required: '+json.dumps(financial.get('missing_fields'),ensure_ascii=False))
    news=get('/companies/600519.SH/news')['items']
    prices={}
    for range_name in ['1M','3M','1Y']:
        prices[range_name]=get('/companies/600519.SH/prices?range='+range_name)
        print('prices '+range_name+': '+str(len(prices[range_name]['items'])),flush=True)
    report=run('research','/research-runs',{'symbol':'600519.SH'})
    if report['status']!='complete': raise RuntimeError('Research incomplete: '+json.dumps({'errors':report.get('errors'),'ai_error':report.get('ai_error')},ensure_ascii=False))
    valuation_id=report['valuation_id']
    explanation=run('explanation','/valuations/'+valuation_id+'/explain')
    suggestions=run('suggestions','/valuations/'+valuation_id+'/suggestions')
    articles=[]
    for index,article in enumerate(news[:10]):
        result=run('article:'+article['id'],'/articles/'+article['id']+'/analyze')
        articles.append({'article':article,'result':result})
    questions=[]
    for index,question in enumerate([
        '当前现金流估值结论最依赖哪些假设？请核对保存的估值，指出反证条件与需要补充的资料。',
        '结合现有新闻，茅台直营与经销渠道变化通过哪些机制影响现金流？哪些结论有证据，哪些还不能判断？',
        '如果向金融科技硕士面试官介绍这份研究，你会如何解释数据口径、财务子公司处理、模型边界及下一步核查？']):
        result=run('question:'+str(index),'/research-runs/'+report['id']+'/questions',{'question':question})
        questions.append({'question':question,'result':result})
    batch=run('batch','/news-batches',{'articles':[{'title':n['article']['title'],'content':n['article']['content'],'source':n['article']['source']} for n in articles]})
    pack={'id':uid('presentation_'),'mode':'live','symbol':'600519.SH','prepared_at':datetime.now(timezone.utc).isoformat(),
          'historical_snapshot':True,'report':report,'prices':prices,'news':articles,'explanation':explanation,
          'suggestions':suggestions,'questions':questions,'prompts':prompts,'batch':batch,'batch_job_id':state['batch']['id'],
          'checks':[{'name':name,'status':'complete','detail':detail} for name,detail in [
              ('报价与财报','保留报价时点、财报期、人工核查与原始来源'),('历史行情','1M / 3M / 1Y 三组数据'),
              ('公司研究','专业模板；证据、风险、新闻与核查事项'),('DCF','基准、三情景、敏感性矩阵、解释与假设建议'),
              ('新闻逐篇分析',str(len(articles))+'篇；含原文证据与经营影响路径'),('批量新闻',str(batch['completed'])+'篇完成；复用相同内容/提示词的分析缓存'),
              ('工具研究问答',str(len(questions))+'个问题提前生成'),('提示词试运行','研究、新闻和估值三种模板均通过对应真实调用')]]}
    save_snapshot('presentation','live','600519.SH',pack,pack['id'])
    (directory/'presentation.json').write_text(json.dumps(pack,ensure_ascii=False,indent=2),encoding='utf-8')
    for path,name in [('/research-runs/'+report['id']+'/export','research.md'),('/valuations/'+valuation_id+'/export','dcf.csv'),('/news-batches/'+state['batch']['id']+'/export','news-analysis.csv')]:
        response=c.get(path,params={'mode':'live'});response.raise_for_status();(directory/name).write_text(response.text,encoding='utf-8')
    print(json.dumps({'presentation_id':pack['id'],'articles':len(articles),'questions':len(questions),'report_id':report['id'],'directory':str(directory)},ensure_ascii=False),flush=True)
