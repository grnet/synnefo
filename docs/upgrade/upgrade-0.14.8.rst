Upgrade to Synnefo v0.14.8
^^^^^^^^^^^^^^^^^^^^^^^^^^

Synnefo v0.14.8 release introduced support for Debian Wheezy (and Django 1.4).
To upgrade from Squeeze to Wheezy you should make sure to change the
``'ENGINE'`` option in ``/etc/synnefo/10-snf-webproject-databases.conf`` to
``'django.db.backends.postgresql_psycopg2``. Replace ``postgresql_psycopg2``
with the DB engine you are using.

If you're upgrading to Synnefo v0.14.8 on Squeeze, you should also make sure to
have the Squezee backports repository installed, since ``snf-webproject``
depends on ``>=python-django-south-0.7.3``, which on Squeeze is only available
from the backports repository.

Since v0.14.8, Synnefo also ships an example Gunicorn configuration file, that
gets installed automatically at ``/etc/gunicorn.d/synnefo.example``.  To use it
you need to do two things:

1. Disable your old configuration file by removing it.
   [if you are upgrading from an older version and you had such a file]

2. Rename the file to ``/etc/gunicorn.d/synnefo`` to make it valid:

.. code-block:: console

    # mv /etc/gunicorn.d/synnefo.example /etc/gunicorn.d/synnefo

Finally, add any other special configuration option needed by your deployment
in this file.

.. warning:: The logging location for the Synnefo gunicorn project has changed in
 /etc/gunicorn.d/synnefo.example: The default configuration no longer stores
 logs under /var/log/gunicorn/synnefo.log, but under
 /var/log/synnefo/gunicorn.log instead, for two reasons:
 a) uniformity with the rest of Synnefo, b) the version of gunicorn included in
 Wheezy now drops privileges to www-data:www-data properly, so it can no longer
 log under /var/log/gunicorn, which is owned by root.
