from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Update

from aiogram.enums import ParseMode


from tortoise import Tortoise
import uvicorn

from config_reader import config

from app.middlewares import UserMiddleware
from app.api import app
from app.handlers import router


bot = Bot(
    token=config.BOT_TOKEN.get_secret_value(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
dp.message.middleware(UserMiddleware())


async def main():
    dp.include_router(router)
    await bot.set_webhook(
        url=f"{config.WEBAPP_URL}/webhook",
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
    )

    await Tortoise.init(
        db_url=config.DB_URL.get_secret_value(),
        modules={"models": ["models"]}
        )
    await Tortoise.generate_schemas()

    await bot.session.close()


if __name__ == "__main__":
    uvicorn.run(app)
