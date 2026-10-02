import asyncio
import uuid
from app.db import Job,transaction
from app.services import jobs


def test_restart_marks_running_and_resumes_queued():
    async def scenario():
        with transaction() as session:
            old=Job(kind='research',mode='demo',symbol='DEMO:HCM',idempotency_key=uuid.uuid4().hex,status='running',payload={'symbol':'DEMO:HCM'})
            queued=Job(kind='research',mode='demo',symbol='DEMO:HCM',idempotency_key=uuid.uuid4().hex,status='queued',payload={'symbol':'DEMO:HCM'})
            session.add_all([old,queued]);session.flush();old_id,queued_id=old.id,queued.id
        await jobs.start()
        try:
            assert jobs.get_job(old_id,'demo')['status']=='interrupted'
            await asyncio.wait_for(jobs.queue.join(),3)
            assert jobs.get_job(queued_id,'demo')['status']=='complete'
        finally: await jobs.stop()
    asyncio.run(scenario())


def test_cancel_discards_late_result(monkeypatch):
    async def scenario():
        entered=asyncio.Event();release=asyncio.Event()
        async def execute(*args):
            entered.set();await release.wait();return {'late':'must not be retained'}
        monkeypatch.setattr(jobs,'execute',execute)
        await jobs.start()
        try:
            job=jobs.submit('research','demo','DEMO:HCM',{},uuid.uuid4().hex)
            await entered.wait();jobs.cancel(job['id'],'demo');release.set()
            await jobs.queue.join()
            final=jobs.get_job(job['id'],'demo')
            assert final['status']=='cancelled' and final['result'] is None
        finally: await jobs.stop()
    asyncio.run(scenario())


def test_batch_partial_failure_retains_success(monkeypatch):
    async def analyze(mode,article,preference):
        from app.errors import AppError
        if article['title']=='失败': raise AppError('source_error','测试故障')
        return {'summary':'成功','evidence':[]}
    monkeypatch.setattr(jobs,'analyze_one',analyze)
    progress=[]
    async def step(text,partial=None):
        if partial:progress.append(partial)
    result=asyncio.run(jobs.execute({'kind':'news_batch','mode':'demo','payload':{'articles':[{'title':'成功','content':'正文'},{'title':'失败','content':'正文'}]}},step))
    assert result['completed']==1
    assert [r['status'] for r in result['items']]==['complete','failed']
    assert len(progress)==2 and progress[0]['completed']==1


def test_worker_timeout_keeps_completed_batch_items(monkeypatch):
    async def execute(data,step):
        await step('第一篇已完成',{'items':[{'index':0,'status':'complete'}],'completed':1})
        raise TimeoutError()
    monkeypatch.setattr(jobs,'execute',execute)
    async def scenario():
        await jobs.start()
        try:
            job=jobs.submit('news_batch','demo','',{'articles':[]},uuid.uuid4().hex)
            await jobs.queue.join()
            final=jobs.get_job(job['id'],'demo')
            assert final['status']=='failed' and final['error']['code']=='task_timeout'
            assert final['result']['completed']==1
        finally: await jobs.stop()
    asyncio.run(scenario())
