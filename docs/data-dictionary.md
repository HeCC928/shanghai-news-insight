# 数据字典与来源核对

日期：2026-09-19。统一 CNY、金额元、股数股、比率小数。缺失保留 null，不把空项推断成零。

## 已验证的适配器

| 数据 | 来源 | 结果与限制 |
| --- | --- | --- |
| 证券名单 | 上交所主数据 | 主板试取1702条；分主板A股/科创板证券类型查询，不只用代码前缀 |
| 最新报价 | 腾讯证券 | 600519.SH 成功，保留原行情时点；市值原单位亿元转元 |
| 日价格 | 腾讯证券日K线 | 1M取得23条不复权收盘价 |
| 新闻 | AKShare stock_news_em / 东方财富 | 近期10条摘录及原链接，不承诺全文 |
| 三张财报 | 东方财富 NewFinanceAnalysis | 核实公司类型后有限日期查询，保存合并口径原字段 |

最初东方财富全市场报价/历史行情候选连接失败，完整长历史财报请求慢，已改用实测成功的有界路径。接口成功一次不构成可用性 SLA。

## 财务映射

| 字段 | 来源或方法 | 口径 |
| --- | --- | --- |
| revenue_base | OPERATE_INCOME | 累计转TTM；不足用最新完整年，明确期间 |
| revenue_growth | 历史收入增长中位数 | 五年假设，不是公司预测 |
| ebit_margin | 收入−成本−税金附加−销售−管理−研发 | 核心经营利润正常化中位数；不含金融收益/投资损益，不延续非常项 |
| da_ratio | FA_IR_DEPR + IA_AMORTIZE + LPE_AMORTIZE + USERIGHT_ASSET_AMORTIZE | 四项均可核实才计算；含使用权摊销 |
| capex_ratio | CONSTRUCT_LONG_ASSET + 使用权摊销代理的租赁再投资 | 融资租赁口径假设 |
| nwc_ratio | (NOTE_ACCOUNTS_RECE + INVENTORY − NOTE_ACCOUNTS_PAYABLE)/收入 | 贸易营运资本代理，未含全部其他经营项目 |
| nwc_base | 正常化贸易比率×基础收入 | 估计基期值 |
| tax_rate / wacc | 默认25% / 9% | 研究假设，不是实测 |
| terminal_growth / roic | 默认2% / 10% | 可编辑假设，需满足模型约束 |
| excess_cash / non_operating_assets | 默认不额外增值 | 保守简化，不代表余额为零 |
| interest_bearing_debt | 短借+长借+债券+租赁+到期非流动负债 | 空项需附注核查；不使用总负债冒充；剔除到期非融资部分 |
| minority_interest_value | MINORITY_EQUITY | 账面价值代理 |
| preferred_equity_value | PREFERRED_SHARES | 缺失需带来源手动核实 |
| diluted_shares | SHARE_CAPITAL | 总股本代理，核对稀释和公司行动，不用流通股本 |
| current_price | 有时点的不复权报价 | 服务端注入，前端不能伪造 |

每项保留 value、unit、origin、source_ref、note。原始快照保存 REPORT_DATE、NOTICE_DATE、UPDATE_DATE、CURRENCY；存量不做TTM，流量TTM=本期累计+上年全年−上年同期。

## 人工补充案例与简化

验收依据[贵州茅台2026半年报](https://static.cninfo.com.cn/finalpage/2026-08-15/1225475868.PDF)第25、27页核实优先权益、融资租赁债务。财务子公司的金融资产负债未单独分部估值，现金和非经营资产也不额外增值；明确为含简化调整的研究情景。数值与理由存于 correction snapshot，不硬编码成普遍规则。

## 时间与缓存

报价交易时段60秒、休市15分钟；新闻15分钟、财报24小时、日价格1小时。缓存另标fresh/cached/stale。2026日历依据[上交所公告](https://www.sse.com.cn/disclosure/announcement/general/c/c_20251222_10802507.shtml)。周末/节假日接受最近交易日收盘；交易时容许十分钟公开报价延迟。未知时间、未来时间、未知日历年或过期报价停止当前推荐。

文章主体出现公司名时标company，否则related；关联不是归属证明。按文章标识和内容去重，保存发布时间、检索时间和来源链接。
