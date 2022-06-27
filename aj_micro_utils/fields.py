import functools
from datetime import datetime, timezone
from typing import Any, Optional, List, Union

from tortoise import fields, ConfigurationError
from tortoise.exceptions import FieldError
from tortoise.fields import Field
from tortoise.fields.data import JsonLoadsFunc, JSON_LOADS, JSON_DUMPS, JsonDumpsFunc

try:
    from ciso8601 import parse_datetime
except ImportError:  # pragma: nocoverage
    from iso8601 import parse_date

    parse_datetime = functools.partial(parse_date, default_timezone=None)


class ArrayIntField(Field):
    class _db_postgres:
        SQL_TYPE = "integer[]"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def to_db_value(
        self, value: Any, instance: "Union[Type[Model], Model]"
    ) -> Optional[List[int]]:
        return value

    def to_python_value(self, value: List[int]) -> Optional[List[int]]:
        return value


class InetField(Field):
    class _db_postgres:
        SQL_TYPE = "inet"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def to_db_value(
        self, value: Any, instance: "Union[Type[Model], Model]"
    ) -> Optional[str]:
        return value

    def to_python_value(self, value: str) -> Optional[str]:
        return value


class CustomDatetimeField(fields.Field, datetime):
    """
    Datetime field.
    ``auto_now`` and ``auto_now_add`` is exclusive.
    You can opt to set neither or only ONE of them.
    ``auto_now`` (bool):
        Always set to ``datetime.utcnow()`` on save.
    ``auto_now_add`` (bool):
        Set to ``datetime.utcnow()`` on first save only.
    """

    skip_to_python_if_native = True
    SQL_TYPE = "TIMESTAMP"

    class _db_postgres:
        SQL_TYPE = "timestamp with time zone"

    def __init__(
        self,
        auto_now: bool = False,
        auto_now_add: bool = False,
        tz: timezone = timezone.utc,
        **kwargs: Any,
    ) -> None:
        if auto_now_add and auto_now:
            raise ConfigurationError("You can choose only 'auto_now' or 'auto_now_add'")
        super().__init__(**kwargs)
        self.auto_now = auto_now
        self.auto_now_add = auto_now | auto_now_add
        self.tz = tz

    def to_python_value(self, value: Any) -> Optional[datetime]:
        if value is None or isinstance(value, datetime):
            return value
        if isinstance(value, int):
            return datetime.fromtimestamp(value, self.tz)
        return parse_datetime(value, default_timezone=self.tz)

    def to_db_value(
        self, value: Optional[datetime], instance: "Union[Type[Model], Model]"
    ) -> Optional[datetime]:
        # Only do this if it is a Model instance, not class. Test for guaranteed instance var
        if hasattr(instance, "_saved_in_db") and (
            self.auto_now
            or (self.auto_now_add and getattr(instance, self.model_field_name) is None)
        ):
            value = datetime.now(self.tz)
            setattr(instance, self.model_field_name, value)
            return value
        return value

    @property
    def constraints(self) -> dict:
        data = {}
        if self.auto_now_add:
            data["readOnly"] = True
        return data


class CustomJSONField(Field, dict, list):  # type: ignore
    """
    JSON field.

    This field can store dictionaries or lists of any JSON-compliant structure.

    You can specify your own custom JSON encoder/decoder, leaving at the default should work well.
    If you have ``python-rapidjson`` installed, we default to using that,
    else the default ``json`` module will be used.

    ``encoder``:
        The custom JSON encoder.
    ``decoder``:
        The custom JSON decoder.

    """

    SQL_TYPE = "TEXT"
    indexable = False

    class _db_postgres:
        SQL_TYPE = "JSONB"

    def __init__(
        self,
        encoder: JsonDumpsFunc = JSON_DUMPS,
        decoder: JsonLoadsFunc = JSON_LOADS,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.encoder = encoder
        self.decoder = decoder

    def to_db_value(
        self,
        value: Optional[Union[dict, list, str]],
        instance: "Union[Type[Model], Model]",
    ) -> Optional[str]:
        if isinstance(value, str):
            try:
                self.encoder(value)
            except Exception:
                raise FieldError(f"Value {value} is invalid json value.")
            return value
        return None if value is None else self.encoder(value)

    def to_python_value(
        self, value: Optional[Union[str, dict, list]]
    ) -> Optional[Union[dict, list]]:
        if isinstance(value, str):
            try:
                return self.decoder(value)
            except Exception:
                raise FieldError(f"Value {value} is invalid json value.")
        return value
