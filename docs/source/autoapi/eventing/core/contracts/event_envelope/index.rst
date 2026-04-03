eventing.core.contracts.event_envelope
======================================

.. py:module:: eventing.core.contracts.event_envelope

.. autoapi-nested-parse::

   CloudEvents envelope formatting helpers.



Classes
-------

.. autoapisummary::

   eventing.core.contracts.event_envelope.EventEnvelopeFormatter


Module Contents
---------------

.. py:class:: EventEnvelopeFormatter(default_source = None, data_content_type = 'application/json')

   Format canonical events as CloudEvents 1.0 payloads.


   .. py:method:: format(event)

      Return a CloudEvents envelope for the given event.



   .. py:method:: get_content_type()

      Return the content type produced by the underlying formatter.



