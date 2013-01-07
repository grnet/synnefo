.. _i-backends:

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
backends

Backends
++++++++

:ref:`ganeti <i-ganeti>` ||
:ref:`image <i-image>` ||
:ref:`gtools <i-gtools>` ||
:ref:`network <i-network>`

The sections above, guide you though the actions needed to create a synnefo
backend. Once you have at least one backend up and running you can go back to
the :ref:`cyclades  <i-cyclades>` section, add the backend, create a public
network and have full synnefo functionality.

In the following sections we will refer to the following roles:

 * ``ganeti`` (all nodes of a Ganeti cluster/synnefo backend)
 * ``master`` (ganeti master node)
 * ``router``

Please note that all these roles can be "played" by the same node.

Prerequisites:
~~~~~~~~~~~~~~

``master``:

 - Available master IP that resolves to FQDN (ganeti.example.com)

``ganeti``:

 - primary interface: `eth0` with IP that resolves to FQDN (nodeX.example.com)
 - /etc/hosts: hostname should not resolv to 127.* address.
 - /etc/ssh/ssh_host_rsa_key*: must be identical among all nodes.
 - extra interfaces: `eth1`, `eth2` (vlans can be used too)
 - NFS mount point: `/srv/pithos`
 - lvm: Volume Group named `ganeti`

``router``:

 - primary interface: `eth0` with public routable IP
 - extra interfaces: `eth1`, `eth2` (vlans can be used too) connected with ganeti nodes
