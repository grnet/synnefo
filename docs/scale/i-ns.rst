.. _i-ns:

Synnefo
-------


:ref:`synnefo <i-synnefo>` ||
ns ||
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

Name Server Setup
+++++++++++++++++

The following applies to ``ns`` node. You will  create  an DNS to resolve all
FQDNs used by both ``synnefo`` and ``backend`` nodes. All we need here is to have
a physical node - ip - role mapping.

Assumptions:
~~~~~~~~~~~~

 - domain to use:  ``example.com``
 - nodes' IPv4 subnet: ``4.3.2.0/24``

For the sake of simplicity we assume we have 6 nodes assinged the following roles:

========  =========  ===========================    ====================
hostname  IP         roles                          FQDN
========  =========  ===========================    ====================
node1     4.3.2.1    ns,router,client,astakos,qh    accounts.example.com
node2     4.3.2.2    cyclades                       cyclades.example.com
node3     4.3.2.3    pithos                         pithos.example.com
node4     4.3.2.4    cms                            cms.example.com
node5     4.3.2.5    db                             db.example.com
node6     4.3.2.6    mq                             mq.example.com
node1     4.3.2.100  master                         ganeti.example.com
========  =========  ===========================    ====================


First install the corresponding package:

.. code-block:: console

   # apt-get install bind9

In `/etc/bind/zones/example.com` add:

.. code-block:: console

    $TTL 14400
    $origin example.com.
    @               IN      SOA     ns.example.com. admin.example.com. (
    2012111903; the Serial Number
    172800; the Refresh Rate
    7200;  the Retry Time
    604800; the Expiration Time
    3600; the Minimum Time
    )

    @               IN        NS      ns.example.com.
    @               IN        A       4.3.2.1
    ns              IN        A       4.3.2.1

    localhost       IN        A       127.0.0.1
    example.com.    IN        MX      10 example.com.

    mail            IN        CNAME   example.com.
    www             IN        CNAME   example.com.
    accounts        IN        CNAME   node1.example.com.
    cyclades        IN        CNAME   node2.example.com.
    pithos          IN        CNAME   node3.example.com.
    cms             IN        CNAME   node4.example.com.
    db              IN        CNAME   node5.example.com.
    mq              IN        CNAME   node6.example.com.
    qh              IN        CNAME   node1.example.com.

    node1           IN        A       4.3.2.1
    node2           IN        A       4.3.2.2
    node3           IN        A       4.3.2.3
    node4           IN        A       4.3.2.4
    node5           IN        A       4.3.2.5
    node6           IN        A       4.3.2.6

    ganeti          IN        A       4.3.2.100


In `/etc/bind/rev/0-24.2.3.4.in-addr.arpa.zone` add:

.. code-block:: console

    $TTL 86400
    $ORIGIN 2.3.4.in-addr.arpa.
    @               IN      SOA     ns.example.com. admin.skata.com. (
    2012070900; the Serial Number
    172800; the Refresh Rate
    7200;  the Retry Time
    604800; the Expiration Time
    3600 ; the Minimum Time
    )
    @               IN        NS      ns.example.com.

    1               IN        PTR     node1.example.com.
    2               IN        PTR     node2.example.com.
    3               IN        PTR     node3.example.com.
    4               IN        PTR     node4.example.com.
    5               IN        PTR     node5.example.com.
    6               IN        PTR     node6.example.com.


In `/etc/bind/named.conf.local` add:

.. code-block:: console

    zone "example.com" in {
            type master;
            file "/etc/bind/zones/example.com";
    };

    zone "0-24.2.3.4.in-addr.arpa" in {
            type master;
            file "/etc/bind/rev/0-24.2.3.4.in-addr.arpa.zone";
    };

And then restart the service:

.. code-block:: console

    # /etc/init.d/bind9 restart


In all ``synnefo`` and ``backend`` nodes add in `/etc/resolv.conf`:

.. code-block:: console

    domain example.com
    search example.com
    nameserver 4.3.2.1


Test your Setup:
++++++++++++++++

Try to ping all FQDNs.
