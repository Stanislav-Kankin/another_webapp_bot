from random import randint
from datetime import datetime, timedelta
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
            return await event.answer("You need to set your username to use this bot.")

        user = await User.get_or_create(id=event.from_user.id, username=event.from_user.username)
        data["user"] = user[0]
        return await handler(event, data)


async def lifespan(app: FastAPI):
    await bot.set_webhook(
        url=f"{config.WEBAPP_URL}/webhook",
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
    )

    await Tortoise.init(db_url=config.DB_URL.get_secret_value(), modules={"models": ["models"]})
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
    next_usage = user.next_usage and f"{user.next_usage:%c}"

    markup = None
    if not next_usage or (datetime.utcnow() + timedelta(hours=1)) < tz.make_naive(user.next_usage):
        markup = (
            InlineKeyboardBuilder()
            .button(text="🍀 Try your luck", web_app=WebAppInfo(url=config.WEBAPP_URL))
        ).as_markup()

    await message.answer(
        f"🎁 <b>Your opened lucky boxes:</b> <code>{user.luckyboxes['count']}</code> "
        f"(+<code>{user.luckyboxes['cash']}</code>)\n"
        f"🕐 <b>Next opening in:</b> <i>{next_usage or 'You can open it right now!'}</i>",
        reply_markup=markup
    )


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
    
    current_datetime = datetime.utcnow()
    add_1h = current_datetime + timedelta(hours=1)

    cash = randint(0, 1000)
    user = await User.filter(id=data.user.id).first()

    if user.next_usage and add_1h > tz.make_naive(user.next_usage):
        return JSONResponse({"success": False, "error": "You can't open box now.", "cash": -1})

    user.luckyboxes["count"] += 1
    user.luckyboxes["cash"] += cash
    user.next_usage = add_1h
    await user.save()

    return JSONResponse({"success": True, "cash": cash})


@app.post("/webhook")
async def webhook(request: Request):
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)


if __name__ == "__main__":
    uvicorn.run(app)