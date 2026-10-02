import asyncio
import httpx
import pytest
from app.adapters.deepseek import DeepSeek
from app.config import Settings
from app.errors import AppError


@pytest.mark.parametrize('status,code,count',[(401,'model_auth',1),(429,'model_busy',3),(503,'model_busy',3),(400,'model_request',1)])
def test_model_http_failures(monkeypatch,status,code,count):
    calls=[]
    class Client:
        def __init__(self,**kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,*args,**kwargs):
            calls.append(1)
            return httpx.Response(status,request=httpx.Request('POST','https://api.deepseek.com/chat/completions'),json={'error':'test'})
    async def no_wait(*args): pass
    monkeypatch.setattr(httpx,'AsyncClient',Client)
    monkeypatch.setattr(asyncio,'sleep',no_wait)
    model=DeepSeek();model.cfg=Settings(_env_file=None,deepseek_api_key='test-credential')
    with pytest.raises(AppError) as error: asyncio.run(model.chat([]))
    assert error.value.code==code and len(calls)==count


def test_model_timeout_and_missing_key(monkeypatch):
    model=DeepSeek();model.cfg=Settings(_env_file=None,deepseek_api_key='')
    with pytest.raises(AppError) as error: asyncio.run(model.chat([]))
    assert error.value.code=='model_not_configured'
    class Client:
        def __init__(self,**kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,*args,**kwargs): raise httpx.ReadTimeout('test')
    monkeypatch.setattr(httpx,'AsyncClient',Client)
    model.cfg=Settings(_env_file=None,deepseek_api_key='test-credential')
    with pytest.raises(AppError) as error: asyncio.run(model.chat([]))
    assert error.value.code=='model_timeout'
