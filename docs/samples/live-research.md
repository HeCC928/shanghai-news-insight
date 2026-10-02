# 贵州茅台 · 公司研究

数据模式：live；生成时间：2026-09-19T13:05:13.709128+00:00
模型：deepseek-flash；提示词版本：0；估值引擎：fcff-rolling-1.0

**推荐 · 当前假设下低估**

推荐 · 当前假设下低估。结论取决于所示经营与折现假设。

## 公司与估值
公司属制造业白酒企业，主营茅台酒及系列酒。中报营业总收入同比增长，净利润同比下降，收入与利润方向不一。直营平台投放规则调整，渠道结构仍在变化。

每股估值 ¥1,439.21，每股报价 ¥1,257.12，相对报价差 +14.5%。基准情景由收入增速、核心经营利润率与折现率驱动，终值现值占比较高，说明结果对长期假设敏感。该差值为模型输出，不是收益承诺；假设为通用研究参数，非公司实测资本成本。

## 支持因素
- 营业总收入同比增长，且连续多年上涨，说明收入端仍有扩张。（fact；来源 news-0）
- 直营平台收入同比大幅增长，自营渠道占比或提升。（fact；来源 news-5）
- 投放由每月三天改为每日常态化，或提升直营渠道可得性与周转。（inference；来源 news-8, news-5）

## 风险
- 中报净利润同比下降，收入增长未同步转化为利润。（fact；来源 news-0）
- 估值对长期假设敏感，终值现值占比高，假设微调会放大结果变化。（inference；来源 valuation）
- 模型税率与折现率为通用研究参数，非公司实测值，实际经营差异或影响结果。（assumption；来源 valuation, financial）

## 新闻
- 被执行信息后经公司回应并由公示系统更正，短期舆情扰动，法律责任认定不成立。（fact；来源 news-1, news-2）
- 直营平台次新飞天常态化投放，反映渠道与投放节奏持续调整的事实。（fact；来源 news-8）
- 资金流向类报道覆盖面广，难以据此判断公司特定资金趋势。（inference；来源 news-3, news-4, news-6）

## 估值假设与限制
- 收入增速延续历史中位数，是否与行业需求及投放节奏相符
- 核心经营利润率中位数作为稳态，是否可持续
- 通用折现率与长期增长假设，是否匹配公司资本成本
- 营运资本比例与税率假设，是否反映真实现金与税负
- revenue_base: 170152009062.43002；derived；基础期间：截至 2026-06-30 的 TTM；累计流量按本期+上年全年−上年同期转换；字段来源：https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
- revenue_growth: [0.15711951294790794, 0.15711951294790794, 0.15711951294790794, 0.15711951294790794, 0.15711951294790794]；assumption；历史可用年度收入增长中位数延伸，不是业绩预测；字段来源：https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
- ebit_margin: [0.6706910602970946, 0.6706910602970946, 0.6706910602970946, 0.6706910602970946, 0.6706910602970946]；assumption；历史核心经营利润=(营业收入−营业成本−税金附加−销售−管理−研发费用)；不含财务收益及投资损益，减值等非常项未延续；历史中位数作为正常化假设；字段来源：https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
- tax_rate: [0.25, 0.25, 0.25, 0.25, 0.25]；assumption；通用研究税率，不是已测现金税率；字段来源：https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
- da_ratio: [0.013117807687589928, 0.013117807687589928, 0.013117807687589928, 0.013117807687589928, 0.013117807687589928]；assumption；历史折旧、无形资产、长期待摊与使用权资产摊销之和/收入中位数；各组成项须可核实；字段来源：https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
- capex_ratio: [0.018854702782632484, 0.018854702782632484, 0.018854702782632484, 0.018854702782632484, 0.018854702782632484]；assumption；购建长期资产现金支出加估计新增使用权资产/收入；新增使用权资产按同期使用权摊销估计，租赁作为融资处理；字段来源：https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
- nwc_ratio: [0.30913961470085216, 0.30913961470085216, 0.30913961470085216, 0.30913961470085216, 0.30913961470085216]；assumption；贸易营运资本代理：(应收票据及账款+存货−应付票据及账款)/收入，未涵盖其他经营项目；字段来源：https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
- nwc_base: 52600726522.13552；assumption；贸易营运资本比例乘基础收入，属于正常化估计；字段来源：https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
- wacc: 0.09；assumption；通用名义折现率，不是公司实测资本成本；字段来源：https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
- terminal_growth: 0.02；assumption；通用长期增长假设；字段来源：https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
- terminal_margin: 0.6706910602970946；assumption；延续历史核心经营利润率中位数，需检查稳态合理性；字段来源：https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
- terminal_tax_rate: 0.25；assumption；通用稳态税率；字段来源：https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
- terminal_roic: 0.1；assumption；通用稳态 ROIC 假设；字段来源：https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
- excess_cash: 0.0；assumption；保守情景将全部现金视作经营所需，不计入超额现金；不是现金余额为零；字段来源：https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
- non_operating_assets: 0.0；assumption；未对非经营资产另行估价，保守地不计增值；不是资产不存在；字段来源：https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
- interest_bearing_debt: 243684868.06；manual；合并表租赁负债 186829502.34 加一年内到期项 56855365.72；借款及债券栏未列示余额，采用已列示租赁融资债务。财务公司吸收存款与金融资产未纳入本经营 DCF，非经营资产亦不额外计值；这是含简化调整的研究情景。；字段来源：https://static.cninfo.com.cn/finalpage/2026-08-15/1225475868.PDF#page=27
- minority_interest_value: 10842757754.86；assumption；少数股东权益账面值作为价值代理，并非市场估值；字段来源：https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
- preferred_equity_value: 0.0；manual；2026 半年报优先股不适用；人工核实为零，不是自动把空值补零。；字段来源：https://static.cninfo.com.cn/finalpage/2026-08-15/1225475868.PDF#page=25
- diluted_shares: 1250081601.0；assumption；报告期总股本作为股数代理；需核对后续公司行动及稀释证券；字段来源：https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519
- current_price: 1257.12；reported；报价快照，不复权；字段来源：https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519

## 来源
- quote: [报价快照](https://gu.qq.com/sh600519)；时点 2026-09-18T08:14:36+00:00；快照 quote_f00df509d2f54a998ce5f4e98251bc3e
- financial: [财务数据与研究假设](https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=sh600519)；时点 2026-08-15 00:00:00；快照 financial_34fe2552537b4a538e955e04dc955ac8
- valuation: 可复现的 DCF 计算；时点 2026-09-19T13:05:08.511751+00:00；快照 val_f0873895be564ed0b47e239cbd79476e
- news-0: [贵州茅台600519.SH)：2026年中报净利润为445.17亿元、同比较去年同期下降1.95%](http://finance.eastmoney.com/a/202608153842377958.html)；时点 2026-08-15T10:11:51+08:00；快照 a_ba5c5d1b3786fdf179ff4426b609
- news-1: [贵州茅台被执行158万元？公司回应](http://finance.eastmoney.com/a/202609163876167522.html)；时点 2026-09-16T18:06:11+08:00；快照 a_933f1687a6efdc86110ca1f18751
- news-2: [被执行158万元？贵州茅台：系第三方公司内部合同纠纷，法院认定公司不承担任何责任](http://finance.eastmoney.com/a/202609163876293995.html)；时点 2026-09-16T21:17:00+08:00；快照 a_a349859016713bbf8004b525a2c5
- news-3: [主力动向：9月16日特大单净流入367.77亿元](http://finance.eastmoney.com/a/202609163876088261.html)；时点 2026-09-16T16:42:00+08:00；快照 a_032053ad807aa55a0b21eb7bd60b
- news-4: [11.09亿元资金今日流入食品饮料股](http://finance.eastmoney.com/a/202609143873515271.html)；时点 2026-09-14T17:37:00+08:00；快照 a_b89f4cad1acbef6410c0db08eeab
- news-5: [i茅台再调整规则：6款次新飞天9日起常态化投放](http://finance.eastmoney.com/a/202609083868170263.html)；时点 2026-09-08T18:24:44+08:00；快照 a_b7c5c69acbdb004f51c175e785bd
- news-6: [19股受融资客青睐，净买入超亿元](http://finance.eastmoney.com/a/202609103870152644.html)；时点 2026-09-10T09:16:00+08:00；快照 a_412d1a636791cfdab242356348ae
- news-7: [深沪北百元股数量达217只，科创板股票占46.08%](http://finance.eastmoney.com/a/202609173877364796.html)；时点 2026-09-17T16:55:00+08:00；快照 a_2e4e68377a1bac31b7469d224ca1
- news-8: [i茅台次新飞天开启常态化售卖 由每月仅三天到每日两场可购](http://finance.eastmoney.com/a/202609083868347560.html)；时点 2026-09-09T00:02:00+08:00；快照 a_9a162d58206b02b302f329a8ddfa
- news-9: [百元股数量达209只，一日增加4只](http://finance.eastmoney.com/a/202609153874722847.html)；时点 2026-09-15T16:31:00+08:00；快照 a_bd8cd0bf017597b3a71d53e2fcd7

基于所示数据与假设的估值研究，不代表收益保证。