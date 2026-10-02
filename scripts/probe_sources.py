"""Small, bounded read-only probes. Raw public data stays in ignored .runtime."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.runtime' / 'probes'
CASES = {
    'news': ('stock_news_em', {'symbol': '600519'}),
    'income': ('stock_profit_sheet_by_report_em', {'symbol': 'SH600519'}),
    'balance': ('stock_balance_sheet_by_report_em', {'symbol': 'SH600519'}),
    'cashflow': ('stock_cash_flow_sheet_by_report_em', {'symbol': 'SH600519'}),
    'quote': ('stock_sh_a_spot_em', {}),
    'profile': ('stock_individual_info_em', {'symbol': '600519', 'timeout': 15}),
    'prices': ('stock_zh_a_hist', {'symbol': '600519', 'start_date': '20260801', 'end_date': '20260919', 'adjust': ''}),
    'universe': ('stock_info_sh_name_code', {'symbol': '主板A股'}),
}

def child(name):
    import akshare as ak
    fn, kwargs = CASES[name]
    started = time.monotonic()
    try:
        df = getattr(ak, fn)(**kwargs)
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f'{name}.json').write_text(df.to_json(orient='records', force_ascii=False, date_format='iso'), encoding='utf-8')
        result = {'case': name, 'status': 'ok' if len(df) else 'empty', 'rows': len(df),
                  'columns': list(df.columns), 'seconds': round(time.monotonic()-started, 2), 'akshare': ak.__version__}
    except Exception as exc:
        result = {'case': name, 'status': 'error', 'error_type': type(exc).__name__,
                  'message': str(exc)[:300], 'seconds': round(time.monotonic()-started, 2)}
    print(json.dumps(result, ensure_ascii=False))

def probe(name):
    try:
        result = subprocess.run([sys.executable, __file__, name], capture_output=True, text=True,
                                encoding='utf-8', timeout=35, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
        lines = result.stdout.strip().splitlines()
        return json.loads(lines[-1]) if lines else {'case': name, 'status': 'process_error', 'error': result.stderr[-200:]}
    except subprocess.TimeoutExpired:
        return {'case': name, 'status': 'timeout', 'seconds': 35}

if __name__ == '__main__':
    if len(sys.argv) == 2:
        child(sys.argv[1])
    else:
        OUT.mkdir(parents=True, exist_ok=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(probe, CASES))
        (OUT / 'summary.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(results, ensure_ascii=False))
