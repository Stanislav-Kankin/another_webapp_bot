import os
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Получаем текущую директорию, где находится этот файл
current_dir = os.path.dirname(os.path.abspath(__file__))


class Config(BaseSettings):
    """
    Класс конфигурации для хранения настроек приложения.
    """

    BOT_TOKEN: SecretStr  # Токен бота
    DB_URL: SecretStr  # URL базы данных

    WEBAPP_URL: str = "https://df04-147-45-193-130.ngrok-free.app"  # URL веб-приложения (туннель)

    CURRENT_DIR: str = os.path.dirname(os.path.abspath(__file__))  # Текущая директория
    TEMPLATES_PATH: str = os.path.join(current_dir, "web", "templates")  # Путь к шаблонам
    STATIC_PATH: str = os.path.join(current_dir, "web", "static")  # Путь к статическим файлам

    model_config = SettingsConfigDict(
        env_file=os.path.join(current_dir, ".env"),  # Путь к файлу с переменными окружения
        env_file_encoding="utf-8"  # Кодировка файла с переменными окружения
    )


# Создаем экземпляр класса Config для использования в приложении
config = Config()
