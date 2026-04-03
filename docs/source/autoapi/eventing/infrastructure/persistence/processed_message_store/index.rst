eventing.infrastructure.persistence.processed_message_store
===========================================================

.. py:module:: eventing.infrastructure.persistence.processed_message_store

.. autoapi-nested-parse::

   SQLAlchemy processed-message store for durable consumer idempotency.



Classes
-------

.. autoapisummary::

   eventing.infrastructure.persistence.processed_message_store.SqlAlchemyProcessedMessageStore


Module Contents
---------------

.. py:class:: SqlAlchemyProcessedMessageStore(session)

   Bases: :py:obj:`eventing.infrastructure.messaging.IProcessedMessageStore`


   Claim inbound event identifiers inside the caller's transaction.


   .. py:method:: claim(*, consumer_name, event_id)
      :async:


      Return whether this consumer may process the given event identifier.



