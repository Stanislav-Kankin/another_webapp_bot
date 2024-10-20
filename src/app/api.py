from tortoise import Tortoise
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config_reader import config


class Api:
    def __init__(self, bot, dp) -> None:
        self.bot = bot
        self.dp = dp

    async def web_app(self):
        app = await FastAPI(lifespan=self.lifespan)
        app.mount("/static", StaticFiles(
            directory=config.STATIC_PATH), name="static"
            )
        return app

    async def lifespan(self, app: FastAPI):
        await self.bot.set_webhook(
            url=f"{config.WEBAPP_URL}/webhook",
            allowed_updates=self.dp.resolve_used_update_types(),
            drop_pending_updastes=True,
        )

        await Tortoise.init(
            db_url=config.DB_URL.get_secret_value(),
            modules={"models": ["models"]}
            )
        await Tortoise.generate_schemas()
        yield
        await Tortoise.close_connections()
        await self.bot.session.close()
