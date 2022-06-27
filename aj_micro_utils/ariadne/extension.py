from inspect import isawaitable
from typing import Any

from ariadne import graphql
from ariadne.asgi import GraphQL
from ariadne.exceptions import HttpError
from starlette.background import BackgroundTasks
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response

from aj_micro_utils.config import get_settings

DEBUG = get_settings().debug


class DebugBackgroundTasks(BackgroundTasks):
    async def __call__(self) -> None:
        for task in self.tasks:
            if DEBUG:
                await task.func(*task.args, **task.kwargs)
            else:
                await task()


class GraphQLWithBackGroundTasks(GraphQL):
    async def get_context_for_request(self, request: Any) -> Any:
        if callable(self.context_value):
            context = self.context_value(request)
            if isawaitable(context):
                context = await context
            return context

        return self.context_value or {
            "request": request,
            "background": DebugBackgroundTasks(),
        }

    async def graphql_http_server(self, request: Request) -> Response:
        try:
            data = await self.extract_data_from_request(request)
        except HttpError as error:
            return PlainTextResponse(error.message or error.status, status_code=400)

        context_value = await self.get_context_for_request(request)
        extensions = await self.get_extensions_for_request(request, context_value)
        middleware = await self.get_middleware_for_request(request, context_value)

        success, response = await graphql(
            self.schema,
            data,
            context_value=context_value,
            root_value=self.root_value,
            validation_rules=self.validation_rules,
            debug=self.debug,
            introspection=self.introspection,
            logger=self.logger,
            error_formatter=self.error_formatter,
            extensions=extensions,
            middleware=middleware,
        )
        status_code = 200 if success else 400
        background = context_value.get("background")
        headers = {"Connection": "keep-alive"}

        return JSONResponse(
            response, status_code=status_code, background=background, headers=headers
        )
