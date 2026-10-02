"""Read saved results and benchmark local demo valuation; no model calls."""
import json
import math
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx

root=Path(__file__).resolve().parents[1]
out=root/'docs'/'samples'
out.mkdir(parents=True,exist_ok=True)
verification=root/'.runtime'/'verification'
with httpx.Client(base_url='http://127.0.0.1:8010/api',timeout=30) as client:
    samples=[]
    for _ in range(20):
        started=time.perf_counter()
        response=client.post('/valuations/calculate?mode=demo',json={'symbol':'DEMO:HCM'})
        response.raise_for_status()
        result=response.json()
        assert len(result['sensitivity']['cells'])==5 and len(result['years'])==5
        samples.append(round((time.perf_counter()-started)*1000,2))
    perf={'measured_at':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),
          'method':'20 sequential HTTP requests over loopback, includes DCF, scenarios and sensitivity; no samples excluded',
          'samples_ms':samples,'median_ms':statistics.median(samples),'p95_ms':sorted(samples)[math.ceil(.95*len(samples))-1],
          'max_ms':max(samples)}
    (verification/'performance.json').write_text(json.dumps(perf,indent=2),encoding='utf-8')
    summary=json.loads((verification/'live-research-summary.json').read_text(encoding='utf-8'))
    for endpoint,name in [(f"/research-runs/{summary['report_id']}/export?mode=live",'live-research.md'),
                          (f"/valuations/{summary['valuation_id']}/export?mode=live",'live-dcf.csv')]:
        response=client.get(endpoint);response.raise_for_status()
        (out/name).write_text(response.text,encoding='utf-8-sig' if name.endswith('csv') else 'utf-8')
    job=client.get('/jobs/j_8822a61ee9d148798ef79ca20d9d77ae?mode=live')
    job.raise_for_status()
    (verification/'live-news-success.json').write_text(json.dumps(job.json(),ensure_ascii=False,indent=2),encoding='utf-8')
    assert job.json()['status']=='complete'
    print(json.dumps(perf,ensure_ascii=False))
    print('Saved live report, DCF export and verified news evidence; no model calls.')
