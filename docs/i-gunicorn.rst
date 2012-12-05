.. _i-gunicorn:

Synnefo
-------

:ref:`synnefo <i-synnefo>` ||
:ref:`ns <i-ns>` ||
:ref:`apt <i-apt>` ||
:ref:`mq <i-mq>` ||
:ref:`db <i-db>` ||
gunicorn ||
:ref:`apache <i-apache>` ||
:ref:`webproject <i-webproject>` ||
:ref:`astakos <i-astakos>` ||
:ref:`cms <i-cms>` ||
:ref:`pithos <i-pithos>` ||
:ref:`cyclades <i-cyclades>` ||
:ref:`kamaki <i-kamaki>` ||
:ref:`backends <i-backends>`

Gunicorn Setup
++++++++++++++

The following apply to ``astakos``, ``pithos``, ``cyclades`` and ``cms`` nodes.

.. code-block:: console

  # apt-get install -t squeeze-backports gunicorn

In `/etc/gunicorn.d/synnefo` add:

.. code-block:: console

   CONFIG = {
    'mode': 'django',
    'environment': {
      'DJANGO_SETTINGS_MODULE': 'synnefo.settings',
    },
    'working_dir': '/etc/synnefo',
    'user': 'www-data',
    'group': 'www-data',
    'args': (
      '--bind=127.0.0.1:8080',
      '--workers=4',
      '--log-level=debug',
    ),
   }
