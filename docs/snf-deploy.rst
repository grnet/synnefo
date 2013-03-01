.. _snf-deploy:

snf-deploy tool
^^^^^^^^^^^^^^^

The `snf-deploy` tool allows you to automatically deploy Synnefo.
You can use `snf-deploy` to deploy Synnefo, in two ways:

1. Create a virtual cluster on your local machine and then deploy on that cluster.
2. Deploy on a pre-existent cluster of physical nodes.

Currently, `snf-deploy` is mostly useful for testing/demo installations and is not
recommended for production environment Synnefo deployments. If you want to deploy
Synnefo in production, please read first the :ref:`Admin's quick installation
guide <quick-install-admin-guide>` and then the :ref:`Admin's guide
<admin-guide>`.

If you use `snf-deploy` you will setup an up-and-running Synnefo installation, but
the end-to-end functionality will depend on your underlying infrastracture (e.g.
is nested virtualization enabled in your PC, is the router properly configured, do
nodes have fully qualified domain names, etc.). In any way, it will enable you to
get a grasp of the Web UI/API and base funtionality of Synnefo and also provide a
proper configuration that you can afterwards consult while reading the Admin
guides to set up a production environment that will scale up and use all available
features (e.g. RADOS, Archipelago, etc).

`snf-deploy` is a debian package that should be installed locally and allows you
to install Synnefo on remote nodes (if you go for (2)), or spawn a cluster of VMs
on your local machine using KVM and then install Synnefo on this cluster (if you
go for (1)). To this end, here we will break down our description into three
sections:

a. `snf-deploy` configuration
b. Creating a virtual cluster (needed for (1))
c. Synnefo deployment (either on virtual nodes created on section b, or on
   remote physical nodes)

If you go for (1) you will need to walk through all the sections. If you go for
(2), you should skip section (b), since you only need sections (a) and (c).

Before getting any further we should mention the roles that `snf-deploy` refers
to. The roles are described :ref:`here <physical-node-roles>`. Note that multiple
roles can co-exist in the same node (virtual or physical).

Currently, `snf-deploy` recognizes the following combined roles:

* **astakos** = **WEBSERVER** + **ASTAKOS**
* **pithos** = **WEBSERVER** + **PITHOS**
* **cyclades** = **WEBSERVER** + **CYCLADES**
* **db** = **ASTAKOS_DB** + **PITHOS_DB** + **CYCLADES_DB**

the following independent roles:

* **cms** = **CMS**
* **mq** = **MQ**
* **ns** = **NS**
* **client** = **CLIENT**
* **router**: The node to do any routing and NAT needed

The above define the roles relative to the Synnefo components. However, in
order to have instances up-and-running, at least one backend must be associated
with Cyclades. Backends are Ganeti clusters each with multiple
**GANETI_NODE**s. Please note that these nodes may be the same as the ones used
for the previous roles. To this end, `snf-deploy` also recognizes:

* **ganeti_backend** = **G_BACKEND** = All available nodes of a specific backend
* **ganeti_master** = **GANETI_MASTER**

Finally, it recognizes the group role:

* **existing_nodes** = **SYNNEFO** + (N x **G_BACKEND**)

In the future, `snf-deploy` will recognize all the independent roles of a scale
out deployment as stated in the :ref:`scale up section <scale-up>`. When that's
done it won't need to introduce its own roles (stated here with lowercase) but
rather use the scale out ones (stated with uppercase on the admin guide).


Configuration (a)
=================

All configuration of `snf-deploy` happens by editting the following files under
``/etc/snf-deploy``:

nodes.conf
----------
Defines all existing hostnames and their ips. Currently snf-deploy expects all
nodes to reside in the same network subnet and domain, will share the same
gateway and nameserver. Synnefo needs fqdn for its services. Therefore a
nameserver is setup in the cluster by snf-deploy so the nameserver IP should be
among the existing ones. From now on we refer to the nodes based on their
hostnames. This implies their fqdn and their IP.

Additionally here we define the available ganeti clusters as far as the
nodes is concerned. Additionaly info is provided in backends.conf

setup.conf
----------
The important section here is the roles. Based on the aforementioned, we
assing each role to a certain role. Note that we refer to nodes with their
short hostnames and they should be previously defined in nodes.conf

Here we define also the authentication details for the nodes (user, password),
various credentials for the synnefo installation, whether nodes have an extra
disk (used for lvm/drbd storage in Ganeti backends) or not. The VMCs should
have three separate network interfaces (either physical or not -vlans) each
in the same collition domain; one for the node's public network, one
for VM's public network and one for VM's private network. In order to
support the most common case, a router is setup on the VMs' public interface
and does NAT (hoping the node has itself internet access).

backends.conf
-------------
Here we include all info regarding Ganeti backends. That is the master node,
its floating IP, the volume group name (in case of lvm support) and the VM's
public network associated to it. Please note that currently Synnefo expects
different public networks per backend but still can support multiple public
networks per backend.


deploy.conf
-----------
Here we define all necessary info for customizing snf-deploy; whether to use
local packages or not (this is used primarily by developers), which bridge
to use (if you create a virtual cluster from scratch), and where are the
necessary local directories (packages, templates, images, etc..)


Virtual Cluster Creation (b)
============================

Supposing you want to install Synnefo from scratch the best way is to launch
a couple of VM's locally. To this end you need a debian base image. An 8GB one
with preinstalled keys and network-manager hostname hooks exists in pithos.okeanos.grnet.gr
and can be fetched with:

.. code-block:: console

   snf-deploy image

This will save locally the image under /var/lib/snf-deploy/images. TODO: mention
related options: --img-dir, --extra-disk, --lvg, --os

To have a functional networking setup for the instances please run:

.. code-block:: console

   snf-deploy prepare

This will add a bridge, iptables to allow traffic from/to it, enable forwarding and
NAT for the given network subnet.

To provide the configured hostnames and IPs to the cluster please run:

.. code-block:: console

   snf-deploy dhcp

This will launch a dnsmasq instance acting only as dhcp server and listening only on
the cluster's bridge. In case you have changes the nodes.conf you should re-create
the dnsmasq related files (in /etc/snf-deploy) only by extra passing --save-config.


At this point you can create the virtual cluster defined in nodes.conf with:

.. code-block:: console

   snf-deploy cluster

This will launch KVM Virtual Machines snapshoting the base image you fetched
before. Their taps will be connected with the already created bridge and their
primary interface should get the given address.


Synnefo Installation (c)
========================

Setting up the Synnefo DNS
--------------------------

At this point you should have an up-and-running cluster (either virtual or not)
with valid hostnames and IPs. Synnefo expects fqdn and therefore a nameserver
(bind) should be setup in a node inside the cluster. All nodes along with your
PC should uses this nameserver and search in the corresponding network domain.
To this end add to your local resolv.conf (please change the default values with
the ones of your custom configuration):

| search <your_domain> synnefo.deploy.local
| nameserver 192.168.0.1

To setup the nameserver in the node specified in setup.conf please run:

.. code-block:: console

   snf-deploy dns

At this point you should have a cluster with fqdns and reverse DNS lookups ready
for synnefo deployment. To sum up we mention all the node requirements for a
successful synnefo installation:

Node Requirements
-----------------

 - OS: Debian Squeeze
 - authentication: `root` with known password
 - primary network interface: `eth0`
 - primary IP in the same IPv4 subnet and network domain
 - spare network interfaces: `eth1`, `eth2` (or vlans on `eth0`)
 - password-less intra-node communication: same `id_rsa/dsa` keys and `authorized_keys`

Those are met already in the case of virtual cluster.

To check the network configuration (fqdns, connectivity):

.. code-block:: console

   snf-deploy check

WARNING: In case ping fails check ``/etc/nsswitch.conf`` hosts entry and put dns after files!!!

To setup the NFS needed among the cluster:

.. code-block:: console

   snf-deploy nfs

To install the Synnefo stack on the existing cluster please run:

.. code-block:: console

   snf-deploy synnefo -vvv

and wait a few seconds.

To check for successful installation you can visit from your local PC:

| https://accounts.synnefo.deploy.local/im/

and login with:

| username: dimara@grnet.gr password: lala

or whatever you gave in setup.conf and get a small taste of your private cloud setup.

Adding a Ganeti Backend
-----------------------

Assuming that all have worked out fine as expected, you must have astakos,
pithos, cms, db and mq up and running. Cyclades work too but partially. No
backend is registered yet. Let's setup one. Currently synnefo supports only
Ganeti clusters for backends. They have to be created offline and once they
are up and running must be registered to Cyclades. After 0.12, synnefo supports
multiple backends. snf-deploy defines backend nodes in nodes.conf and backend
info in backends.conf.

To deploy a backend please use:

.. code-block:: console

   snf-deploy backend --backend-name ganeti1 -vvv

where ganeti1 or whatever refers to the corresponding entry in conf files.

To setup backend storage (lvm, drbd or file) and network (bridges, iptables,
router):

.. code-block:: console

   snf-deploy backend-storage --backend-name ganeti1
   snf-deploy backend-network --backend-name ganeti1

To test deployment state please visit:

.. code-block:: console

    https://cyclades.synnefo.deploy.local/ui/

and try to create a VM.


snf-deploy as a DevTool
=======================

For developers who want to contribute a single node setup is highly recommended.
snf-deploy tools also supports updating packages that are localy generated. This
to work please add all \*.deb files in packages directory (see deploy.conf) and
run:

.. code-block:: console

   snf-deploy synnefo --update --use-local-packages
   snf-deploy backend --backend-name ganeti2 --update --use-local-packages


For advanced users there is a possibility to individually run one or more of the
supported actions. To find out which are those run:

.. code-block:: console

    snf-deploy run --help
