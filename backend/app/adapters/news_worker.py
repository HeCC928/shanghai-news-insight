import hashlib
import json
import re
import sys
from datetime import datetime, timezone
import akshare as ak

if __name__ == '__main__':
    symbol=sys.argv[1]
    if not re.fullmatch(r'\d{6}\.SH',symbol):
        raise ValueError('Invalid symbol')
    rows=ak.stock_news_em(symbol=symbol.split('.')[0]).to_dict('records')
    result=[]
    seen=set()
    for raw in rows:
        url=str(raw.get('新闻链接') or '')
        title=str(raw.get('新闻标题') or '')
        if url in seen or not title:
            continue
        seen.add(url)
        content=str(raw.get('新闻内容') or '')
        stamp=str(raw.get('发布时间') or '')
        result.append(dict(id='article_'+hashlib.sha256((url+title).encode()).hexdigest()[:24],
            symbol=symbol,title=title,content=content,excerpt=content[:140],category='待分析',sentiment='未分析',
            source=str(raw.get('文章来源') or '来源未注明'),source_url=url if url.startswith(('https://','http://')) else None,
            published_at=stamp.replace(' ','T')+'+08:00' if stamp else None,
            fetched_at=datetime.now(timezone.utc).isoformat(),is_demo=False,content_scope='excerpt',evidence=[]))
    sys.stdout.buffer.write(json.dumps(result,ensure_ascii=False).encode('utf-8'))
