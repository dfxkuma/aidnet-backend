from tortoise.models import Model
from tortoise import fields


class Hospital(Model):
    login_id = fields.IntField(pk=True)
    name = fields.CharField(null=False, max_length=100)
    address = fields.CharField(null=False, max_length=100)
    medical_staff = fields.JSONField(
        default=[
            {"name": "정신병좌", "position": "정신의학과"},
        ]
    )
