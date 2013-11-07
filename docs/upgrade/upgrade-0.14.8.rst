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

Finally, add any other special configuration option needed by your deployment in
this file.
