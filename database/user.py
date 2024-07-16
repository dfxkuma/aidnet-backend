import re

from tortoise.models import Model
from tortoise import fields, validators


class User(Model):
    id = fields.UUIDField(pk=True)
    username = fields.CharField(null=False, max_length=100)
    email = fields.CharField(
        null=False,
        max_length=100,
        validators=[
            validators.RegexValidator(
                "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", re.I
            ),
        ],
    )
    hashed_password = fields.CharField(null=False, max_length=100)
    flags = fields.IntField(null=False, default=0)


class UserRegisterCode(Model):
    id = fields.UUIDField(pk=True)
    email = fields.CharField(
        null=False,
        max_length=100,
        validators=[
            validators.RegexValidator(
                "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", re.I
            ),
        ],
    )
    code = fields.CharField(null=False, max_length=6)
    created_at = fields.DatetimeField(auto_now_add=True)
    expired_at = fields.DatetimeField(null=False)
