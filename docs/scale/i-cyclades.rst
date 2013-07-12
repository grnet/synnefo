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
    # apt-get install kamaki
    # apt-get install snf-pithos-backend
    # apt-get install snf-cyclades-app

In `/etc/synnefo/cyclades.conf` add:

.. code-block:: console

    MAX_CIDR_BLOCK = 21

    CPU_BAR_GRAPH_URL = 'https://cyclades.example.com/stats/%s/cpu-bar.png'
    CPU_TIMESERIES_GRAPH_URL = 'https://cyclades.example.com/stats/%s/cpu-ts.png'
    NET_BAR_GRAPH_URL = 'https://cyclades.example.com/stats/%s/net-bar.png'
    NET_TIMESERIES_GRAPH_URL = 'https://cyclades.example.com/stats/%s/net-ts.png'

    ASTAKOS_BASE_URL = 'https://accounts.example.synnefo.org/'

    SECRET_ENCRYPTION_KEY= "oEs0pt7Di1mkxA0P6FiK"

    GANETI_CREATEINSTANCE_KWARGS = {
        'os': 'snf-image+default',
        'hvparams': {'serial_console': False},
        'wait_for_sync': False}

    GANETI_USE_HOTPLUG = True
    CLOUDBAR_LOCATION = 'https://accounts.example.com/static/im/cloudbar/'
    CLOUDBAR_SERVICES_URL = 'https://accounts.example.com/ui/get_services'
    CLOUDBAR_MENU_URL = 'https://accounts.example.com/ui/get_menu'
    BACKEND_DB_CONNECTION = 'postgresql://synnefo:example_passw0rd@db.example.com:5432/snf_pithos'
    BACKEND_BLOCK_PATH = '/srv/pithos/data/'

    AMQP_HOSTS = ["amqp://synnefo:example_rabbitmq_passw0rd@mq.example.com:5672"]

    TIMEOUT = 60 * 1000
    UI_UPDATE_INTERVAL = 2000
    FEEDBACK_CONTACTS = (
        ('feedback@example.com', 'feedback@example.com'),
    )
    UI_FLAVORS_DISK_TEMPLATES_INFO = {
        'rbd': {'name': 'Rbd',
               'description': 'Volumes residing inside a RADOS cluster'},

        'plain': {'name': 'Local',
                 'description': 'Fast, not high available local storage (LVM)'},

        'drbd': {'name': 'Standard',
                 'description': 'High available persistent storage (DRBD)'},

        'ext_vlmc': {'name': 'Tmp',
                    'description': 'Volatile storage'},
    }
    UI_SUPPORT_SSH_OS_LIST = ['debian', 'fedora', 'okeanos', 'ubuntu', 'kubuntu',
                              'centos', 'archlinux', 'gentoo']
    UI_SYSTEM_IMAGES_OWNERS = {
        'images@okeanos.io': 'system',
    }

    CACHE_BACKEND = 'memcached://127.0.0.1:11211/'

    CYCLADES_SERVICE_TOKEN = "XXXXXXXXXX"

    UI_SYSTEM_IMAGES_OWNERS = {
        'admin@synnefo.gr': 'system',
        'images@synnefo.gr': 'system'
    }

XXXXXXXX is the token for cyclades registered service and can be found
in astakos node running:

.. code-block:: console

   snf-manage service-list


Restart services and initialize database:

.. code-block:: console

   # /etc/init.d/gunicorn restart
   # /etc/init.d/apache2 restart
   # snf-manage syncdb
   # snf-manage migrate --delete-ghost-migrations
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

After 0.13 every backend added stays in drained mode (no VMs can be added).
Therefore get your backend ID (propably 1) and run:

.. code-block:: console

   # snf-manage backend-list
   # snf-manage backend-modify --drained=False 1

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

   DEFAULT_MAC_FILTERED_BRIDGE = 'prv0'

Add public network where the VM's will eventually connect to in order to
access Internet:

.. code-block:: console

   # snf-manage network-create --subnet=10.0.1.0/24 --gateway=10.0.1.1 --public --dhcp --flavor=CUSTOM --mode=bridged --link=br0 --name=Internet --backend-id=1


Test your Setup:
++++++++++++++++

In cyclades node run:

.. code-block:: console

    snf-manage backend-list
    snf-manage network-list
    snf-manage server-list

Visit https://cyclades.example.com/ui/ and create a VM or network.

