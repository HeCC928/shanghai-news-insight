"""Explicit small-sample live acceptance. No credentials are printed or exported."""
import json
import time
import uuid
from datetime import datetime,timezone
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.runtime/verification'
OUT.mkdir(parents=True,exist_ok=True)
source='https://static.cninfo.com.cn/finalpage/2026-08-15/1225475868.PDF'


with httpx.Client(base_url='http://127.0.0.1:8010/api',timeout=110) as c:
    financial=c.get('/companies/600519.SH/financials?mode=live');financial.raise_for_status();financial=financial.json()
    correction={'snapshot_id':financial['snapshot_id'],'fields':{
        'preferred_equity_value':{'value':0,'source_ref':source+'#page=25','note':'2026 半年报优先股不适用；人工核实为零，不是自动把空值补零。'},
        'interest_bearing_debt':{'value':243684868.06,'source_ref':source+'#page=27','note':'合并表租赁负债 186829502.34 加一年内到期项 56855365.72；借款及债券栏未列示余额，采用已列示租赁融资债务。财务公司吸收存款与金融资产未纳入本经营 DCF，非经营资产亦不额外计值；这是含简化调整的研究情景。'}
    }}
    fixed=c.post('/companies/600519.SH/financials/corrections?mode=live',json=correction);fixed.raise_for_status();fixed=fixed.json()
    check=c.get('/companies/600519.SH/financials?mode=live').json()
    assert check['snapshot_id']==fixed['snapshot_id'],'Manual review did not persist'
    started=time.perf_counter()
    response=c.post('/research-runs?mode=live',json={'symbol':'600519.SH'},headers={'Idempotency-Key':'live-acceptance-'+uuid.uuid4().hex})
    response.raise_for_status();job=response.json();previous=''
    while job['status'] in ('queued','running') and time.perf_counter()-started<135:
        if job['step']!=previous: print(job['step'],flush=True);previous=job['step']
        time.sleep(1)
        result=c.get('/jobs/'+job['id']+'?mode=live');result.raise_for_status();job=result.json()
    report=job.get('result') or {}
    summary={'verified_at':datetime.now(timezone.utc).isoformat(),'job_id':job['id'],'job_status':job['status'],
        'elapsed_seconds':round(time.perf_counter()-started,2),'report_id':report.get('id'),'report_status':report.get('status'),
        'model_id':report.get('model_id'),'usage':report.get('usage'),'ai_error':report.get('ai_error'),
        'errors':report.get('errors'),'financial_correction_id':fixed['snapshot_id'],'manual_fields':list(correction['fields']),
        'source_count':len(report.get('sources',[])),'valuation_id':report.get('valuation_id'),'error':job.get('error')}
    (OUT/'live-research-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'live-research-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'manual-correction.json').write_text(json.dumps(correction,ensure_ascii=False,indent=2),encoding='utf8')
    if report.get('id'):
        export=c.get('/research-runs/'+report['id']+'/export?mode=live');export.raise_for_status()
        (OUT/'live-research.md').write_text(export.text,encoding='utf8')
    if report.get('valuation_id'):
        export=c.get('/valuations/'+report['valuation_id']+'/export?mode=live');export.raise_for_status()
        (OUT/'live-dcf.csv').write_text(export.text,encoding='utf8')
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
