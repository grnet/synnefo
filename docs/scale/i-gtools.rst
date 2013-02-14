.. _i-gtools:

Synnefo
-------

:ref:`synnefo <i-synnefo>` ||
:ref:`ns <i-ns>` ||
:ref:`apt <i-apt>` ||
:ref:`mq <i-mq>` ||
:ref:`db <i-db>` ||
:ref:`gunicorn <i-gunicorn>` ||
:ref:`apache <i-apache>` ||
:ref:`webproject <i-webproject>` ||
:ref:`astakos <i-astakos>` ||
:ref:`cms <i-cms>` ||
:ref:`pithos <i-pithos>` ||
:ref:`cyclades <i-cyclades>` ||
:ref:`kamaki <i-kamaki>` ||
:ref:`backends <i-backends>`

Backends
++++++++

:ref:`ganeti <i-ganeti>` ||
:ref:`image <i-image>` ||
gtools ||
:ref:`network <i-network>`

gtools Setup
~~~~~~~~~~~~

The following apply to ``ganeti`` nodes.

.. code-block:: console

   # apt-get install snf-cyclades-gtools

Add this line in `/etc/synnefo/gtools.conf`

.. code-block:: console

   AMQP_HOSTS = ["amqp://synnefo:example_rabbitmq_passw0rd@mq.example.com:5672"]


and enable ``snf-ganeti-eventd``:

.. code-block:: console

   # sed -i 's/false/true/' /etc/default/snf-ganeti-eventd
   # /etc/init.d/snf-ganeti-eventd start



Test your Setup:
++++++++++++++++
