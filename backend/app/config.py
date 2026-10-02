from functools import lru_cache
from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore', env_file_encoding='utf-8')
    deepseek_api_key: SecretStr = SecretStr('')
    deepseek_base_url: str = 'https://api.deepseek.com'
    deepseek_model: str = 'deepseek-flash'
    data_mode: str = 'demo'
    database_url: str = 'sqlite:///./.runtime/huxun.db'
    request_timeout: int = Field(default=20, ge=1, le=120)
    model_request_timeout: int = Field(default=65, ge=5, le=180)
    job_timeout: int = Field(default=240, ge=10, le=600)
    worker_concurrency: int = Field(default=2, ge=1, le=4)

    @property
    def key_configured(self):
        return bool(self.deepseek_api_key.get_secret_value().strip())

    @property
    def resolved_database_url(self):
        prefix = 'sqlite:///./'
        if self.database_url.startswith(prefix):
            path = ROOT / self.database_url[len(prefix):]
            path.parent.mkdir(parents=True, exist_ok=True)
            return f'sqlite:///{path.as_posix()}'
        return self.database_url


@lru_cache
def settings():
    return Settings()
