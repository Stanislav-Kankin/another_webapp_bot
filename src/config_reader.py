import os

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

current_dir = os.path.dirname(os.path.abspath(__file__))


class Config(BaseSettings):
    BOT_TOKEN: SecretStr
    DB_URL: SecretStr

    WEBAPP_URL: str = "https://fruity-clocks-vanish.loca.lt"  #ТУННЕЛЬ

    CURRENT_DIR: str = os.path.dirname(os.path.abspath(__file__))
    TEMPLATES_PATH: str = os.path.join(current_dir, "web", "templates")
    STATIC_PATH: str = os.path.join(current_dir, "web", "static")

    model_config = SettingsConfigDict(
        env_file=os.path.join(current_dir, ".env"),
        env_file_encoding="utf-8"
    )


config = Config()
