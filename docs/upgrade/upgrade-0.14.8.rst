Upgrade to Synnefo v0.14.8
^^^^^^^^^^^^^^^^^^^^^^^^^^

Since v0.14.8, Synnefo ships an example Gunicorn configuration file, that gets
installed automatically at ``/etc/gunicorn.d/synnefo.example``.
To use it you need to do two things:

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
