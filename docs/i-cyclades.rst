.. _i-cyclades:

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
cyclades ||
:ref:`kamaki <i-kamaki>` ||
:ref:`backends <i-backends>`

Cyclades Setup
++++++++++++++

The following apply to ``cyclades`` node. In the rest of the sections
we will refer to its IP with FQDN ``cyclades.example.com``.Please make sure you have
db, mq, gunicorn, apache, webproject, pithos and astakos already setup.

Install the corresponding package. Please note that memcache is needed for
versions >= 0.13 :

.. code-block:: console

    # apt-get install memcached
    # apt-get install python-memcache
    # apt-get install snf-cyclades-app

In `/etc/synnefo/cyclades.conf` add:

.. code-block:: console

    MAX_CIDR_BLOCK = 21
    PUBLIC_USE_POOL = True

    CUSTOM_BRIDGED_BRIDGE = 'br0'

    MAX_VMS_PER_USER = 5
    VMS_USER_QUOTA = {
        'user@example.com': 20,
    }
    MAX_NETWORKS_PER_USER = 3
    NETWORKS_USER_QUOTA = { 'user@example.com': 10 }
    GANETI_DISK_TEMPLATES = ('blockdev', 'diskless', 'drbd', 'file', 'plain',
                             'rbd',  'sharedfile', 'ext')
    ASTAKOS_URL = 'https://accounts.example.com/im/authenticate'

    SECRET_ENCRYPTION_KEY= "oEs0pt7Di1mkxA0P6FiK"

    GANETI_CREATEINSTANCE_KWARGS = {
        'os': 'snf-image+default',
        'hvparams': {'serial_console': False, 'security_model': 'pool'},
        'wait_for_sync': False}

    GANETI_USE_HOTPLUG = True
    CLOUDBAR_LOCATION = 'https://accounts.example.com/static/im/cloudbar/'
    CLOUDBAR_ACTIVE_SERVICE = '2'
    CLOUDBAR_SERVICES_URL = 'https://accounts.example.com/im/get_services'
    CLOUDBAR_MENU_URL = 'https://accounts.example.com/im/get_menu'
    BACKEND_DB_CONNECTION = 'postgresql://synnefo:example_passw0rd@db.example.com:5432/snf_pithos'
    BACKEND_BLOCK_PATH = '/srv/pithos/data/'

    AMQP_HOSTS = ["amqp://synnefo:example_rabbitmq_passw0rd@mq.example.com:5672"]

    CACHE_BACKEND = 'memcached://127.0.0.1:11211/'
    VMAPI_BASE_URL = 'https://cyclades.example.com/'


Restart services and initialize database:

.. code-block:: console

   # /etc/init.d/gunicorn restart
   # /etc/init.d/apache2 restart
   # snf-manage syncdb
   # snf-manage migrate
   # snf-manage loaddata flavors

Enable dispatcher:

.. code-block:: console

   # sed -i 's/false/true/' /etc/default/snf-dispatcher
   # /etc/init.d/snf-dispatcher start

In order end-user to have access to the VM's console:

.. code-block:: console

   # apt-get install snf-vncauthproxy

Edit `/etc/default/vncauthproxy`:

.. code-block:: console

   CHUID="www-data:nogroup"


At this point you should setup a :ref:`backend <i-backends>`. Please refer to the
coresponding section.  Here we assume that at least one backend is up and running,
so we can add it in Cyclades with:

.. code-block:: console

   # snf-manage backend-add --clustername=ganeti.example.com --user=synnefo --pass=example_rapi_passw0rd

Further assumptions:

- Preprovisioned Bridges: ``br0``, ``prv0``, ``prv1..prv20``
- Available "public" Subnet: ``10.0.1.0/24``
- Available "public" Gateway: ``10.0.1.1``
- Connectivity link for public network: ``br0``


Here admin has to define two different resource pools in Synnefo:

 - MAC prefix Pool
 - Bridge Pool

.. code-block:: console

   # snf-manage pool-create --type=mac-prefix --base=aa:00:0 --size=65536
   # snf-manage pool-create --type=bridge --base=prv --size=20

Add the synnefo setting in :file:`/etc/synnefo/cyclades.conf`:

.. code-block:: console

   PRIVATE_MAC_FILTERED_BRIDGE = 'prv0'

Add public network where the VM's will eventually connect to in order to
access Internet:

.. code-block:: console

   # snf-manage network-create --subnet=10.0.1.0/24 --gateway=10.0.1.1 --public --dhcp --flavor=CUSTOM --mode=bridged --link=br0 --name=Internet --backend-id=1
