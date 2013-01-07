.. _i-mq:

Synnefo
-------

:ref:`synnefo <i-synnefo>` ||
:ref:`ns <i-ns>` ||
:ref:`apt <i-apt>` ||
mq ||
:ref:`db <i-db>` ||
:ref:`gunicorn <i-gunicorn>` ||
:ref:`apache <i-apache>` ||
:ref:`astakos <i-astakos>` ||
:ref:`cms <i-cms>` ||
:ref:`pithos <i-pithos>` ||
:ref:`cyclades <i-cyclades>` ||
:ref:`kamaki <i-kamaki>` ||
:ref:`backends <i-backends>`

Message Queue Setup
+++++++++++++++++++

The following apply to ``mq`` node. For the rest of the sections we will refer to
its IP as ``mq.example.com`` .

.. code-block:: console

  # apt-get install rabbitmq-server


Add new administrator user named ``synnefo`` and gets full privileges on all
exchanges:

.. code-block:: console

   # rabbitmqctl add_user synnefo "examle_rabbitmq_passw0rd"
   # rabbitmqctl set_permissions synnefo ".*" ".*" ".*"
   # rabbitmqctl delete_user guest
   # rabbitmqctl set_user_tags synnefo administrator
   # /etc/init.d/rabbitmq-server restart
