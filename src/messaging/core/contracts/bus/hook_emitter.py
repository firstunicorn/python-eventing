"""Hook emission logic for event bus lifecycle.

This module provides the `HookEmitter` which manages lifecycle hook
emission with optional debug tracing. It wraps DispatchHooks and
DispatchSettings to provide a unified hook emission interface.

See also
--------
- messaging.core.contracts.bus.event_bus : The EventBus that uses this emitter
- messaging.core.contracts.dispatch_hooks : Hook definitions and trace structure
"""

from __future__ import annotations

from messaging.core.contracts.dispatch_hooks import DispatchHooks, DispatchSettings, DispatchTrace


class HookEmitter:
    """Emit lifecycle hooks with debug support."""

    def __init__(self, hooks: DispatchHooks, settings: DispatchSettings) -> None:
        """Initialize the emitter with hooks and settings.

        Parameters
        ----------
        hooks : DispatchHooks
            The lifecycle hooks to emit
        settings : DispatchSettings
            Settings that control hook behavior (debug mode, enabled flag)
        """
        self._hooks = hooks
        self._settings = settings

    def emit(self, attribute: str, trace: DispatchTrace) -> None:
        """Emit a specific hook with optional debug tracing.

        If the hook attribute exists and is not None, it will be invoked.
        If debug mode is enabled, the on_debug hook will also be emitted.

        Parameters
        ----------
        attribute : str
            The hook attribute name (e.g., 'on_dispatch', 'on_success')
        trace : DispatchTrace
            The trace information to pass to the hook
        """
        hook = getattr(self._hooks, attribute)
        if hook is not None:
            hook(trace)
        if self._settings.debug and self._hooks.on_debug is not None:
            self._hooks.on_debug(trace)
