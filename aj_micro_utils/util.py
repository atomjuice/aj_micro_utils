import ssl
from typing import Union, List
from uuid import UUID

from tortoise import expand_db_url

from aj_micro_utils.config import get_settings


def dict_value_to_key(dict, value):
    for k, v in dict.items():
        if v == value:
            return k


def validate_uuid4(uuid_string):
    try:
        val = UUID(uuid_string, version=4)
    except ValueError:
        return False

    return val.hex == uuid_string.replace("-", "")


def validate_as_uuid4(keys: Union[str, List[str]]):
    def validate_wrapper(func):
        def func_wrapper(*args, **kwargs):

            if len(args) == 0:
                return

            if isinstance(keys, str):
                if kwargs.get(keys, None):
                    if not validate_uuid4(kwargs[keys]):
                        return None
            else:
                for key in keys:
                    if kwargs.get(key, None):
                        if not validate_uuid4(kwargs[key]):
                            return None

            return func(*args, **kwargs)

        return func_wrapper

    return validate_wrapper


def db_url_to_config(
    url: str, ssl: Union[bool, ssl.SSLContext], testing: bool = False
) -> dict:
    expanded = expand_db_url(url, testing)
    expanded["credentials"]["ssl"] = ssl

    return expanded
