eventing.infrastructure.outbox.outbox_event_handler
===================================================

.. py:module:: eventing.infrastructure.outbox.outbox_event_handler

.. autoapi-nested-parse::

   In-process handler that writes domain events to the transactional outbox.



Classes
-------

.. autoapisummary::

   eventing.infrastructure.outbox.outbox_event_handler.OutboxEventHandler


Module Contents
---------------

.. py:class:: OutboxEventHandler(repository)

   Bases: :py:obj:`python_domain_events.IDomainEventHandler`\ [\ :py:obj:`eventing.core.contracts.BaseEvent`\ ]


   Persist dispatched domain events into the outbox.


   .. py:method:: handle(event)
      :async:


      Store the event in the outbox repository.



