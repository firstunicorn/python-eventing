eventing.core.contracts.bus.event_bus
=====================================

.. py:module:: eventing.core.contracts.bus.event_bus

.. autoapi-nested-parse::

   Decorator-friendly facade for in-process event dispatch.



Classes
-------

.. autoapisummary::

   eventing.core.contracts.bus.event_bus.EventBus


Module Contents
---------------

.. py:class:: EventBus(*, backend = None, hooks = None, settings = None)

   Provide a higher-level event emitter/subscriber facade.


   .. py:method:: register(event_type, handler, *, handler_name = None)

      Register one handler instance or async callback.



   .. py:method:: subscriber(event_type, *, handler_name = None)

      Register an async callback through a decorator.



   .. py:method:: dispatch(event)
      :async:


      Dispatch one event through the configured backend.



