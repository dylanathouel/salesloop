from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str

    # Auth
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # LLM (OpenRouter)
    openrouter_api_key: str = ""
    openrouter_model: str
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2

    # HTTP
    cors_origins: str = "http://localhost:5173"

    # Rate limiting (slowapi format, e.g. "10/minute")
    auth_rate_limit: str = "10/minute"
    rate_limit_enabled: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
