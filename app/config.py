from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки сервиса. Любое поле можно переопределить переменной окружения."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/search"
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index: str = "documents"
