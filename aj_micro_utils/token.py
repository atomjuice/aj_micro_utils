from typing import List, Union

import jwt
from jwt import ExpiredSignatureError, DecodeError

from aj_micro_utils.config import get_settings


def decode_jwt():
    def decode_wrapper(func):
        def func_wrapper(*args, **kwargs):

            if len(args) == 0:
                return

            request = args[1].context["request"]
            token = request.headers.get("Authorization", None)

            if token is None:
                return

            try:
                decoded_data = jwt.decode(
                    token,
                    get_settings().jwt_gateway_secret,
                    algorithms=["HS256"],
                    options={
                        "verify_signature": True,
                        "verify_exp": True,
                        "require_exp": True,
                    },
                )
            except ExpiredSignatureError:
                return
            except DecodeError:
                return

            return func(token_data=decoded_data, *args, **kwargs)

        return func_wrapper

    return decode_wrapper


def loop_roles(user_roles, role: str, service: str = None):
    """Function used internally by has_role to loop the user roles"""
    for ur in user_roles:
        if ur["name"] == role:
            if not service:
                return True

            if ur["service"] == service:
                return True

    return False


def has_role(user_roles, roles: Union[str, List[str]], service: str = None):
    if isinstance(roles, str):
        return loop_roles(user_roles, roles, service)

    for role in roles:
        if loop_roles(user_roles, role, service):
            return True

    return False


def require_role(roles: Union[str, List[str]], service: str = None):
    """Check if the data token contains one of the roles in the list or has the singular role"""

    def check_wrapper(func):
        def func_wrapper(*args, **kwargs):

            if kwargs.get("token_data", None) is None:
                return None

            if has_role(kwargs["token_data"]["roles"], roles, service=service):
                return func(*args, **kwargs)

            return {
                "success": False,
                "error": "You do not have permission to perform this action",
            }

        return func_wrapper

    return check_wrapper
