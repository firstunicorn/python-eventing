"""Decorator-friendly facade for in-process event dispatch.

This module provides the `EventBus` class which acts as the main
emitter and subscriber facade. It wraps the lower-level dispatch backends
and provides decorator registration, tracing, and lifecycle hooks.

See also
--------
- eventing.core.contracts.bus.backends : Dispatch backends used by the bus
- eventing.core.contracts.dispatch_hooks : Lifecycle hooks emitted by the bus
"""

from __future__ import annotations

from collections.abc import Callable

from eventing.core.contracts.base_event import BaseEvent
from eventing.core.contracts.bus.backends import DispatchBackend, SequentialDispatchBackend
from eventing.core.contracts.bus.types import EventCallback, HandlerLike, RegisteredHandler
from eventing.core.contracts.dispatch_hooks import DispatchHooks, DispatchSettings, DispatchTrace


class EventBus:
    """Provide a higher-level event emitter/subscriber facade."""

    def __init__(
        self,
        *,
        backend: DispatchBackend | None = None,
        hooks: DispatchHooks | None = None,
        settings: DispatchSettings | None = None,
    ) -> None:
        self._backend = backend or SequentialDispatchBackend()
        self._hooks = hooks or DispatchHooks()
        self._settings = settings or DispatchSettings()
        self._handlers: dict[type[BaseEvent], list[RegisteredHandler]] = {}

    def register(
        self,
        event_type: type[BaseEvent],
        handler: HandlerLike,
        *,
        handler_name: str | None = None,
    ) -> None:
        """Register one handler instance or async callback."""
        callback = handler.handle if hasattr(handler, "handle") else handler
        name = handler_name or self._resolve_handler_name(handler)
        self._handlers.setdefault(event_type, []).append(RegisteredHandler(name, callback))

    def subscriber(
        self,
        event_type: type[BaseEvent],
        *,
        handler_name: str | None = None,
    ) -> Callable[[EventCallback], EventCallback]:
        """Register an async callback through a decorator."""

        def decorator(callback: EventCallback) -> EventCallback:
            self.register(event_type, callback, handler_name=handler_name or callback.__name__)
            return callback

        return decorator

    async def dispatch(self, event: BaseEvent) -> None:
        """Dispatch one event through the configured backend."""
        handlers = list(self._handlers.get(type(event), []))
        if not self._settings.enabled:
            self._emit("on_disabled", DispatchTrace("disabled", event, self._backend.name))
            return

        async def invoke_one(handler: RegisteredHandler) -> None:
            dispatch_trace = DispatchTrace("dispatch", event, self._backend.name, handler.name)
            self._emit("on_dispatch", dispatch_trace)
            try:
                await handler.callback(event)
            except Exception as error:
                self._emit(
                    "on_failure",
                    DispatchTrace("failure", event, self._backend.name, handler.name, error),
                )
                raise
            self._emit(
                "on_success",
                DispatchTrace("success", event, self._backend.name, handler.name),
            )

        await self._backend.invoke(event, handlers, invoke_one)

    def _emit(self, attribute: str, trace: DispatchTrace) -> None:
        hook = getattr(self._hooks, attribute)
        if hook is not None:
            hook(trace)
        if self._settings.debug and self._hooks.on_debug is not None:
            self._hooks.on_debug(trace)

    @staticmethod
    def _resolve_handler_name(handler: HandlerLike) -> str:
        if hasattr(handler, "handle"):
            return handler.__class__.__name__
        return handler.__name__
