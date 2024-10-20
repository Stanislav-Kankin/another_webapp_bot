from datetime import datetime
import pytz

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models import User
from config_reader import config

router = Router()


@router.message(CommandStart())
async def start(message: Message, user: User):
    # next_usage = user.next_usage and f"{user.next_usage:%c}"

    markup = None
    dt_time_cmd_start = datetime.now(pytz.utc)
    if 1 <= user.number_of_tries <= 5:
        markup = (
            InlineKeyboardBuilder()
            .button(
                text="🍀 Испытай свою удачу!",
                web_app=WebAppInfo(url=config.WEBAPP_URL))
        ).as_markup()
    elif user.number_of_tries <= 0:
        markup = (
            InlineKeyboardBuilder()
            .button(
                text="🤑 Добавить ящики сейчас(КУПИТЬ)!", callback_data="pay")
            .button(
                text="🥰 Пригласи друга в группу и получишь +1 попытку!", callback_data="friend")
        ).as_markup()

    await message.answer(
        f"🎁 <b>Ящиков открыто:</b> <code>{user.luckyboxes['count']}</code> "
        f"(+<code>{user.luckyboxes['cash']}</code>)\n"
        f"🎲 Осталось ящиков <b>{user.number_of_tries}</b>.\n",

        reply_markup=markup
    )
    user.cmd_str = dt_time_cmd_start
    await user.save()
    if user.number_of_tries < 5 and user.next_usage > user.cmd_str:
        user.number_of_tries = user.number_of_tries
    elif user.number_of_tries < 5 and user.next_usage <= user.cmd_str:
        user.number_of_tries = 5
        await user.save()

    print(f"time 0f use: {user.time_of_use}")
    print(f"next usage: {user.next_usage}")
    print(f"cmd start: {user.cmd_str}")
