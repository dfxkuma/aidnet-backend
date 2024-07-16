from tortoise.models import Model
from tortoise import fields


class Ambulance(Model):
    login_id = fields.IntField(pk=True)
    license_number = fields.CharField(null=False, max_length=10)
    driver = fields.CharField(null=False, max_length=20)
