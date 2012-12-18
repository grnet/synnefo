.. _snf-deploy:

snf-deploy tool
^^^^^^^^^^^^^^^


This tool allows you to deploy all Synnefo components from scratch
or to an existing cluster.

This is useful mostly for testing/demo installation and is not suggested for
production environments. At the end you will have an up-and-running Synnefo but
the end-to-end functionallity will depend from your underlying infrastracture
(e.g. is nested virtualization enabled in your PC, is the router properly
configured, do node have fully qualified domain names, etc.). Nevertheless you
will be able to experience the API/UI and base funtionality the Synnefo IaaS
provides and you 'll get a proper configuration that will guide you through
setting a production environment that will scale up and use all available
features (e.g. rados, archipelagos, etc).

snf-deploy is a debian package that should be installed locally and allow you
install Synnefo on remote nodes (either already existing or not). To this
end this guide will break the whole procedure into three; the configuration,
the virtual cluster creation (optional) and finally the Synnefo installation.

Before getting any further we should mention the roles that snf-deploy refers
to. Note that more than one roles can co-exist in the same node (except for few)
but it is highy recommended to dedicate one node (VM or physical) to each role:

 - existing nodes: All available nodes in the cluster

 - accounts: Identity Management
 - pithos: Storage Service
 - cms: Content Management System
 - cyclades: Compute Service to manage Instances, Networks, etc.
 - mq: Asynchronous Message Queue System for inter-service communication
 - qh: Quota Holder to keep track of resources utilization

 - ns: Nameserver to resolve Synnefo FQDN
 - router: The node to do any routing and NAT needed
 - client: The node to setup a command line tool to manage a user account

All these define the synnefo components. In order to have instances up-and-running,
at least a backend must be associated with Cyclades. Backends are
Ganeti clusters each with multiple nodes. Please note that these nodes may be the
same as the ones used before. To this end we refer to:

 - ganeti nodes: All available nodes for a specific backend
 - master: The master node in each ganeti backend

Configuration
=============

The configuration files to edit are under /etc/snf-deploy:

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


Virtual Cluster Creation
========================

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


Setting up the Synnefo DNS
==========================

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



Synnefo Installation
====================

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
=======================

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


snf-deploy as DevTool
=====================

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
