eventing.infrastructure.messaging.kafka_consumer_base
=====================================================

.. py:module:: eventing.infrastructure.messaging.kafka_consumer_base

.. autoapi-nested-parse::

   Idempotent consumer base backed by a durable processed-message store.



Classes
-------

.. autoapisummary::

   eventing.infrastructure.messaging.kafka_consumer_base.IdempotentConsumerBase


Module Contents
---------------

.. py:class:: IdempotentConsumerBase(*, consumer_name, processed_message_store)

   Bases: :py:obj:`abc.ABC`


   Skip duplicate events by identifier using a durable processed-message store.


   .. py:method:: consume(message)
      :async:


      Process a message once, returning whether work was performed.



   .. py:method:: handle_event(message)
      :abstractmethod:

      :async:


      Handle one deserialized event payload.



