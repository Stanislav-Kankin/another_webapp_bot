from tortoise import Tortoise
from fastapi import FastAPI

from config_reader import config


class App:
    def __init__(self, bot, dp) -> None:
        self.bot = bot
        self.dp = dp

    async def app(self):
        await FastAPI(lifespan=self.lifespan)

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
