.. _i-synnefo:

Synnefo
-------

synnefo ||
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


The above sections are the software components/roles that you should setup in
order to have full synnefo funtionality.  After successful installation, you
will have the following services running:

 * Identity Management (Astakos)
 * Object Storage Service (Pithos+)
 * Compute Service (Cyclades)
 * Image Service (part of Cyclades)
 * Network Service (part of Cyclades)

and a single unified Web UI to manage them all.

It is really useful nodes to have fully qualified domain names. The installation
needs additional CNAMEs, and therefor in the following section we will guide you
though how to setup a DNS node so that all IP's (internal/public) will resolve to
specific FQDN. `/etc/hosts` could be used for simplicity too.

In the following sections we will refer to nodes based on their roles. To this
end here we define the following roles:

 * ``synnefo`` (all available nodes for Synnefo components)
 * ``backend`` (all available VMCs - nodes to host VMs)
 * ``astakos``
 * ``cyclades``
 * ``pithos``
 * ``cms``
 * ``mq`` (message queue)
 * ``db`` (database)
 * ``ns`` (name server)
 * ``client`` (end-user)

Please note that all these roles can be "played" by the same node, but for the
sake of scalability is highly recommended to deploy Synnefo on more than 6 nodes,
each with different role(s). In setup synnefo and backend nodes are the same
ones.


Prerequisites:
++++++++++++++

``synnefo``:

 - OS: Debian Squeeze

``pithos``:

 - NFS server: export dir /srv/pithos

Assumptions:
++++++++++++

``synnefo``:

 - primary interface: `eth0`
 - primary IP: inside 4.3.2.0/24 IPv4 subnet
