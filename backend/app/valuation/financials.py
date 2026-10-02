"""Convert reported fields into a disclosed, editable research baseline.

Reported, derived and assumed values remain separate. Approximate economic
adjustments are never relabelled as reported financial statement facts.
"""
from statistics import median
from app.valuation.normalization import normalize_number, ttm, financial_eligibility
from app.valuation.engine import DCFInputs


def number(row, key):
    return normalize_number(row.get(key), '元')


def normalize_reports(symbol, raw, quote, company):
    incomes={r['REPORT_DATE'][:10]:r for r in raw['income']}
    balances={r['REPORT_DATE'][:10]:r for r in raw['balance']}
    cashflows={r['REPORT_DATE'][:10]:r for r in raw['cashflow']}
    periods=sorted(incomes, reverse=True)
    if not periods:
        return {'status':'insufficient_data','reason':'没有利润表','inputs':None,'provenance':{},'history':[], 'missing_fields':['income']}
    latest=periods[0]
    annuals=[d for d in periods if d.endswith('12-31')]
    sector=incomes[latest].get('ORG_TYPE') or company.get('sector','')
    # Financial statement organization type is authoritative for this gate.
    status,reason=financial_eligibility(sector,latest,[])
    provenance={}
    assumptions=[]
    missing=[]
    source=raw['source_url']
    def put(key,value,origin,note,unit='CNY'):
        provenance[key]=dict(value=value,origin=origin,note=note,unit=unit,source_ref=source)
        if value is None:
            missing.append(key)
        return value
    def flow(table,key):
        if latest.endswith('12-31'):
            return number(table.get(latest,{}),key)
        previous_year=int(latest[:4])-1
        value=ttm(number(table.get(latest,{}),key),number(table.get(f'{previous_year}-12-31',{}),key),number(table.get(str(previous_year)+latest[4:],{}),key))
        if value is not None:
            return value
        return number(table.get(annuals[0],{}),key) if annuals else None
    revenue=put('revenue_base',flow(incomes,'OPERATE_INCOME'),'derived','优先按累计报表构建 TTM；不足时使用最新完整年度，见基础期间')
    prior_year=int(latest[:4])-1
    revenue_ttm=latest.endswith('12-31') or all(number(incomes.get(d,{}),'OPERATE_INCOME') is not None for d in [latest,f'{prior_year}-12-31',str(prior_year)+latest[4:]])
    base_period=('截至 '+latest+' 的 TTM') if revenue_ttm and not latest.endswith('12-31') else (latest if latest.endswith('12-31') else annuals[0] if annuals else '未知')
    provenance['revenue_base']['note']='基础期间：'+base_period+'；累计流量按本期+上年全年−上年同期转换'
    history=[]
    for period in annuals[:4]:
        inc,cf,bs=incomes[period],cashflows.get(period,{}),balances.get(period,{})
        sales,capex=number(inc,'OPERATE_INCOME'),number(cf,'CONSTRUCT_LONG_ASSET')
        core_costs=[number(inc,k) for k in ['OPERATE_COST','OPERATE_TAX_ADD','SALE_EXPENSE','MANAGE_EXPENSE','RESEARCH_EXPENSE']]
        profit=sales-sum(core_costs) if sales is not None and all(v is not None for v in core_costs) else None
        # D&A components must all be available; missing is not replaced by zero.
        da_parts=[number(cf,k) for k in ['FA_IR_DEPR','IA_AMORTIZE','LPE_AMORTIZE','USERIGHT_ASSET_AMORTIZE']]
        da=sum(da_parts) if all(v is not None for v in da_parts) else None
        # Financing treatment of leases: add back ROU depreciation, assume future
        # new ROU investment equals that depreciation, include lease debt below.
        lease_da=number(cf,'USERIGHT_ASSET_AMORTIZE')
        capex=capex+lease_da if capex is not None and lease_da is not None else None
        rece,inventory,pay=[number(bs,k) for k in ['NOTE_ACCOUNTS_RECE','INVENTORY','NOTE_ACCOUNTS_PAYABLE']]
        trade_nwc=rece+inventory-pay if all(v is not None for v in (rece,inventory,pay)) else None
        if sales and sales>0:
            history.append(dict(year=int(period[:4]),revenue=sales,ebit_margin=profit/sales if profit is not None else None,
                          da_ratio=da/sales if da is not None else None,capex_ratio=capex/sales if capex is not None else None,
                          nwc_ratio=trade_nwc/sales if trade_nwc is not None else None))
    def median_field(key):
        values=[r[key] for r in history[:3] if r[key] is not None]
        return median(values) if values else None
    growths=[history[i]['revenue']/history[i+1]['revenue']-1 for i in range(len(history)-1) if history[i+1]['revenue']>0]
    g=median(growths) if growths else None
    margin=median_field('ebit_margin')
    if margin is not None and margin<=0:
        status,reason='requires_manual_model','历史经营利润无法支持正常化终值'
    inputs={}
    inputs['revenue_base']=revenue
    inputs['revenue_growth']=put('revenue_growth',[g]*5 if g is not None else None,'assumption','历史可用年度收入增长中位数延伸，不是业绩预测','ratio')
    for key,note in [
        ('ebit_margin','历史核心经营利润=(营业收入−营业成本−税金附加−销售−管理−研发费用)；不含财务收益及投资损益，减值等非常项未延续；历史中位数作为正常化假设'),
        ('da_ratio','历史折旧、无形资产、长期待摊与使用权资产摊销之和/收入中位数；各组成项须可核实'),
        ('capex_ratio','购建长期资产现金支出加估计新增使用权资产/收入；新增使用权资产按同期使用权摊销估计，租赁作为融资处理'),
        ('nwc_ratio','贸易营运资本代理：(应收票据及账款+存货−应付票据及账款)/收入，未涵盖其他经营项目')]:
        value=median_field(key)
        inputs[key]=put(key,[value]*5 if value is not None else None,'assumption',note,'ratio')
    latest_bs=balances.get(latest,{})
    for key,value,note in [
        ('tax_rate',[.25]*5,'通用研究税率，不是已测现金税率'),
        ('wacc',.09,'通用名义折现率，不是公司实测资本成本'),
        ('terminal_growth',.02,'通用长期增长假设'),
        ('terminal_roic',.10,'通用稳态 ROIC 假设'),
        ('terminal_margin',margin,'延续历史核心经营利润率中位数，需检查稳态合理性'),
        ('terminal_tax_rate',.25,'通用稳态税率')]:
        inputs[key]=put(key,value,'assumption',note,'ratio')
    ratio=median_field('nwc_ratio')
    inputs['nwc_base']=put('nwc_base',ratio*revenue if ratio is not None and revenue else None,'assumption','贸易营运资本比例乘基础收入，属于正常化估计')
    # Explicit conservative economic choices, not missing-field zero imputation.
    inputs['excess_cash']=put('excess_cash',0,'assumption','保守情景将全部现金视作经营所需，不计入超额现金；不是现金余额为零')
    inputs['non_operating_assets']=put('non_operating_assets',0,'assumption','未对非经营资产另行估价，保守地不计增值；不是资产不存在')
    debt_parts=[number(latest_bs,k) for k in ['SHORT_LOAN','LONG_LOAN','BOND_PAYABLE','LEASE_LIAB','NONCURRENT_LIAB_1YEAR']]
    debt=sum(debt_parts) if all(v is not None for v in debt_parts) else None
    inputs['interest_bearing_debt']=put('interest_bearing_debt',debt,'derived','短期借款+长期借款+应付债券+租赁负债+一年内到期非流动负债；任一空项需查附注，不能用总负债替代；到期项中非融资部分需人工剔除')
    inputs['minority_interest_value']=put('minority_interest_value',number(latest_bs,'MINORITY_EQUITY'),'assumption','少数股东权益账面值作为价值代理，并非市场估值')
    preferred=number(latest_bs,'PREFERRED_SHARES')
    inputs['preferred_equity_value']=put('preferred_equity_value',preferred,'reported','优先股权益；未列示与零不同，缺失需核实补充')
    inputs['diluted_shares']=put('diluted_shares',number(latest_bs,'SHARE_CAPITAL'),'assumption','报告期总股本作为股数代理；需核对后续公司行动及稀释证券','shares')
    inputs['current_price']=put('current_price',quote.get('price'),'reported','报价快照，不复权','CNY/share')
    assumptions=[p['note'] for p in provenance.values() if p['origin']=='assumption']
    # The auto-generated baseline deliberately stays incomplete for undisclosed
    # equity adjustments. A sourced manual correction is a first-class workflow.
    if missing and status=='eligible':
        status,reason='insufficient_data','需要核实补充：'+ '、'.join(dict.fromkeys(missing))
    if status=='eligible':
        try:
            DCFInputs(**inputs)
        except ValueError:
            status,reason='requires_manual_model','历史参数超出首版自动模型范围，请人工核查'
    return dict(symbol=symbol,status=status,reason=reason,period_end=latest,
                disclosed_at=incomes[latest].get('NOTICE_DATE'),source_url=source,history=history,
                inputs=inputs,provenance=provenance,missing_fields=list(dict.fromkeys(missing)),
                assumptions=assumptions,quality_status='assumption_heavy',is_demo=False,
                base_period=base_period,organization_type=sector)
