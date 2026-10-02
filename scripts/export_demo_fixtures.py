import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'backend'))
from app.adapters import demo

payload={'mode':'demo','fictional':True,'companies':[]}
for row in demo.COMPANIES:
    symbol=row['symbol']
    payload['companies'].append({'company':demo.company(symbol),'financial':demo.financials(symbol),'news':demo.news(symbol),'prices':demo.prices(symbol,'1M')})
(root/'fixtures/demo.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf8')
print('Exported five fictional fixture cases.')
