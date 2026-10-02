import time
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope='module')
def client():
    with TestClient(app) as instance:
        yield instance


def wait_job(client,job_id):
    for _ in range(100):
        job=client.get(f'/api/jobs/{job_id}').json()
        if job['status'] not in ('queued','running'):
            assert job['status']=='complete',job
            return job['result']
        time.sleep(.02)
    pytest.fail('Job did not terminate')


def test_data_scope_and_watchlist(client):
    assert client.get('/api/health').json()['model_configured'] is False
    companies=client.get('/api/companies').json()['items']
    assert len(companies)==5
    assert all(c['symbol'].startswith('DEMO:') for c in companies)
    assert client.get('/api/companies/600519.SH/overview').status_code==404
    assert client.get('/api/companies?query=华辰').json()['items'][0]['symbol']=='DEMO:HCM'
    assert client.post('/api/watchlist',json={'symbol':'DEMO:QTECH'}).status_code==200
    assert 'DEMO:QTECH' in client.get('/api/watchlist').json()['symbols']
    assert client.delete('/api/watchlist/DEMO:QTECH').status_code==200
    assert 'DEMO:QTECH' not in client.get('/api/watchlist').json()['symbols']


def test_valuation_snapshots_scenarios_and_export(client):
    body={'symbol':'DEMO:HCM'}
    preview=client.post('/api/valuations/calculate',json=body)
    assert preview.status_code==200,preview.text
    value=preview.json()
    assert value['recommendation']=='recommend'
    assert len(value['years'])==5
    assert len(value['sensitivity']['cells'])==5
    modified={**value['inputs'],'wacc':.15,'current_price':.01}
    saved=client.post('/api/valuations',json={**body,'inputs':modified,'title':'折现率测试'}).json()
    assert saved['current_price']==22.8, 'Client must not fabricate the current quote'
    assert saved['fair_value']<value['fair_value']
    assert saved['provenance']['wacc']['origin']=='manual'
    assert client.get('/api/valuations/'+saved['id']).json()['inputs']['wacc']==.15
    exported=client.get('/api/valuations/'+saved['id']+'/export')
    assert exported.status_code==200 and 'quote_snapshot_id' in exported.text
    assert client.post('/api/valuations/calculate',json={'symbol':'DEMO:HBANK'}).status_code==422
    assert client.post('/api/valuations/calculate',json={'symbol':'DEMO:QTECH'}).status_code==422
    assert client.post('/api/valuations/calculate',json={'symbol':'DEMO:YHE'}).json()['recommendation']=='not_recommend'
    assert client.post('/api/valuations/calculate',json={'symbol':'DEMO:LXC'}).json()['recommendation']=='fair_value'


def test_complete_research_evidence_question_and_idempotency(client):
    headers={'Idempotency-Key':uuid.uuid4().hex}
    created=client.post('/api/research-runs',json={'symbol':'DEMO:HCM'},headers=headers)
    assert created.status_code==202,created.text
    job_id=created.json()['id']
    assert client.post('/api/research-runs',json={'symbol':'DEMO:HCM'},headers=headers).json()['id']==job_id
    assert client.post('/api/research-runs',json={'symbol':'DEMO:YHE'},headers=headers).status_code==409
    report=wait_job(client,job_id)
    assert report['status']=='complete'
    assert report['model_id']=='demo-prepared-content'
    assert report['recommendation']=='recommend'
    ids={s['id'] for s in report['sources']}
    for item in report['risks']+report['supporting_factors']:
        assert set(item['source_ids'])<=ids
    news_source=next(s for s in report['sources'] if s['kind']=='news')
    article=client.get('/api/articles/'+news_source['snapshot_id']).json()
    assert article['is_demo']
    assert client.get('/api/research-runs/'+report['id']+'/export').status_code==200
    answer_job=client.post('/api/research-runs/'+report['id']+'/questions',json={'question':'为什么推荐？'}).json()
    assert '演示回答' in wait_job(client,answer_job['id'])['answer']


def test_ineligible_report_stays_unavailable(client):
    job=client.post('/api/research-runs',json={'symbol':'DEMO:HBANK'}).json()
    report=wait_job(client,job['id'])
    assert report['recommendation']=='unavailable'
    assert report['valuation'] is None
    assert report['status']=='partial'


def test_news_prompt_batch_and_formula_escape(client):
    rows=client.get('/api/companies/DEMO:HCM/news?days=7&query=订单').json()['items']
    assert len(rows)==1 and rows[0]['sentiment']=='负面'
    version=client.post('/api/prompts/news',json={'content':'重点写出不确定性'}).json()
    assert version['version']>=1
    assert client.get('/api/prompts/news/versions').json()['items'][0]['content']=='重点写出不确定性'
    client.post('/api/prompts/news/reset')
    body={'articles':[{'title':'=SUM(A1:A2)','content':'公司发布经营公告。仍有不确定性。'}]}
    job=client.post('/api/news-batches',json=body).json()
    result=wait_job(client,job['id'])
    assert result['completed']==1
    exported=client.get('/api/news-batches/'+job['id']+'/export').text
    assert "'=SUM" in exported
    assert client.post('/api/news-batches',json={'articles':[]}).status_code==422
    uploaded=client.post('/api/news-batches/import',files={'file':('sample.csv','title,content\n标题,原文内容'.encode(),'text/csv')})
    assert uploaded.status_code==202
    assert wait_job(client,uploaded.json()['id'])['completed']==1


def test_validation_does_not_echo_input(client):
    response=client.post('/api/valuations/calculate',json={'symbol':'DEMO:HCM','inputs':{'secret':'private-input'}})
    assert response.status_code==422
    assert 'private-input' not in response.text


def test_cache_clear_keeps_historical_sources(client):
    from app.db import load_snapshot
    original=client.get('/api/companies/DEMO:HCM/overview').json()['quote']
    assert load_snapshot(original['snapshot_id'],'demo','quote')
    assert client.post('/api/settings/clear-cache').status_code==200
    assert load_snapshot(original['snapshot_id'],'demo','quote'), 'Source kind and payload must remain immutable'
    new=client.get('/api/companies/DEMO:HCM/overview').json()['quote']
    assert new['snapshot_id']!=original['snapshot_id']


def test_csv_single_retry_uses_saved_input(client):
    uploaded=client.post('/api/news-batches/import',files={'file':('sample.csv','title,content\n导入标题,公司披露原文'.encode(),'text/csv')}).json()
    wait_job(client,uploaded['id'])
    retry=client.post('/api/news-batches/'+uploaded['id']+'/retry/0').json()
    assert wait_job(client,retry['id'])['items'][0]['title']=='导入标题'


def test_suggestions_do_not_mutate_saved_valuation(client):
    saved=client.post('/api/valuations',json={'symbol':'DEMO:HCM'}).json()
    job=client.post('/api/valuations/'+saved['id']+'/suggestions').json()
    proposed=wait_job(client,job['id'])
    assert proposed['changes'][0]['new_value']>saved['inputs']['wacc']
    assert proposed['applied'] is False
    assert client.get('/api/valuations/'+saved['id']).json()['inputs']==saved['inputs']


@pytest.mark.parametrize('fails',[False,True])
def test_empty_or_failed_news_preserves_financial_research(client,monkeypatch,fails):
    from app.services.data import DataService
    from app.errors import AppError
    async def unavailable(self,symbol):
        if fails: raise AppError('news_unavailable','新闻源暂不可用')
        return {'items':[]}
    monkeypatch.setattr(DataService,'news',unavailable)
    job=client.post('/api/research-runs',json={'symbol':'DEMO:HCM'}).json()
    report=wait_job(client,job['id'])
    assert report['valuation']['fair_value']>0
    assert not any(s['kind']=='news' for s in report['sources'])
    source_ids={s['id'] for s in report['sources']}
    assert all(set(item['source_ids'])<=source_ids for item in report['risks'])
    if fails: assert any(e['code']=='news_unavailable' for e in report['errors'])
