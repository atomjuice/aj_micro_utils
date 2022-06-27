from tortoise import models, fields
from aj_micro_utils.fields import CustomDatetimeField


class TestModel(models.Model):
    class Meta:
        paginate_on = "created"

    __test__ = False

    id = fields.IntField(pk=True)
    model_name = fields.CharField(max_length=255)
    email = fields.CharField(max_length=255)
    reference = fields.CharField(max_length=35)
    tracking_number = fields.IntField()
    uuid_field = fields.UUIDField()
    created = CustomDatetimeField(auto_now_add=True)


def formatter(obj: "TestModel") -> dict:
    return {
        "id": obj.id,
        "modelName": obj.model_name,
        "email": obj.email,
        "reference": obj.reference,
        "trackingNumber": obj.tracking_number,
        "uuidField": obj.uuid_field,
    }
