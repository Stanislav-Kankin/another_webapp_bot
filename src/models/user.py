from tortoise import fields
from tortoise.models import Model


class User(Model):
    id = fields.BigIntField(pk=True)
    username = fields.CharField(max_length=32, null=True)
    luckyboxes = fields.JSONField(default={"count": 0, "cash": 0})
    next_usage = fields.DatetimeField(null=True)
    number_of_tries = fields.IntField(default=3, null=True)
