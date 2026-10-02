"""Public-source adapters with bounded requests and explicit provider attribution."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone, timedelta
import hashlib
import json
import re
import sys
from pathlib import Path
import httpx
from app.config import ROOT
from app.errors import AppError

EM_BASE = 'https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/'
SSE_SOURCE = 'https://www.sse.com.cn/assortment/stock/list/share/'


def now_iso():
    return datetime.now(timezone.utc).isoformat()


async def get_json(client, url, **kwargs):
    try:
        r=await client.get(url, **kwargs)
        r.raise_for_status()
        return r.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise AppError('source_unavailable', '公开数据源暂不可用，请稍后重试', retryable=True) from exc


async def universe():
    async with httpx.AsyncClient(timeout=20) as client:
        async def board(kind):
            params={'STOCK_TYPE':kind,'REG_PROVINCE':'','CSRC_CODE':'','STOCK_CODE':'',
                'sqlId':'COMMON_SSE_CP_GPJCTPZ_GPLB_GP_L','COMPANY_STATUS':'2,4,5,7,8',
                'type':'inParams','isPagination':'true','pageHelp.pageSize':'10000','pageHelp.pageNo':'1'}
            data=await get_json(client,'https://query.sse.com.cn/sseQuery/commonQuery.do',params=params,
                                headers={'Referer':SSE_SOURCE,'User-Agent':'Mozilla/5.0'})
            rows=[]
            for raw in data.get('result',[]):
                code=raw.get('A_STOCK_CODE')
                if not code:
                    continue
                rows.append(dict(symbol=code+'.SH',name=raw.get('SEC_NAME_CN',''),
                    full_name=raw.get('FULL_NAME',''),sector=raw.get('CSRC_CODE_DESC') or raw.get('CSRC_GREAT_KIND_NAME') or '行业待核实',
                    exchange='SSE',security_type='A',board='科创板' if kind=='8' else '主板A股',
                    source_url=SSE_SOURCE,is_demo=False))
            if not rows:
                raise AppError('source_empty','证券名单为空，未切换为虚构股票',retryable=True)
            return rows
        results=await asyncio.gather(board('1'),board('8'))
        return results[0]+results[1]


async def quote(symbol):
    code=symbol.split('.')[0]
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            response=await client.get('https://qt.gtimg.cn/q=sh'+code)
            response.raise_for_status()
            fields=response.content.decode('gb18030',errors='replace').split('"')[1].split('~')
            if len(fields)<46 or fields[2]!=code:
                raise ValueError('Unexpected symbol')
            price=float(fields[3])
            if price<=0:
                raise ValueError('No valid quote')
            try:
                stamp=datetime.strptime(fields[30],'%Y%m%d%H%M%S').replace(tzinfo=timezone(timedelta(hours=8))).astimezone(timezone.utc).isoformat()
            except ValueError:
                stamp=None
            return dict(symbol=symbol,price=price,previous_close=float(fields[4]),change_pct=float(fields[32])/100,
                        market_cap=float(fields[45])*1e8,market_as_of=stamp,fetched_at=now_iso(),
                        currency='CNY',source='腾讯证券',source_url=f'https://gu.qq.com/sh{code}',
                        quality_status='quoted',is_demo=False,adjustment='none')
        except (httpx.HTTPError,ValueError,IndexError) as exc:
            raise AppError('quote_unavailable','无法取得有效报价；保留数据状态，不生成推荐',retryable=True) from exc


async def prices(symbol, range_name):
    code='sh'+symbol.split('.')[0]
    length={'1M':23,'3M':66,'1Y':250}.get(range_name,23)
    async with httpx.AsyncClient(timeout=20) as client:
        data=await get_json(client,'https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get',
                            params={'param':f'{code},day,,,{length},'})
    rows=data.get('data',{}).get(code,{}).get('day',[])
    if not rows:
        raise AppError('prices_unavailable','历史价格暂不可用',retryable=True)
    return [{'date':r[0],'close':float(r[2])} for r in rows]


async def ak_news(symbol):
    # A subprocess provides a hard deadline even when a third-party requests call lacks one.
    proc=await asyncio.create_subprocess_exec(sys.executable,str(Path(__file__).with_name('news_worker.py')),symbol,
                stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    try:
        stdout, _=await asyncio.wait_for(proc.communicate(),timeout=20)
    except BaseException:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()
        raise
    if proc.returncode:
        raise AppError('news_unavailable','新闻源暂不可用',retryable=True)
    try:
        return json.loads(stdout.decode('utf-8'))
    except ValueError as exc:
        raise AppError('news_unavailable','新闻源返回了无法解析的数据',retryable=True) from exc


async def financial_reports(symbol):
    code='SH'+symbol.split('.')[0]
    async with httpx.AsyncClient(timeout=20,follow_redirects=True) as client:
        try:
            page=await client.get(EM_BASE+'Index',params={'type':'web','code':code.lower()})
            match=re.search(r'id="hidctype"[^>]*value="([^"]+)"',page.text) or re.search(r'value="([^"]+)"[^>]*id="hidctype"',page.text)
            if not match:
                raise AppError('financial_type_unknown','无法核实财报公司类型',retryable=True)
            ctype=match[1]
            dates_json=await get_json(client,EM_BASE+'lrbDateAjaxNew',params={'companyType':ctype,'reportDateType':'0','code':code})
            all_dates=sorted({r['REPORT_DATE'][:10] for r in dates_json.get('data',[])},reverse=True)
            if not all_dates:
                raise AppError('financials_empty','没有可用的财报日期')
            latest=all_dates[0]
            previous_same=str(int(latest[:4])-1)+latest[4:]
            selected=list(dict.fromkeys([latest]+[d for d in all_dates if d.endswith('12-31')][:4]+([previous_same] if previous_same in all_dates else [])))
            async def fetch(path):
                batches=[]
                for start in range(0,len(selected),5):
                    data=await get_json(client,EM_BASE+path,params={'companyType':ctype,'reportDateType':'0','reportType':'1','code':code,'dates':','.join(selected[start:start+5])})
                    batches.extend(data.get('data',[]))
                return batches
            income,balance,cashflow=await asyncio.gather(fetch('lrbAjaxNew'),fetch('zcfzbAjaxNew'),fetch('xjllbAjaxNew'))
            return dict(income=income,balance=balance,cashflow=cashflow,fetched_at=now_iso(),company_type=ctype,
                        source_url=EM_BASE+f'Index?type=web&code={code.lower()}')
        except httpx.HTTPError as exc:
            raise AppError('financials_unavailable','财报请求超时或连接失败',retryable=True) from exc
