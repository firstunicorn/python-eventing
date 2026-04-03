eventing.core.contracts.event_registry
======================================

.. py:module:: eventing.core.contracts.event_registry

.. autoapi-nested-parse::

   Registry for mapping event type identifiers to event classes.



Exceptions
----------

.. autoapisummary::

   eventing.core.contracts.event_registry.UnknownEventTypeError


Classes
-------

.. autoapisummary::

   eventing.core.contracts.event_registry.EventRegistry


Module Contents
---------------

.. py:exception:: UnknownEventTypeError

   Bases: :py:obj:`KeyError`


   Raised when an event type cannot be resolved by the registry.


.. py:class:: EventRegistry

   Store event type to model mappings for deserialization.


   .. py:method:: register(event_class, *, event_type = None)

      Register an event class by explicit or model-declared event type.



   .. py:method:: register_many(event_classes)

      Register multiple event classes in insertion order.



   .. py:method:: get(event_type)

      Return the registered event class for the given type.



   .. py:method:: deserialize(payload)

      Build an event instance from a serialized payload.



