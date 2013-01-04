.. _i-image:

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
image ||
:ref:`gtools <i-gtools>` ||
:ref:`network <i-network>`

snf-image Setup
~~~~~~~~~~~~~~~

The following apply to ``ganeti`` nodes.

.. code-block:: console

   # apt-get install snf-image-host

Append this lines in `/etc/snf-image/default`

.. code-block:: console

    PITHOS_DB="postgresql://synnefo:example_passw0rd@db.example.com:5432/snf_pithos"
    PITHOS_DATA="/srv/pithos/data"
    PROGRESS_MONITOR='snf-progress-monitor'


and create snf-image-helper with:

.. code-block:: console

   # snf-image-update-helper -y


Test your Setup:
++++++++++++++++
