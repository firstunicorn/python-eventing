eventing.core.contracts.bus.backends
====================================

.. py:module:: eventing.core.contracts.bus.backends

.. autoapi-nested-parse::

   Dispatch backend abstractions for the event bus facade.



Classes
-------

.. autoapisummary::

   eventing.core.contracts.bus.backends.DispatchBackend
   eventing.core.contracts.bus.backends.SequentialDispatchBackend


Module Contents
---------------

.. py:class:: DispatchBackend

   Bases: :py:obj:`Protocol`


   Execute one dispatch strategy.


   .. py:attribute:: name
      :type:  str


   .. py:method:: invoke(event, handlers, invoke_one)
      :async:


      Run the provided handlers for one event.



.. py:class:: SequentialDispatchBackend

   Dispatch handlers sequentially in registration order.


   .. py:attribute:: name
      :value: 'sequential'



   .. py:method:: invoke(event, handlers, invoke_one)
      :async:



