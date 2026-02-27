from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=True)

    GITHUB_TOKEN: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""
    OPENROUTER_API_KEY: str = ""
    AI_MODEL: str = "openai/gpt-5.3-codex"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    MAX_FILE_SIZE_KB: int = 500


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()