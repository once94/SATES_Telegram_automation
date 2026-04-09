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

    # Admin
    ADMIN_TELEGRAM_IDS: list[int] = []

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
