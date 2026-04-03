eventing.core.contracts.dispatch_hooks
======================================

.. py:module:: eventing.core.contracts.dispatch_hooks

.. autoapi-nested-parse::

   Lifecycle hooks and settings for event dispatch.



Attributes
----------

.. autoapisummary::

   eventing.core.contracts.dispatch_hooks.DispatchHook


Classes
-------

.. autoapisummary::

   eventing.core.contracts.dispatch_hooks.DispatchTrace
   eventing.core.contracts.dispatch_hooks.DispatchHooks
   eventing.core.contracts.dispatch_hooks.DispatchSettings


Module Contents
---------------

.. py:class:: DispatchTrace

   Describe one dispatch lifecycle transition.


   .. py:attribute:: stage
      :type:  str


   .. py:attribute:: event
      :type:  eventing.core.contracts.base_event.BaseEvent


   .. py:attribute:: backend_name
      :type:  str


   .. py:attribute:: handler_name
      :type:  str | None
      :value: None



   .. py:attribute:: error
      :type:  Exception | None
      :value: None



.. py:data:: DispatchHook

.. py:class:: DispatchHooks

   Optional callbacks for dispatch lifecycle events.


   .. py:attribute:: on_dispatch
      :type:  DispatchHook | None
      :value: None



   .. py:attribute:: on_success
      :type:  DispatchHook | None
      :value: None



   .. py:attribute:: on_failure
      :type:  DispatchHook | None
      :value: None



   .. py:attribute:: on_disabled
      :type:  DispatchHook | None
      :value: None



   .. py:attribute:: on_debug
      :type:  DispatchHook | None
      :value: None



.. py:class:: DispatchSettings

   Configure dispatch behavior.


   .. py:attribute:: enabled
      :type:  bool
      :value: True



   .. py:attribute:: debug
      :type:  bool
      :value: False



