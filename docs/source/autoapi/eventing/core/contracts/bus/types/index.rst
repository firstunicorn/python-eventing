eventing.core.contracts.bus.types
=================================

.. py:module:: eventing.core.contracts.bus.types

.. autoapi-nested-parse::

   Type aliases and lightweight records for event-bus dispatch.



Attributes
----------

.. autoapisummary::

   eventing.core.contracts.bus.types.EventCallback
   eventing.core.contracts.bus.types.HandlerLike


Classes
-------

.. autoapisummary::

   eventing.core.contracts.bus.types.RegisteredHandler


Module Contents
---------------

.. py:data:: EventCallback

.. py:data:: HandlerLike

.. py:class:: RegisteredHandler

   Store one registered callback with its display name.


   .. py:attribute:: name
      :type:  str


   .. py:attribute:: callback
      :type:  EventCallback


