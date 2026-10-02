"""SSE session clock. Unknown calendar years fail closed for recommendations."""
from datetime import date, datetime, time, timedelta, timezone

SHANGHAI=timezone(timedelta(hours=8))
CALENDAR_SOURCE='https://www.sse.com.cn/disclosure/announcement/general/c/c_20251222_10802507.shtml'
HOLIDAYS={2026:[('01-01','01-03'),('02-15','02-23'),('04-04','04-06'),('05-01','05-05'),('06-19','06-21'),('09-25','09-27'),('10-01','10-07')]}


def trading_day(day):
    if day.year not in HOLIDAYS: return None
    return day.weekday()<5 and not any(a<=day.strftime('%m-%d')<=b for a,b in HOLIDAYS[day.year])


def session_state(now=None):
    now=(now or datetime.now(timezone.utc)).astimezone(SHANGHAI)
    day=trading_day(now.date())
    if day is None: return 'calendar_unknown'
    if not day: return 'closed'
    minute=now.hour*60+now.minute
    if 570<=minute<690 or 780<=minute<900: return 'trading'
    if 690<=minute<780: return 'lunch'
    return 'closed'


def quote_quality(stamp,now=None):
    now=(now or datetime.now(timezone.utc)).astimezone(SHANGHAI)
    session=session_state(now)
    result={'market_state':session,'calendar_source':CALENDAR_SOURCE,'valid_for_valuation':False}
    if session=='calendar_unknown': return {**result,'freshness':'calendar_unknown'}
    try:
        quoted=datetime.fromisoformat(stamp.replace('Z','+00:00'))
        if quoted.tzinfo is None: raise ValueError('No timezone')
        quoted=quoted.astimezone(SHANGHAI)
    except (ValueError,TypeError,AttributeError): return {**result,'freshness':'unknown_time'}
    if quoted>now+timedelta(minutes=5): return {**result,'freshness':'future_time'}
    if session=='trading':
        valid=quoted.date()==now.date() and (now-quoted).total_seconds()<=600
    elif session=='lunch':
        valid=quoted.date()==now.date() and quoted.time()>=time(11,20)
    else:
        day=now.date()
        if trading_day(day) and now.time()<time(9,30): day-=timedelta(days=1)
        while trading_day(day) is False: day-=timedelta(days=1)
        if trading_day(day) is None: return {**result,'freshness':'calendar_unknown'}
        valid=quoted.date()==day and quoted.time()>=time(14,50)
    return {**result,'freshness':'current' if valid else 'stale','valid_for_valuation':valid}
