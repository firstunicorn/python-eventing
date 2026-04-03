eventing.infrastructure.persistence.processed_message_orm
=========================================================

.. py:module:: eventing.infrastructure.persistence.processed_message_orm

.. autoapi-nested-parse::

   SQLAlchemy ORM model for durable consumer idempotency.



Classes
-------

.. autoapisummary::

   eventing.infrastructure.persistence.processed_message_orm.ProcessedMessageRecord


Module Contents
---------------

.. py:class:: ProcessedMessageRecord

   Bases: :py:obj:`eventing.infrastructure.persistence.orm_base.Base`


   Persist one successfully claimed event identifier per consumer.


   .. py:attribute:: consumer_name
      :type:  sqlalchemy.orm.Mapped[str]


   .. py:attribute:: event_id
      :type:  sqlalchemy.orm.Mapped[str]


   .. py:attribute:: processed_at
      :type:  sqlalchemy.orm.Mapped[datetime.datetime]


