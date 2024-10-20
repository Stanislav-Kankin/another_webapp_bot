

from tortoise import Tortoise
import uvicorn

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

from config_reader import config


from app.api import api_router, lifespan
from app.handlers import router


from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from app.middlewares import UserMiddleware
from aiogram.enums import ParseMode


bot = Bot(
    token=config.BOT_TOKEN.get_secret_value(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
dp.message.middleware(UserMiddleware())


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(
    directory=config.STATIC_PATH), name="static"
    )
templates = Jinja2Templates(directory=config.TEMPLATES_PATH)
app.include_router(api_router)


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


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
