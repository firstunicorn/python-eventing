eventing.infrastructure.messaging.processed_message_store
=========================================================

.. py:module:: eventing.infrastructure.messaging.processed_message_store

.. autoapi-nested-parse::

   Processed-message store contract for durable consumer idempotency.



Classes
-------

.. autoapisummary::

   eventing.infrastructure.messaging.processed_message_store.IProcessedMessageStore


Module Contents
---------------

.. py:class:: IProcessedMessageStore

   Bases: :py:obj:`Protocol`


   Claim inbound event identifiers for one named consumer.


   .. py:method:: claim(*, consumer_name, event_id)
      :async:


      Return whether this consumer may process the given event identifier.



