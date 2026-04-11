# pylint: disable=too-many-arguments

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from typing import Any

from fastapi import FastAPI

def setup_cors_middleware(
    app: FastAPI,
    allowed_origins: str | list[str],
    allow_credentials: bool = ...,
    allowed_methods: list[str] | None = ...,
    allowed_headers: list[str] | None = ...,
    max_age: int = ...,
) -> None: ...
def setup_error_handlers(
    app: FastAPI,
    custom_exception_class: type[Exception] | None = ...,
) -> None: ...
def create_lifespan_manager(
    on_startup: Callable[[], Awaitable[None]] | None = ...,
    on_shutdown: Callable[[], Awaitable[None]] | None = ...,
    service_name: str = ...,
    service_version: str = ...,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]: ...
def create_health_check_endpoint(
    service_name: str,
    version: str = ...,
    additional_checks: dict[str, Any] | None = ...,
) -> Callable[[], Awaitable[dict[str, Any]]]: ...
