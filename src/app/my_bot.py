
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from app.middlewares import UserMiddleware
from config_reader import config
from aiogram.enums import ParseMode

bot = Bot(
    token=config.BOT_TOKEN.get_secret_value(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
dp.message.middleware(UserMiddleware())
