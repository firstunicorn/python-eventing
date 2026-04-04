# Eventing

[![Documentation Status](https://readthedocs.org/projects/python-eventing/badge/?version=latest)](https://python-eventing.readthedocs.io/en/latest/?badge=latest)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](https://github.com/firstunicorn/python-eventing/actions)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Validate Dependencies](https://github.com/firstunicorn/python-eventing/actions/workflows/validate-dependencies.yml/badge.svg)](https://github.com/firstunicorn/python-eventing/actions/workflows/validate-dependencies.yml)

Package-first universal event infrastructure for microservices.

📚 **[Full Documentation](https://python-eventing.readthedocs.io/en/latest/)** - Comprehensive guides and API reference

Support scale: `❌` none, `✅` basic, `✅✅` strong, `✅✅✅` first-class

| Capability | `python-eventing` | [`pyventus`](https://github.com/mdapena/pyventus) | [`fastapi-events`](https://github.com/melvinkcx/fastapi-events) | Notes |
| --- | --- | --- | --- | --- |
| Transactional outbox | ✅✅✅ | ❌ | ❌ | Durable local DB plus outbox boundary is a core feature here |
| Kafka data plane | ✅✅✅ | ❌ | ❌ | This package is built for Kafka-backed microservice messaging |
| DLQ handling | ✅✅✅ | ❌ | ❌ | Native part of the durable eventing layer here |
| Health checks for eventing runtime | ✅✅✅ | ❌ | ❌ | Outbox and runtime health belong to this package |
| Typed cross-service event contracts | ✅✅ | ✅ | ✅✅ | `python-eventing` and `fastapi-events` are stronger on explicit payload modeling |
| Decorator subscriber registration | ✅✅ | ✅✅✅ | ✅✅ | `EventBus.subscriber(...)` exists now; `pyventus` is still the most polished here |
| In-process dispatch backend abstraction | ✅✅ | ✅✅✅ | ✅ | `DispatchBackend` exists here; `pyventus` offers a broader processor model |
| Lifecycle hooks / callbacks | ✅✅ | ✅✅✅ | ✅ | `DispatchHooks` covers dispatch, success, failure, disabled, and debug |
| Debug / disable controls | ✅✅ | ✅✅ | ✅✅✅ | `DispatchSettings(enabled, debug)` is implemented; `fastapi-events` is strongest for app-level toggling |
| Observability / telemetry polish | ✅ | ✅ | ✅✅✅ | This package is hook-ready; `fastapi-events` has stronger native OTEL support |
| Producer / outbox batch publish | ✅✅✅ | ❌ | ❌ | `ScheduledOutboxWorker` publishes outbox events in batches already |
| Consumer dedup helper | ✅✅✅ | ❌ | ❌ | `IdempotentConsumerBase` now uses a durable processed-message store instead of process memory |
| Durable cross-service idempotency | ✅✅✅ | ❌ | ❌ | `IProcessedMessageStore` plus `SqlAlchemyProcessedMessageStore` provide transactional duplicate protection |
| Consumer batch handling | ❌ | ❌ | ✅✅✅ | `fastapi-events` supports `handle_many(...)`; this package stays one-message-per-consume today |
| FastAPI-local event flow | ❌ | ✅ | ✅✅✅ | This package intentionally avoids request-lifecycle middleware eventing |

## Scope

- Transactional outbox primitives
- Event contracts and registry
- Kafka publishing and consumer base classes
- In-process emitter/subscriber facade and hooks

## Documentation

📖 **[Integration Guide](https://python-eventing.readthedocs.io/en/latest/integration-guide.html)** - Step-by-step integration instructions

🔍 **[API Reference](https://python-eventing.readthedocs.io/en/latest/autoapi/index.html)** - Complete API documentation

📋 **[Event Catalog](https://python-eventing.readthedocs.io/en/latest/event-catalog.html)** - Available event types and contracts

### Key Topics

- [Transactional Outbox Pattern](https://python-eventing.readthedocs.io/en/latest/transactional-outbox.html) - Guaranteed event delivery
- [Idempotent Consumers](https://python-eventing.readthedocs.io/en/latest/consumer-transactions.html) - Duplicate message handling
- [Dead Letter Queue](https://python-eventing.readthedocs.io/en/latest/dlq-handlers.html) - Failed event handling
- [Health Checks](https://python-eventing.readthedocs.io/en/latest/autoapi/eventing/infrastructure/health/index.html) - Monitoring outbox and broker status

## Distribution

- PyPI distribution name: `python-eventing`
- Python import package: `eventing`

Services should consume the published package rather than a source checkout.
Kafka remains shared infrastructure and each participating service uses
local producer/consumer clients.

## Local development

```powershell
poetry install
poetry build
poetry run pytest
```
