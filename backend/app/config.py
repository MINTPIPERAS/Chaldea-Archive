from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CHALDEA_", extra="ignore")

    database_url: str = "postgresql+asyncpg://chaldea:chaldea@localhost:5432/chaldea"

    # Vite 开发服务器来源
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Embedding（详见 Docs/embedding-guide.md）：cloud | ollama | local
    embedding_provider: str = "cloud"
    embedding_base_url: str = "https://api.siliconflow.cn/v1"
    embedding_api_key: str = ""
    embedding_model: str = "BAAI/bge-m3"
    embedding_dimension: int = 1024


settings = Settings()
