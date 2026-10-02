from sqlalchemy import select
from app.db import Session, Prompt, transaction
from app.errors import AppError

from app.services.prompt_library import DEFAULTS, PRESETS

def latest(kind):
    if kind not in DEFAULTS:
        raise AppError('invalid_prompt','未知提示词类型',422)
    with Session() as s:
        item=s.scalar(select(Prompt).where(Prompt.kind==kind).order_by(Prompt.version.desc()).limit(1))
        return {'id':item.id,'kind':kind,'version':item.version,'content':item.content} if item else {'id':'default-'+kind,'kind':kind,'version':0,'content':DEFAULTS[kind]}

def save(kind,content):
    previous=latest(kind)
    if not content.strip() or len(content)>6000:
        raise AppError('invalid_prompt','提示词须为 1 至 6000 字符',422)
    with transaction() as s:
        item=Prompt(kind=kind,version=previous['version']+1,content=content)
        s.add(item); s.flush()
        return {'id':item.id,'kind':kind,'version':item.version,'content':content}

def versions(kind):
    latest(kind)
    with Session() as s:
        return [{'id':p.id,'kind':kind,'version':p.version,'content':p.content} for p in s.scalars(select(Prompt).where(Prompt.kind==kind).order_by(Prompt.version.desc()))]
