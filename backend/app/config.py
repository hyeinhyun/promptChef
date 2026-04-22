from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    google_api_key: str = ""

    fast_model_openai: str = "gpt-4o-mini"
    deep_model_openai: str = "gpt-4o"
    fast_model_google: str = "gemini-1.5-flash"
    deep_model_google: str = "gemini-1.5-pro"

    default_provider: str = "openai"  # openai | google
    allowed_origins: str = "*"


settings = Settings()
