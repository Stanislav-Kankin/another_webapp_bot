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

    markup = None
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
        # f"🕐 <b>Следующее возможное октрытие:</b> <i>{user.number_of_tries or 'Можешь открыть сейчас!'}</i>",
        reply_markup=markup
    )


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/open-box")
async def open_box(request: Request):
    # Проверка авторизации
    # ...

    # Получение текущего времени
    current_datetime = datetime.utcnow()

    # Получение пользователя
    user = await User.filter(id=data.user.id).first()

    # Проверка количества ящиков
    if user.luckyboxes['count'] >= 5:
        # Если ящиков больше или равно 5, проверяем время следующего открытия
        if user.next_usage and current_datetime < tz.make_naive(user.next_usage):
            return JSONResponse({"success": False, "error": "Невозможно открыть ящик сейчас. Попробуйте позже."})
        else:
            # Если время следующего открытия прошло, рассчитываем время следующего открытия
            next_usage = current_datetime + timedelta(hours=1)
            user.next_usage = next_usage
    else:
        # Если ящиков меньше 5, открываем ящик и увеличиваем счетчики
        cash = randint(0, 1000)
        user.luckyboxes['count'] += 1
        user.luckyboxes['cash'] += cash

    # Сохранение пользователя в базе данных
    await user.save()

    # Возвращаем ответ
    return JSONResponse({"success": True, "cash": cash})




@app.post("/webhook")
async def webhook(request: Request):
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)


if __name__ == "__main__":
    uvicorn.run(app)
