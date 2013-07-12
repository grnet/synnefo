.. _i-pithos:

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
pithos ||
:ref:`cyclades <i-cyclades>` ||
:ref:`kamaki <i-kamaki>` ||
:ref:`backends <i-backends>`


Pithos Setup
++++++++++++

The following apply to ``pithos`` node. For the rest of the sections we will
refer to its IP with FQDN ``pithos.example.com``. Please make sure you have db,
gunicorn, apache, webproject and astakos already setup.


First you must setup an NFS server and export `/srv/pithos` directory.

.. code-block:: console

   # cd /srv/pithos
   # mkdir data
   # chown www-data:www-data data
   # chmod g+ws data
   # apt-get install -t squeeze-backports nfs-kernel-server

Here add these lines in `/etc/exports`:

.. code-block:: console

    /srv/pithos 4.3.2.0/24(rw,sync,no_subtree_check,no_root_squash)
    /srv 4.3.2.0/24(rw,fsid=0,no_subtree_check,sync)


And then install the corresponding package:

.. code-block:: console

   # apt-get install snf-pithos-app

In `/etc/synnefo/pithos.conf` add:

.. code-block:: console

    ASTAKOS_BASE_URL = 'https://accounts.example.com/'

    PITHOS_BACKEND_DB_CONNECTION = 'postgresql://synnefo:example_passw0rd@db.example.com:5432/snf_pithos'
    PITHOS_BACKEND_BLOCK_PATH = '/srv/pithos/data'
    PITHOS_UPDATE_MD5 = False
    PITHOS_SERVICE_TOKEN = 'XXXXXXXXXXX'

    # Set False if astakos & pithos are on the same node
    PITHOS_PROXY_USER_SERVICES = True


Install pithos web UI with:

.. code-block:: console

   # apt-get install snf-pithos-webclient


In `/etc/synnefo/webclient.conf` add:

.. code-block:: console

    CLOUDBAR_LOCATION = 'https://accounts.example.com/static/im/cloudbar/'
    CLOUDBAR_SERVICES_URL = 'https://accounts.example.com/ui/get_services'
    CLOUDBAR_MENU_URL = 'https://accounts.example.com/ui/get_menu'

XXXXXXXXXXXXXX  should be the Pithos token and id found on astakos node by running:

.. code-block:: console

   # snf-manage service-list

After configuration is done, restart services:

.. code-block:: console

   # /etc/init.d/gunicorn restart
   # /etc/init.d/apache2 restart


Test your Setup:
++++++++++++++++

Visit https://pithos.example.com/ui/ and upload files.
