from pathlib import Path
from typing import Literal
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).with_name('.env'), env_file_encoding='utf-8', extra='ignore')
    SECRET_KEY: SecretStr
    ALGORITHM: Literal['HS256'] = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, gt=0)
    AI_MODE: Literal['rules', 'llm'] = 'rules'
    LLM_API_KEY: SecretStr | None = None

settings = Settings()
