"""Decorator-friendly facade for in-process event dispatch.

This module provides the `EventBus` class which acts as the main
emitter and subscriber facade. It coordinates handler resolution,
dispatch execution, and hook emission through specialized components.

See also
--------
- messaging.core.contracts.bus.backends : Dispatch backends used by the bus
- messaging.core.contracts.bus.handler_resolver : Handler name and callback extraction
- messaging.core.contracts.bus.dispatch_executor : Handler invocation logic
- messaging.core.contracts.bus.hook_emitter : Lifecycle hook emission
"""

from __future__ import annotations

from collections.abc import Callable

from messaging.core.contracts.base_event import BaseEvent
from messaging.core.contracts.bus.backends import DispatchBackend, SequentialDispatchBackend
from messaging.core.contracts.bus.dispatch_executor import DispatchExecutor
from messaging.core.contracts.bus.handler_resolver import HandlerResolver
from messaging.core.contracts.bus.hook_emitter import HookEmitter
from messaging.core.contracts.bus.types import EventCallback, HandlerLike, RegisteredHandler
from messaging.core.contracts.dispatch_hooks import DispatchHooks, DispatchSettings, DispatchTrace


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
        hooks_instance = hooks or DispatchHooks()
        settings_instance = settings or DispatchSettings()
        self._settings = settings_instance
        self._hooks_emitter = HookEmitter(hooks_instance, settings_instance)
        self._executor = DispatchExecutor(hooks_instance, self._backend.name)
        self._resolver = HandlerResolver()
        self._handlers: dict[type[BaseEvent], list[RegisteredHandler]] = {}

    def register(
        self,
        event_type: type[BaseEvent],
        handler: HandlerLike,
        *,
        handler_name: str | None = None,
    ) -> None:
        """Register one handler instance or async callback."""
        callback = self._resolver.extract_callback(handler)
        name = handler_name or self._resolver.resolve_name(handler)
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
            self._hooks_emitter.emit("on_disabled", DispatchTrace("disabled", event, self._backend.name))
            return

        async def invoke_one(handler: RegisteredHandler) -> None:
            await self._executor.invoke_handler(event, handler)

        await self._backend.invoke(event, handlers, invoke_one)
