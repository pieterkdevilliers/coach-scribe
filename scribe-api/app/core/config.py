from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    redis_url: str = "redis://localhost:6379"
    ollama_base_url: str = "http://ollama:11434"
    llm_model: str = "llama3.1:8b"
    whisper_model: str = "medium"
    temp_dir: str = "/tmp/scribe"
    max_file_size_mb: int = 500
    llm_timeout: int = 600
    logfire_token: str | None = None


settings = Settings()
