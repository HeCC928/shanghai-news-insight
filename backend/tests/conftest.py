import os
from pathlib import Path
import tempfile

# Never run API tests against the user's real local database or credential.
_test_directory=tempfile.TemporaryDirectory(prefix='huxun-test-')
os.environ['DATABASE_URL']='sqlite:///'+(Path(_test_directory.name)/'tests.db').as_posix()
os.environ['DEEPSEEK_API_KEY']=''
os.environ['DATA_MODE']='demo'


def pytest_sessionfinish(session,exitstatus):
    from app.db import engine
    engine.dispose()
    _test_directory.cleanup()
