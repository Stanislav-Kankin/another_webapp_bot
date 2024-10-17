from tortoise import fields
from tortoise.models import Model


class User(Model):
    id = fields.BigIntField(pk=True)
    username = fields.CharField(max_length=32, null=True)
    luckyboxes = fields.JSONField(default={"count": 0, "cash": 0})
    time_of_use = fields.DatetimeField(null=True)
    next_usage = fields.DatetimeField(null=True)
    number_of_tries = fields.IntField(default=5, null=True)
    cmd_str = fields.DatetimeField(null=True)
