from pydantic import computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Telegram
    BOT_TOKEN: str
    GROUP_CHAT_ID: int

    # Forum topic thread IDs
    TOPIC_AUDITS: int = 0
    TOPIC_ENERGY: int = 0

    # Google Gemini AI
    GOOGLE_API_KEY: str = ""

    # Database
    DB_PATH: str = "data/sates.db"
    DEBUG: bool = False

    # Admin (comma-separated string from env, parsed into list)
    ADMIN_TELEGRAM_IDS: str = ""

    @computed_field
    @property
    def admin_ids(self) -> list[int]:
        if not self.ADMIN_TELEGRAM_IDS:
            return []
        return [int(x.strip()) for x in self.ADMIN_TELEGRAM_IDS.split(",") if x.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
