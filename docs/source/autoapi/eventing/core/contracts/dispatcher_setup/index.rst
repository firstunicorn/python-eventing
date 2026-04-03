eventing.core.contracts.dispatcher_setup
========================================

.. py:module:: eventing.core.contracts.dispatcher_setup

.. autoapi-nested-parse::

   Helpers for wiring the in-process event dispatcher.



Classes
-------

.. autoapisummary::

   eventing.core.contracts.dispatcher_setup.HandlerRegistration


Functions
---------

.. autoapisummary::

   eventing.core.contracts.dispatcher_setup.build_dispatcher
   eventing.core.contracts.dispatcher_setup.build_event_bus


Module Contents
---------------

.. py:class:: HandlerRegistration

   Bind an event class to an in-process handler instance.


   .. py:attribute:: event_type
      :type:  type[eventing.core.contracts.base_event.BaseEvent]


   .. py:attribute:: handler
      :type:  python_domain_events.IDomainEventHandler[eventing.core.contracts.base_event.BaseEvent]


.. py:function:: build_dispatcher(registrations)

   Create a dispatcher and register all provided handlers.


.. py:function:: build_event_bus(registrations, *, backend = None, hooks = None, settings = None)

   Create the higher-level event bus from the same registration model.


