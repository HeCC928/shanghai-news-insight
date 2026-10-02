import csv
import io


def csv_safe(value):
    if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@')):
        return "'"+value
    return value


def valuation_csv(valuation):
    stream=io.StringIO(newline='')
    writer=csv.writer(stream)
    writer.writerow(['section','field','value','unit','origin','note'])
    for field in ['symbol','mode','created_at','model_version','financial_snapshot_id','quote_snapshot_id']:
        writer.writerow(['metadata',field,csv_safe(valuation.get(field,'')),'','',''])
    for field,value in valuation['inputs'].items():
        provenance=valuation.get('provenance',{}).get(field,{})
        writer.writerow(['assumption',field,str(value),provenance.get('unit',''),provenance.get('origin',''),csv_safe(provenance.get('note',''))])
    writer.writerow([])
    keys=list(valuation['years'][0])
    writer.writerow(keys)
    for year in valuation['years']:
        writer.writerow([csv_safe(year[k]) for k in keys])
    writer.writerow([])
    for key in ['operating_ev','equity_value','fair_value','valuation_gap','discount_to_value','recommendation']:
        writer.writerow(['result',key,valuation[key]])
    for source in valuation.get('provenance',{}).values():
        writer.writerow(['source',csv_safe(source.get('source_ref',''))])
    return '\ufeff'+stream.getvalue()


def report_markdown(report):
    from app.services.research import LABELS
    lines=[f'# {report["company"]["name"]} · 公司研究', '',
        f'数据模式：{report["mode"]}；生成时间：{report["created_at"]}',
        f'模型：{report["model_id"]}；提示词版本：{report["prompt_version"]}；估值引擎：{report["valuation_model_version"]}',
        '',f'**{LABELS[report["recommendation"]]}**','',report['summary'],'',
        '## 公司与估值',report['business_overview'],'',report['valuation_explanation']]
    for title,key in [('支持因素','supporting_factors'),('风险','risks'),('新闻','news_insights')]:
        lines.extend(['',f'## {title}'])
        lines.extend(f'- {s["text"]}（{s["kind"]}；来源 {", ".join(s["source_ids"])}）' for s in report[key])
    lines.extend(['','## 估值假设与限制'])
    lines.extend('- '+s for s in report['assumptions_to_review'])
    valuation=report.get('valuation')
    if valuation:
        for field,value in valuation['inputs'].items():
            p=valuation['provenance'].get(field,{})
            lines.append(f'- {field}: {value}；{p.get("origin","")}；{p.get("note","")}；字段来源：{p.get("source_ref","")}')
    lines.extend(['','## 来源'])
    for s in report['sources']:
        link=f'[{s["title"]}]({s["url"]})' if s.get('url') else s['title']
        lines.append(f'- {s["id"]}: {link}；时点 {s.get("published_at") or "未提供"}；快照 {s["snapshot_id"]}')
    lines.extend(['','基于所示数据与假设的估值研究，不代表收益保证。'])
    return '\n'.join(lines)
