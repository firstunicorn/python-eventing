eventing.core.contracts.base_event
==================================

.. py:module:: eventing.core.contracts.base_event

.. autoapi-nested-parse::

   Canonical event base shared across in-process and outbox flows.



Classes
-------

.. autoapisummary::

   eventing.core.contracts.base_event.BaseEvent


Module Contents
---------------

.. py:class:: BaseEvent(/, **data)

   Bases: :py:obj:`python_outbox_core.IOutboxEvent`, :py:obj:`python_domain_events.BaseDomainEvent`


   Bridge event contract for internal dispatching and outbox publishing.


   .. py:attribute:: model_config

      Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].


   .. py:attribute:: event_id
      :type:  uuid.UUID
      :value: None



   .. py:attribute:: event_type
      :type:  str
      :value: None



   .. py:attribute:: aggregate_id
      :type:  str
      :value: None



   .. py:attribute:: occurred_at
      :type:  datetime.datetime
      :value: None



   .. py:attribute:: source
      :type:  str
      :value: None



   .. py:attribute:: data_version
      :type:  str
      :value: None



   .. py:attribute:: correlation_id
      :type:  uuid.UUID | None
      :value: None



   .. py:attribute:: causation_id
      :type:  uuid.UUID | None
      :value: None



   .. py:attribute:: metadata
      :type:  dict[str, Any]
      :value: None



   .. py:method:: ensure_utc_timestamp(value)
      :classmethod:


      Normalize event timestamps to UTC and reject naive datetimes.



   .. py:method:: to_message()

      Serialize the event as a JSON-friendly payload.



   .. py:method:: get_partition_key()

      Use aggregate identity as the default broker partition key.



