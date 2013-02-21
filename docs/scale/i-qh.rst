.. _i-qh:

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
qh ||
:ref:`cms <i-cms>` ||
:ref:`pithos <i-pithos>` ||
:ref:`cyclades <i-cyclades>` ||
:ref:`kamaki <i-kamaki>` ||
:ref:`backends <i-backends>`

Quataholder Setup
+++++++++++++++++

The following apply to ``qh`` node. In the following sections
we will refer to its IP as ``qh.example.com`` . Make sure
you have db, mq, astakos, apache and gunicorn setup already.

First install the corresponding package:

.. code-block:: console

   # apt-get install snf-quotaholder-app

In `/etc/synnefo/quotaholder.conf` add:

.. code-block:: console

   QUOTAHOLDER_TOKEN = '1234'

and then run:

   # /etc/init.d/gunicorn restart
   # snf-manage syncdb --noinput


Test your Setup:
++++++++++++++++

Visit ``http://accounts.example.com/im/`` and login with your credentials and see
current usage.
