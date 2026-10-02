"""Explicitly fictional, reproducible examples; never returned in live mode."""
from copy import deepcopy
from datetime import date, timedelta
import math
from app.valuation.engine import DCFInputs, calculate

AS_OF = '2026-09-18T07:00:00Z'
COMPANIES = [
    {'symbol': 'DEMO:HCM', 'name': '华辰制造', 'sector': '高端制造', 'tagline': '让精密制造，连接产业未来', 'price': 22.80, 'change_pct': .0187, 'kind': 'eligible'},
    {'symbol': 'DEMO:YHE', 'name': '云海能源', 'sector': '清洁能源', 'tagline': '以稳定现金流，观察能源转型', 'price': 68.40, 'change_pct': -.0094, 'kind': 'eligible'},
    {'symbol': 'DEMO:LXC', 'name': '临溪消费', 'sector': '品牌消费', 'tagline': '从经营质量，理解长期价值', 'price': 30.0, 'change_pct': .0042, 'kind': 'fair'},
    {'symbol': 'DEMO:QTECH', 'name': '启元科技', 'sector': '半导体设备', 'tagline': '财务数据待补充样例', 'price': 46.72, 'change_pct': -.0231, 'kind': 'missing'},
    {'symbol': 'DEMO:HBANK', 'name': '沪江银行', 'sector': '银行', 'tagline': '金融行业模型边界样例', 'price': 12.56, 'change_pct': .0064, 'kind': 'unsupported'},
]

BASE = dict(revenue_base=12e9, revenue_growth=[.06,.06,.05,.04,.03],
            ebit_margin=[.22]*5, tax_rate=[.25]*5, da_ratio=[.04]*5,
            capex_ratio=[.055]*5, nwc_ratio=[.14]*5, nwc_base=1.68e9,
            wacc=.09, terminal_growth=.02, terminal_margin=.22,
            terminal_tax_rate=.25, terminal_roic=.10, excess_cash=2.8e9,
            non_operating_assets=0, interest_bearing_debt=1.2e9,
            minority_interest_value=0, preferred_equity_value=0,
            diluted_shares=1e9, current_price=22.8)


def company(symbol):
    result = next((deepcopy(c) for c in COMPANIES if c['symbol'] == symbol), None)
    if result and result['kind'] == 'fair':
        result['price'] = calculate(DCFInputs(**BASE))['fair_value']
    if result:
        result.update(exchange='DEMO', security_type='fictional', is_demo=True,
                      currency='CNY', market_as_of=AS_OF, source='沪讯虚构演示数据')
    return result


def financials(symbol):
    c = company(symbol)
    if c['kind'] in ('missing', 'unsupported'):
        return {'symbol': symbol, 'status': 'insufficient_data' if c['kind']=='missing' else 'unsupported_sector',
                'reason': '缺少资本开支与股本数据' if c['kind']=='missing' else '银行不适用当前非金融 FCFF 模型',
                'missing_fields': ['capex_ratio', 'diluted_shares'] if c['kind']=='missing' else [],
                'inputs': None, 'provenance': {}, 'period_end': '2026-06-30', 'is_demo': True,
                'history': [], 'source_url': None}
    inputs = {**deepcopy(BASE), 'current_price': c['price']}
    provenance = {k: {'value': v, 'origin': 'assumption', 'unit': 'ratio' if 'ratio' in k or 'margin' in k or 'rate' in k or k in ['wacc','terminal_growth','terminal_roic','revenue_growth'] else 'CNY',
                       'source_ref': 'demo-financial', 'note': '虚构演示输入，不对应真实公司'} for k,v in inputs.items()}
    return dict(symbol=symbol, status='eligible', reason='虚构演示数据完整', inputs=inputs,
                provenance=provenance, period_end='2026-06-30', disclosed_at='2026-08-20', is_demo=True,
                source_url=None, quality_status='demo', missing_fields=[], assumptions=['所有数字均为虚构样例'],
                history=[{'year':y,'revenue':r,'ebit_margin':m,'capex_ratio':.055,'da_ratio':.04,'nwc_ratio':.14}
                         for y,r,m in [(2023,10.2e9,.20),(2024,11.3e9,.21),(2025,12e9,.22)]])


def news(symbol):
    c = company(symbol)
    samples = [
        ('需求观察', '下游订单交付节奏放缓，公司提示短期经营不确定性', '负面', '公司表示，部分客户调整了订单交付计划，短期收入确认存在不确定性。管理层将继续关注回款与库存水平。', 18),
        ('公司公告', '披露股份回购计划，关注后续执行进度', '正面', '公司披露拟使用自有资金回购股份，计划仍需履行相应程序。回购金额与实施节奏取决于后续经营情况。', 17),
        ('财务报告', '发布半年度经营数据，经营现金流保持稳定', '中性', '公司发布半年度经营摘要，主要业务保持运行。报告同时提示原材料成本和营运资本占用可能影响现金流。', 16),
        ('业务发展', '推进产线升级，资本投入进入新阶段', '中性', '公司正在推进生产线升级，相关资本开支将分期投入。项目收益取决于客户需求与产能利用情况。', 14),
        ('行业动态', '产业链协同提速，行业需求仍待观察', '中性', '行业企业持续推进供应链协作，需求恢复速度尚不明确。该报道属于行业背景，不代表单家公司的经营预测。', 12),
        ('公司公告', '投资者交流纪要：聚焦经营效率与长期投入', '正面', '管理层表示将继续改善经营效率，并在现金流约束下进行长期投入。相关规划存在执行不确定性。', 9),
    ]
    rows=[]
    for i,(category,title,sentiment,content,day) in enumerate(samples):
        rows.append(dict(id=f'demo-{symbol.split(":")[1]}-{i}', symbol=symbol, company=c['name'],
                    title=f'{c["name"]}：{title}', content=content, excerpt=content[:55]+'…',
                    category=category, sentiment=sentiment, source='演示资料 · 虚构新闻',
                    source_url=None, published_at=f'2026-09-{day:02}T02:30:00Z', fetched_at=AS_OF,
                    is_demo=True, content_scope='fictional', evidence=[{'start':0,'end':len(content.split('。')[0])+1,'text':content.split('。')[0]+'。'}]))
    return rows


def prices(symbol, range_name='1M'):
    c=company(symbol)
    days={'1M':31,'3M':93,'1Y':366}.get(range_name,31)
    end=date(2026,9,18)
    dates=[end-timedelta(days=i) for i in reversed(range(days)) if (end-timedelta(days=i)).weekday()<5]
    values=[.88+.12*i/max(len(dates)-1,1)+.026*math.sin(i*.51)+.014*math.cos(i*1.4) for i in range(len(dates))]
    scale=c['price']/values[-1]
    return [{'date':d.isoformat(),'close':round(v*scale,2)} for d,v in zip(dates,values)]
