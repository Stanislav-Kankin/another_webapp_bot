from random import randint
from datetime import datetime, timedelta
import pytz
from typing import Callable, Awaitable, Any

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, Update, WebAppInfo
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.web_app import safe_parse_webapp_init_data

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from tortoise import Tortoise
import uvicorn

from models import User
from config_reader import config


class UserMiddleware(BaseMiddleware):

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any]
    ) -> Any:
        if not event.from_user.username:
            return await event.answer(
                "Нужно задать имя пользователя чтобы использовать бот."
                )

        user = await User.get_or_create(
            id=event.from_user.id, username=event.from_user.username
            )
        data["user"] = user[0]
        return await handler(event, data)


async def lifespan(app: FastAPI):
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
    yield
    await Tortoise.close_connections()
    await bot.session.close()

bot = Bot(
    token=config.BOT_TOKEN.get_secret_value(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory=config.TEMPLATES_PATH)

dp.message.middleware(UserMiddleware())
app.mount("/static", StaticFiles(directory=config.STATIC_PATH), name="static")


@dp.message(CommandStart())
async def start(message: Message, user: User):
    # next_usage = user.next_usage and f"{user.next_usage:%c}"

    dict_markup = None
    dt_time_cmd_start = datetime.now(pytz.utc)
    if 1 <= user.number_of_tries <= 5:
        dict_markup = (
            InlineKeyboardBuilder()
            .button(
                text="🍀 Испытай свою удачу!",
                web_app=WebAppInfo(url=config.WEBAPP_URL))
        ).as_markup()
    elif user.number_of_tries <= 0:
        dict_markup = (
            InlineKeyboardBuilder()
            .button(
                text="🤑 Добавить ящики сейчас(КУПИТЬ)!",
                callback_data="pay")
            .button(
                text="🥰 Пригласи друга в группу и получишь +1 попытку!",
                callback_data="friend")
        ).as_markup()

    await message.answer(
        f"🎁 <b>Ящиков открыто:</b> <code>{user.luckyboxes['count']}</code> "
        f"(+<code>{user.luckyboxes['cash']}</code>)\n"
        f"🎲 Осталось ящиков <b>{user.number_of_tries}</b>.\n",

        reply_markup=dict_markup
    )
    user.cmd_str = dt_time_cmd_start
    await user.save()
    if user.number_of_tries < 5 and user.next_usage > user.cmd_str:
        user.number_of_tries = user.number_of_tries
    elif user.number_of_tries < 5 and user.next_usage <= user.cmd_str:
        user.number_of_tries = 5
        await user.save()


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
