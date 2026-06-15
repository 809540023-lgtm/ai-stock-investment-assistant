from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    finmind_token: str = ""
    secret_key: str = "dev-secret-change-me"
    frontend_origin: str = "http://localhost:5173"

    database_url: str = "sqlite:///./app.db"
    access_token_expire_minutes: int = 60 * 24 * 7

    @property
    def ai_enabled(self) -> bool:
        return bool(self.anthropic_api_key)


settings = Settings()
