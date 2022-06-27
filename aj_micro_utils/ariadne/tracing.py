from copy import deepcopy
from functools import partial
from inspect import isawaitable
from typing import Any, Callable, Dict, Optional

from ariadne.types import ContextValue, Extension, Resolver
from ariadne.contrib.tracing.utils import format_path, should_trace
from graphql import GraphQLResolveInfo
from newrelic.agent import (
    set_transaction_name,
    end_of_transaction,
    add_custom_span_attribute,
    FunctionTrace,
)

ArgFilter = Callable[[Dict[str, Any], GraphQLResolveInfo], Dict[str, Any]]


class NewRelicExtension(Extension):
    _arg_filter: Optional[ArgFilter]

    def __init__(self, *, arg_filter: Optional[ArgFilter] = None):
        self._arg_filter = arg_filter

    def request_started(self, context: ContextValue):
        set_transaction_name("GraphQL Query")

    def request_finished(self, context: ContextValue):
        end_of_transaction()

    async def resolve(
        self, next_: Resolver, parent: Any, info: GraphQLResolveInfo, **kwargs
    ):
        if not should_trace(info):
            result = next_(parent, info, **kwargs)
            if isawaitable(result):
                result = await result
            return result

        with FunctionTrace(info.field_name, label="graphql") as trace:
            add_custom_span_attribute("graphql.parentType", info.parent_type.name)

            graphql_path = ".".join(
                map(str, format_path(info.path))  # pylint: disable=bad-builtin
            )
            add_custom_span_attribute("graphql.path", graphql_path)

            if kwargs:
                filtered_kwargs = self.filter_resolver_args(kwargs, info)
                for kwarg, value in filtered_kwargs.items():
                    add_custom_span_attribute(f"graphql.param.{kwarg}", value)

            result = next_(parent, info, **kwargs)
            if isawaitable(result):
                result = await result
            return result

    def filter_resolver_args(
        self, args: Dict[str, Any], info: GraphQLResolveInfo
    ) -> Dict[str, Any]:
        if not self._arg_filter:
            return args

        return self._arg_filter(deepcopy(args), info)


class NewRelicExtensionSync(NewRelicExtension):
    def resolve(
        self, next_: Resolver, parent: Any, info: GraphQLResolveInfo, **kwargs
    ):  # pylint: disable=invalid-overridden-method
        if not should_trace(info):
            result = next_(parent, info, **kwargs)
            return result

        with FunctionTrace(info.field_name, label="graphql") as scope:
            add_custom_span_attribute("graphql.parentType", info.parent_type.name)

            graphql_path = ".".join(
                map(str, format_path(info.path))  # pylint: disable=bad-builtin
            )
            add_custom_span_attribute("graphql.path", graphql_path)

            if kwargs:
                filtered_kwargs = self.filter_resolver_args(kwargs, info)
                for kwarg, value in filtered_kwargs.items():
                    add_custom_span_attribute(f"graphql.param.{kwarg}", value)

            result = next_(parent, info, **kwargs)
            return result


def newrelic_extension(*, arg_filter: Optional[ArgFilter] = None):
    return partial(NewRelicExtension, arg_filter=arg_filter)


def newrelic_extension_sync(*, arg_filter: Optional[ArgFilter] = None):
    return partial(NewRelicExtensionSync, arg_filter=arg_filter)
