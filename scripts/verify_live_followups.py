"""One news, valuation explanation and scoped follow-up; uses the saved acceptance report."""
import json,time,uuid
from pathlib import Path
from datetime import datetime,timezone
import httpx

out=Path(__file__).resolve().parents[1]/'.runtime/verification'
report=json.loads((out/'live-research-report.json').read_text(encoding='utf8'))
news=next(s for s in report['sources'] if s['kind']=='news')
checks=[('article','/articles/'+news['snapshot_id']+'/analyze',{}),
        ('explain','/valuations/'+report['valuation_id']+'/explain',{}),
        ('question','/research-runs/'+report['id']+'/questions',{'question':'请先使用 get_valuation 核对本报告已保存的估值，再解释其最重要的假设局限。保持本报告公司和快照，不查询其他公司。'})]
results=[]
with httpx.Client(base_url='http://127.0.0.1:8010/api',timeout=25) as c:
    for name,path,body in checks:
        start=time.perf_counter()
        request=c.post(path+'?mode=live',json=body,headers={'Idempotency-Key':'acceptance-'+uuid.uuid4().hex})
        request.raise_for_status();job=request.json()
        while job['status'] in ('queued','running') and time.perf_counter()-start<125:
            time.sleep(1)
            request=c.get('/jobs/'+job['id']+'?mode=live');request.raise_for_status();job=request.json()
        result={'check':name,'seconds':round(time.perf_counter()-start,2),'checked_at':datetime.now(timezone.utc).isoformat(),**job}
        results.append(result)
        (out/'live-followups.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps({'check':name,'status':job['status'],'seconds':result['seconds'],'error':job.get('error'),'usage':(job.get('result') or {}).get('usage'),'tool_calls':(job.get('result') or {}).get('tool_calls')},ensure_ascii=False),flush=True)
