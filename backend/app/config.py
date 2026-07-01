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

    # 管理員 email（逗號分隔）。這些帳號自動具管理權限，用來啟動第一位管理員。
    admin_emails: str = ""

    # Twilio 語音電話（inbound AI 客服）
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    # 對外公開的後端網址（給 Twilio webhook 回呼，例：https://xxx.onrender.com）。
    # 留空時用 webhook 請求本身的網域組 action URL。
    public_base_url: str = ""
    # 是否驗證 X-Twilio-Signature。正式環境務必 true；本機用 ngrok 測試可設 false。
    twilio_validate_signature: bool = True

    @property
    def ai_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def twilio_enabled(self) -> bool:
        return bool(self.twilio_account_sid and self.twilio_auth_token)


settings = Settings()
