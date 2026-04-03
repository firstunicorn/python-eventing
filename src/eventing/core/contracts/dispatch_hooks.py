"""Lifecycle hooks and settings for event dispatch."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from eventing.core.contracts.base_event import BaseEvent


@dataclass(frozen=True, slots=True)
class DispatchTrace:
    """Describe one dispatch lifecycle transition."""

    stage: str
    event: BaseEvent
    backend_name: str
    handler_name: str | None = None
    error: Exception | None = None


DispatchHook = Callable[[DispatchTrace], None]


@dataclass(frozen=True, slots=True)
class DispatchHooks:
    """Optional callbacks for dispatch lifecycle events."""

    on_dispatch: DispatchHook | None = None
    on_success: DispatchHook | None = None
    on_failure: DispatchHook | None = None
    on_disabled: DispatchHook | None = None
    on_debug: DispatchHook | None = None


@dataclass(frozen=True, slots=True)
class DispatchSettings:
    """Configure dispatch behavior."""

    enabled: bool = True
    debug: bool = False
