.. _i-apt:

Synnefo
-------

:ref:`synnefo <i-synnefo>` ||
:ref:`ns <i-ns>` ||
apt ||
:ref:`mq <i-mq>` ||
:ref:`db <i-db>` ||
:ref:`gunicorn <i-gunicorn>` ||
:ref:`apache <i-apache>` ||
:ref:`webproject <i-webproject>` ||
:ref:`astakos <i-astakos>` ||
:ref:`qh <i-qh>` ||
:ref:`cms <i-cms>` ||
:ref:`pithos <i-pithos>` ||
:ref:`cyclades <i-cyclades>` ||
:ref:`kamaki <i-kamaki>` ||
:ref:`backends <i-backends>`

APT Setup
+++++++++

The following apply to ``synnefo`` nodes.

To be able to download all synnefo components, you need to add the following
lines in `/etc/apt/sources.list.d/synnefo.list` file:

.. code-block:: console

    deb http://apt.dev.grnet.gr squeeze main
    deb-src http://apt.dev.grnet.gr squeeze main
    deb http://apt.dev.grnet.gr squeeze-backports main
    deb-src http://apt.dev.grnet.gr squeeze-backports main
    deb http://backports.debian.org/debian-backports squeeze-backports main
    deb http://www.rabbitmq.com/debian/ testing main

Import the additional repos' GPG key and get the packages list:

.. code-block:: console

   # wget http://www.rabbitmq.com/rabbitmq-signing-key-public.asc
   # apt-key add rabbitmq-signing-key-public.asc
   # curl https://dev.grnet.gr/files/apt-grnetdev.pub | apt-key add -
   # apt-get update


Test your Setup:
++++++++++++++++

.. code-block:: console

   apt-cache policy synnefo
