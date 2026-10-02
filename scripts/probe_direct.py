import asyncio
import json
from pathlib import Path
import re
import sys
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.config import settings

async def main():
    out = ROOT / '.runtime' / 'probes'
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        base = 'https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/'
        page = await client.get(base+'Index', params={'type':'web','code':'sh600519'})
        match = re.search(r'id="hidctype"[^>]*value="([^"]+)"',page.text)
        if not match:
            match = re.search(r'value="([^"]+)"[^>]*id="hidctype"',page.text)
        ctype = match[1] if match else '4'
        dates = '2026-06-30,2025-12-31,2025-06-30,2024-12-31,2023-12-31'
        async def fetch(name, path):
            try:
                response = await client.get(base+path,params={'companyType':ctype,'reportDateType':'0','reportType':'1','code':'SH600519','dates':dates})
                data=response.json().get('data',[])
                (out / f'direct_{name}.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
                return {'case':name,'status':response.status_code,'rows':len(data),'columns':list(data[0]) if data else []}
            except Exception as exc:
                return {'case':name,'error_type':type(exc).__name__}
        results=await asyncio.gather(fetch('income','lrbAjaxNew'),fetch('balance','zcfzbAjaxNew'),fetch('cashflow','xjllbAjaxNew'))
        print(json.dumps([{'case':v['case'], 'status':v.get('status'), 'rows':v.get('rows'), 'error':v.get('error_type')} for v in results]))
        (out/'direct_summary.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        cfg=settings()
        if cfg.key_configured:
            response=await client.post(cfg.deepseek_base_url.rstrip('/')+'/chat/completions',headers={'Authorization':'Bearer '+cfg.deepseek_api_key.get_secret_value()},json={'model':cfg.deepseek_model,'messages':[{'role':'user','content':'Respond with exactly the JSON object {"connected":true}.'}],'response_format':{'type':'json_object'},'thinking':{'type':'disabled'},'max_tokens':32})
            data=response.json()
            print(json.dumps({'deepseek_status':response.status_code,'model':data.get('model'),'connected':data.get('choices',[{}])[0].get('message',{}).get('content') if response.is_success else None,'error_code':data.get('error',{}).get('code')}))

if __name__=='__main__':
    asyncio.run(main())
