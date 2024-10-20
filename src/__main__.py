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

from tortoise import Tortoise, timezone as tz
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
async def start(message: Message, user: User, request: Request):
    # next_usage = user.next_usage and f"{user.next_usage:%c}"
    authorization = request.headers.get("Authentication")
    data = safe_parse_webapp_init_data(bot.token, authorization)
    user = await User.filter(id=data.user.id).first()
    markup = None
    time_cmd_start = datetime.now(pytz.utc)
    if user.number_of_tries:
    # if not next_usage or (datetime.utcnow() + timedelta(seconds=30)) < tz.make_naive(user.next_usage) and user.number_of_tries != 0:
        markup = (
            InlineKeyboardBuilder()
            .button(
                text="🍀 Испытай свою удачу!",
                web_app=WebAppInfo(url=config.WEBAPP_URL))
        ).as_markup()

    await message.answer(
        f"🎁 <b>Ящиков открыто:</b> <code>{user.luckyboxes['count']}</code> "
        f"(+<code>{user.luckyboxes['cash']}</code>)\n"
        f"🎲 Осталось ящиков <b>{user.number_of_tries}</b>.\n",
        # f"⚙ время тест: {time_is_now}\n"
        # f"Delta + time = {datetime.now(pytz.utc) + timedelta(seconds=10)}",
        # f"🕐 <b>Следующее возможное октрытие:</b> <i>{user.number_of_tries or 'Можешь открыть сейчас!'}</i>",
        reply_markup=markup
    )
    user.cmd_str = time_cmd_start
    user.save()
    await chek_tries_time()
    print(f"time 0f use: {user.time_of_use}")
    print(f"next usage: {user.next_usage}")
    print(f"cmd start: {user.cmd_str}")


async def chek_tries_time(request: Request):
    authorization = request.headers.get("Authentication")
    data = safe_parse_webapp_init_data(bot.token, authorization)
    user = await User.filter(id=data.user.id).first()
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

    current_datetime = datetime.now(pytz.utc)
    next_use = current_datetime + timedelta(seconds=10)

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
    user.time_of_use = current_datetime
    user.next_usage = next_use
    if user.number_of_tries < 5 and user.next_usage > user.time_of_use:
        user.number_of_tries = user.number_of_tries
    elif user.number_of_tries < 5 and user.next_usage <= user.time_of_use:
        user.number_of_tries = 5
    print(current_datetime)
    print(next_use)
    await user.save()
    # await chek_tries_time(request=request)

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
