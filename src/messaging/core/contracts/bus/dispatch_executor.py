"""Handler invocation and error handling for event dispatch.

This module provides the `DispatchExecutor` which invokes event handlers
with tracing and error handling. It emits lifecycle hooks before, during,
and after handler execution.

See also
--------
- messaging.core.contracts.bus.event_bus : The EventBus that uses this executor
- messaging.core.contracts.dispatch_hooks : Lifecycle hooks emitted during dispatch
"""

from __future__ import annotations

from messaging.core.contracts.base_event import BaseEvent
from messaging.core.contracts.bus.types import RegisteredHandler
from messaging.core.contracts.dispatch_hooks import DispatchHooks, DispatchTrace


class DispatchExecutor:
    """Execute handlers with tracing and error handling."""

    def __init__(self, hooks: DispatchHooks, backend_name: str) -> None:
        """Initialize the executor with hooks and backend name.

        Parameters
        ----------
        hooks : DispatchHooks
            Lifecycle hooks to emit during dispatch
        backend_name : str
            Name of the dispatch backend for tracing
        """
        self._hooks = hooks
        self._backend_name = backend_name

    async def invoke_handler(
        self,
        event: BaseEvent,
        handler: RegisteredHandler,
    ) -> None:
        """Invoke one handler with tracing and error handling.

        This method emits on_dispatch before invocation, then either on_success
        or on_failure after the handler completes. Exceptions are re-raised
        after hooks are emitted.

        Parameters
        ----------
        event : BaseEvent
            The event being dispatched
        handler : RegisteredHandler
            The registered handler to invoke

        Raises
        ------
        Exception
            Any exception raised by the handler is re-raised after logging
        """
        dispatch_trace = DispatchTrace("dispatch", event, self._backend_name, handler.name)
        self._emit_hook("on_dispatch", dispatch_trace)

        try:
            await handler.callback(event)
        except Exception as error:
            self._emit_hook(
                "on_failure",
                DispatchTrace("failure", event, self._backend_name, handler.name, error),
            )
            raise

        self._emit_hook(
            "on_success",
            DispatchTrace("success", event, self._backend_name, handler.name),
        )

    def _emit_hook(self, attribute: str, trace: DispatchTrace) -> None:
        """Emit a lifecycle hook if configured."""
        hook = getattr(self._hooks, attribute)
        if hook is not None:
            hook(trace)
