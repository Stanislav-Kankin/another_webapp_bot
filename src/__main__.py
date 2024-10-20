from random import randint
from datetime import datetime, timedelta
import pytz

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, Update, WebAppInfo

from aiogram.enums import ParseMode

from aiogram.utils.web_app import safe_parse_webapp_init_data

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from tortoise import Tortoise
import uvicorn

from models import User
from config_reader import config

from app.middlewares import UserMiddleware
from app.api import App
from app.handlers import router


bot = Bot(
    token=config.BOT_TOKEN.get_secret_value(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

app = App(bot, dp)
templates = Jinja2Templates(directory=config.TEMPLATES_PATH)

dp.message.middleware(UserMiddleware())
app.mount("/static", StaticFiles(directory=config.STATIC_PATH), name="static")


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/open-box")
async def open_box(request: Request):
    authorization = request.headers.get("Authentication")
    try:
        data = safe_parse_webapp_init_data(bot.token, authorization)
    except ValueError:
        return JSONResponse({"success": False, "error": "Unauthorized"}, 401)

    dt_current_datetime = datetime.now(pytz.utc)
    dt_next_use = dt_current_datetime + timedelta(seconds=10)

    i_cash = randint(0, 1000)
    user = await User.filter(id=data.user.id).first()

    if user.number_of_tries == 0:
    # if user.next_usage and add_1h < tz.make_naive(user.next_usage):  # заменил тут знак
        return JSONResponse(
            {"success": False,
             "error": "Невозможно открыть сейчас. 😢",
             "cash": -1}
            )

    user.luckyboxes["count"] += 1
    user.luckyboxes["cash"] += i_cash
    user.number_of_tries -= 1
    user.time_of_use = dt_current_datetime
    user.next_usage = dt_next_use

    await user.save()

    return JSONResponse({"success": True, "cash": i_cash})


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


@app.post("/webhook")
async def webhook(request: Request):
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)


if __name__ == "__main__":
    uvicorn.run(app)
