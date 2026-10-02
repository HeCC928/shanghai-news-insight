# 五年 FCFF 估值方法

人民币名义现金流，WACC，期末折现。未来五个滚动年度以最近经营数据为基线，不把已发生财年再折现，不细建模季度季节性。

```text
Revenue[t] = Revenue[t-1] × (1 + growth[t])
EBIT[t] = Revenue[t] × margin[t]
NOPAT[t] = EBIT[t] − max(EBIT[t],0) × tax[t]
D&A[t] = Revenue[t] × da_ratio[t]
CapEx[t] = Revenue[t] × capex_ratio[t]
NWC[t] = Revenue[t] × nwc_ratio[t]
FCFF[t] = NOPAT[t] + D&A[t] − CapEx[t] − (NWC[t] − NWC[t-1])
PV[t] = FCFF[t] / (1 + WACC)^t
Revenue[6] = Revenue[5] × (1 + terminal_growth)
NOPAT[6] = Revenue[6] × terminal_margin × (1 − terminal_tax)
Terminal FCFF = NOPAT[6] × (1 − terminal_growth / terminal_ROIC)
Terminal value[5] = Terminal FCFF / (WACC − terminal_growth)
Operating EV = sum(PV[t]) + PV(Terminal value[5])
Common equity = EV + excess cash + non-operating assets
                − interest-bearing debt − minority value − preferred equity
Fair value/share = common equity / diluted shares
```

终值扣除支持增长的再投资。非正普通股价值返回unavailable，不夹成虚假正数。

未舍入每股价值相对现价高/低超过0.01元，对应recommend/not_recommend；容差内fair_value。估值差=(价值−价)/价，价值折价率=(价值−价)/价值；分母不同。

三情景使用同一数据快照，变化增长、利润率和WACC；不是置信区间。敏感性矩阵无效参数格为空。WACC−g至少0.005，g与稳态ROIC也须匹配。

增长未必增加价值：低于资本成本的回报可能让更高增长消耗价值。因此只对固定正现金流案例检验WACC上升、价值下降，不声称所有模型单调。

金融企业、关键缺失、超过十八个月财报、未知/过期报价不能产生自动当前推荐。持续亏损或参数无法正常化需要人工研究。

租赁采用融资口径：EBIT保留使用权折旧，D&A加回，未来租赁再投资按摊销代理，股权桥接扣融资租赁债务。贸易营运资本、少数股权账面值、现金处理均包含明确估计，详见数据字典。

## Golden case

收入1000、零增长、margin20%、tax25%、D&A=CapEx=5%、NWC10%、基期NWC100、WACC10%、g0、terminalROIC10%。每年FCFF150、EV1500；现金100、债务200、股数100，股权1400、每股14。报价10时估值差40%，价值折价28.5714%。测试每股误差不超过0.000001。

方法背景：[Damodaran估值教学材料](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/lectures/val.html)。本项目默认参数、质量门槛和规则标签是产品设计，不是该来源的个股建议。
