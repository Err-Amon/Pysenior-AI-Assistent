from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=True)

    # GitHub
    GITHUB_TOKEN: str = ""
    GITHUB_WEBHOOK_SECRET: str = "test_secret"

    # App
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    MAX_FILE_SIZE_KB: int = 500

    # LLM Configuration
    LLM_PROVIDER: str = "openai"  # Options: "openai", "anthropic", "gemini", "groq"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""  # FREE tier: https://makersuite.google.com/app/apikey
    GROQ_API_KEY: str = ""  # FREE tier: https://console.groq.com


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
