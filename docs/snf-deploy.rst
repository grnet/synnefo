.. _snf-deploy:

snf-deploy tool
^^^^^^^^^^^^^^^

The `snf-deploy` tool allows you to automatically deploy Synnefo.
You can use `snf-deploy` to deploy Synnefo, in two ways:

1. Create a virtual cluster on your local machine and then deploy on that cluster.
2. Deploy on a pre-existent cluster of physical nodes running Debian Squeeze.

Currently, `snf-deploy` is mostly useful for testing/demo installations and is
not recommended for production environment Synnefo deployments. If you want to
deploy Synnefo in production, please read first the :ref:`Admin's quick
installation guide <quick-install-admin-guide>` and then the :ref:`Admin's
guide <admin-guide>`.

If you use `snf-deploy` you will setup an up-and-running Synnefo installation,
but the end-to-end functionality will depend on your underlying infrastracture
(e.g.  is nested virtualization enabled in your PC, is the router properly
configured, do nodes have fully qualified domain names, etc.). In any way, it
will enable you to get a grasp of the Web UI/API and base funtionality of
Synnefo and also provide a proper configuration that you can afterwards consult
while reading the Admin guides to set up a production environment that will
scale up and use all available features (e.g. RADOS, Archipelago, etc).

`snf-deploy` is a debian package that should be installed locally and allows
you to install Synnefo on remote nodes (if you go for (2)), or spawn a cluster
of VMs on your local machine using KVM and then install Synnefo on this cluster
(if you go for (1)). To this end, here we will break down our description into
three sections:

a. :ref:`snf-deploy configuration <conf>`
b. :ref:`Creating a virtual cluster <vcluster>` (needed for (1))
c. :ref:`Synnefo deployment <inst>` (either on virtual nodes created on section b,
   or on remote physical nodes)

If you go for (1) you will need to walk through all the sections. If you go for
(2), you should skip section `(b) <vcluster>`, since you only need sections
`(a) <conf>` and `(c) <inst>`.

Before getting any further we should mention the roles that `snf-deploy` refers
to. The Synnefo roles are described in detail :ref:`here
<physical-node-roles>`. Note that multiple roles can co-exist in the same node
(virtual or physical).

Currently, `snf-deploy` recognizes the following combined roles:

* **accounts** = **WEBSERVER** + **ASTAKOS**
* **pithos** = **WEBSERVER** + **PITHOS**
* **cyclades** = **WEBSERVER** + **CYCLADES**
* **db** = **ASTAKOS_DB** + **PITHOS_DB** + **CYCLADES_DB**

the following independent roles:

* **qh** = **QHOLDER**
* **cms** = **CMS**
* **mq** = **MQ**
* **ns** = **NS**
* **client** = **CLIENT**
* **router**: The node to do any routing and NAT needed

The above define the roles relative to the Synnefo components. However, in
order to have instances up-and-running, at least one backend must be associated
with Cyclades. Backends are Ganeti clusters, each with multiple **GANETI_NODE**
s. Please note that these nodes may be the same as the ones used for the
previous roles. To this end, `snf-deploy` also recognizes:

* **cluster_nodes** = **G_BACKEND** = All available nodes of a specific backend
* **master_node** = **GANETI_MASTER**

Finally, it recognizes the group role:

* **existing_nodes** = **SYNNEFO** + (N x **G_BACKEND**)

In the future, `snf-deploy` will recognize all the independent roles of a scale
out deployment as stated in the :ref:`scale up section <scale-up>`. When that's
done, it won't need to introduce its own roles (stated here with lowercase) but
rather use the scale out ones (stated with uppercase on the admin guide).


.. _conf:

Configuration (a)
=================

All configuration of `snf-deploy` happens by editting the following files under
``/etc/snf-deploy``:

``nodes.conf``
--------------

This file reflects the hardware infrastucture on which Synnefo is going to be
deployed and is the first to be set before running `snf-deploy`.

Defines the nodes' hostnames and their IPs. Currently `snf-deploy` expects all
nodes to reside in the same network subnet and domain, and share the same
gateway and nameserver. Since Synnefo requires FQDNs to operate, a nameserver
is going to be automatically setup in the cluster by `snf-deploy`. Thus, the
nameserver's IP should appear among the defined node IPs. From now on, we will
refer to the nodes with their hostnames. This implies their FQDN and their IP.

Also, defines the nodes' authentication credentials (username, password).
Furthermore, whether nodes have an extra disk (used for LVM/DRBD storage in
Ganeti backends) or not. The VM container nodes should have three separate
network interfaces (either physical or vlans) each in the same collision
domain; one for the node's public network, one for VMs' public network and one
for VMs' private networks. In order to support the most common case, a router
is setup on the VMs' public interface and does NAT (hoping the node has itself
internet access).

The nodes defined in this file can reflect a number of physical nodes, on which
you will deploy Synnefo (option (2)), or a number of virtual nodes which will
get created by `snf-deploy` using KVM (option (1)), before deploying Synnefo.
As we will see in the next sections, one should first set up this file and then
tell `snf-deploy` whether the nodes on this file should be created, or treated
as pre-existing.

An example ``nodes.conf`` file looks like this:

FIXME: example file here

``synnefo.conf``
----------------

This file reflects the way Synnefo will be deployed on the nodes defined at
``nodes.conf``.

The important section here is the roles. In this file we assing each of the
roles described in the :ref:`introduction <snf-deploy>` to a specific node. The
node is one of the nodes defined at ``nodes.conf``. Note that we refer to nodes
with their short hostnames.

Here we also define all credentials related to users needed by the various
Synnefo services (database, RAPI, RabbitMQ) and the credentials of a test
end-user (`snf-deploy` simulates a user signing up).

Furthermore, define the Pithos shared directory which will hold all the Pithos
related data (maps and blocks).

Finally, define the name of the bridge interfaces controlled by Synnefo, and a
testing Image to register after everything is up and running.

An example ``setup.conf`` file (based on the previous ``nodes.conf`` example)
looks like this:

FIXME: example file here

``ganeti.conf``
---------------

This file reflects the way Ganeti clusters will be deployed on the nodes
defined at ``nodes.conf``.

Here we include all info with regard to Ganeti backends. That is: the master
node, its floating IP, the volume group name (in case of LVM support) and the
VMs' public network associated to it. Please note that currently Synnefo
expects different public networks per backend but still can support multiple
public networks per backend.

FIXME: example file here

``deploy.conf``
---------------

This file customizes `snf-deploy` itself.

It defines some needed directories and also includes options that have to do
with the source of the packages to be deployed. Specifically, whether to deploy
using local packages found under a local directory or deploy using an apt
repository. If deploying from local packages, there is also an option to first
download the packages from a custom URL and save them under the local directory
for later use.

FIXME: example file here

``vcluster.conf``
-----------------

This file defines options that are relevant to the virtual cluster creationi, if
one chooses to create one.

There is an option to define the URL of the Image that will be used as the host
OS for the VMs of the virtual cluster. Also, options for defining an LVM space
or a plain file to be used as a second disk. Finally, networking options to
define where to bridge the virtual cluster.


.. _vcluster:

Virtual Cluster Creation (b)
============================

As stated in the introduction, `snf-deploy` gives you the ability to create a
local virtual cluster using KVM and then deploy Synnefo on top of this cluster.
The number of cluster nodes is arbitrary and is defined in ``nodes.conf``.

This section describes the creation of the virtual cluster, on which Synnefo
will be deployed in the :ref:`next section <inst>`. If you want to deploy
Synnefo on existing physical nodes, you should skip this section.

The first thing you need to deploy a virtual cluster, is a Debian Base image,
which will be used to spawn the VMs. We already provide an 8GB Debian Squeeze
Base image with preinstalled keys and network-manager hostname hooks. This
resides on our production Pithos service. Please see the corresponding
``squeeze_image_url`` variable in ``vcluster.conf``. The image can be fetched
by running:

.. code-block:: console

   snf-deploy vcluster prep-image

This will download the image from the URL defined at ``squeeez_image_url``
(Pithos by default) and save it locally under ``/var/lib/snf-deploy/images``.

TODO: mention related options: --img-dir, --extra-disk, --lvg, --os

Once you have the image, then you need to setup the local machine's networking
appropriately. You can do this by running:

.. code-block:: console

   snf-deploy vcluster prep-net

This will add a bridge (defined with the ``bridge`` option inside
``vcluster.conf``), iptables to allow traffic from/to the cluster, and enable
forwarding and NAT for the selected network subnet (defined inside
``nodes.conf`` in the ``subnet`` option).

To complete the preparation, you need a DHCP server that will provide the
selected hostnames and IPs to the cluster (defined under ``[ips]`` in
``nodes.conf``). To do so, run:

.. code-block:: console

   snf-deploy vcluster prep-dhcp

This will launch a dnsmasq instance, acting only as DHCP server and listening
only on the cluster's bridge. Every time you make changes inside ``nodes.conf``
you should re-create the dnsmasq related files (under ``/etc/snf-deploy``) by
passing --save-config option.

After running all the above preparation tasks we can finally create the cluster
defined in ``nodes.conf`` by running:

.. code-block:: console

   snf-deploy vcluster create

This will launch all the needed KVM virtual machines, snapshotting the image we
fetched before. Their taps will be connected with the already created bridge
and their primary interface will get the given address.

Now that we have the nodes ready, we can move on and deploy Synnefo on them.


.. _inst:

Synnefo Installation (c)
========================

At this point you should have an up-and-running cluster, either virtual
(created in the `previous section <vcluster>` on your local machine) or
physical on remote nodes. The cluster should also have valid hostnames and IPs.
And all its nodes should be defined in ``nodes.conf``.

You should also have set up ``synnefo.conf`` to reflect which Synnefo component
will reside in which node.

Setting up the Synnefo DNS
--------------------------

Synnefo expects FQDNs and therefore a nameserver (BIND) should be setup in a
node inside the cluster. All nodes along with your local machine should use
this nameserver and search in the corresponding network domain. To this end,
add to your local ``resolv.conf`` (please change the default values with the
ones of your custom configuration):

.. code-block:: console

   search <your_domain> synnefo.deploy.local
   nameserver 192.168.0.1

To actually setup the nameserver in the node specified as ``ns`` in
``synnefo.conf`` run:

.. code-block:: console

   snf-deploy dns

At this point you should have a cluster with FQDNs and reverse DNS lookups
ready for the Synnefo deployment. To sum up, we mention all the node
requirements for a successful Synnefo installation, before proceeding.

Node Requirements
-----------------

 - OS: Debian Squeeze
 - authentication: `root` with same password for all nodes
 - primary network interface: `eth0`
 - primary IP in the same IPv4 subnet and network domain
 - spare network interfaces: `eth1`, `eth2` (or vlans on `eth0`)
 - password-less intra-node communication: same `id_rsa/dsa` keys and `authorized_keys`

In case you have created a virtual cluster as described in the :ref:`section
(b) <vcluster>`, the above requirements are already taken care of. In case of a
physical cluster, you need to set them up manually by yourself, before
proceeding with the Synnefo installation.

To check the network configuration (FQDNs, connectivity):

.. code-block:: console

   snf-deploy check-net

WARNING: In case ping fails check ``/etc/nsswitch.conf`` hosts entry and put dns
after files!!!

If everything is setup correctly and all prerequisites are met, we can start
the Synnefo deployment.

Synnefo deployment
------------------

First, we need to setup the NFS:

.. code-block:: console

   snf-deploy nfs

To install the Synnefo stack on the existing cluster run:

.. code-block:: console

   snf-deploy synnefo -vvv

This might take a while.

If this finishes without errors, check for successful installation by visiting
from your local machine (make sure you have already setup your local
``resolv.conf`` to point at the cluster's DNS):

| https://accounts.synnefo.deploy.local/im/

and login with:

| username: dimara@grnet.gr password: lala

or the ``user_name`` and ``user_passwd`` defined in your ``synnefo.conf``.
Take a small tour checking out Pithos and the rest of the Web UI. You can
upload a sample file on Pithos to see that Pithos is working. Do not try to
create a VM yet, since we have not yet added a Ganeti backend.

If everything seems to work, we go ahead to the last step which is adding a
Ganeti backend.

Adding a Ganeti Backend
-----------------------

Assuming that everything works as expected, you must have Astakos, Pithos, CMS,
DB and RabbitMQ up and running. Cyclades should work too, but partially. That's
because no backend is registered yet. Let's setup one. Currently, Synnefo
supports only Ganeti clusters as valid backends. They have to be created
independently with `snf-deploy` and once they are up and running, we register
them to Cyclades. From version 0.12, Synnefo supports multiple Ganeti backends.
`snf-deploy` defines them in ``ganeti.conf``.

After setting up ``ganeti.conf``, run:

.. code-block:: console

   snf-deploy backend create --backend-name ganeti1 -vvv

where ``ganeti1`` should have previously been defined as a section in
``ganeti.conf``. This will create the ``ganeti1`` backend on the corresponding
nodes (``cluster_nodes``, ``master_node``) defined in the ``ganeti1`` section
of the ``ganeti.conf`` file. If you are an experienced user and want to deploy
more than one Ganeti backend you should create multiple sections in
``ganeti.conf`` and re-run the above command with the corresponding backend
names.

After creating and adding the Ganeti backend, we need to setup the backend
networking. To do so, we run:

.. code-block:: console

   snf-deploy backend setup-network --backend-name ganeti1

And finally, we need to setup the backend storage:

.. code-block:: console

   snf-deploy backend setup-storage --backend-name ganeti1

This command will first check the ``extra_disk`` in ``nodes.conf`` and try to
find it on the nodes of the cluster. If the nodes indeed have that disk,
`snf-deploy` will create a PV and the corresponding VG and will enable LVM and
DRBD storage in the Ganeti cluster.

If the option is blank or `snf-deploy` can't find the disk on the nodes, LVM
and DRBD will be disabled and only Ganeti's ``file`` disk template will be
enabled.

To test everything went as expected, visit from your local machine:

.. code-block:: console

    https://cyclades.synnefo.deploy.local/ui/

and try to create a VM. Also create a Private Network and try to connect it. If
everything works, you have setup Synnefo successfully. Enjoy!


snf-deploy as a DevTool
=======================

For developers, a single node setup is highly recommended and `snf-deploy` is a
very helpful tool. `snf-deploy` also supports updating packages that are
locally generated. For this to work please add all \*.deb files in packages
directory (see ``deploy.conf``) and set the ``use_local_packages`` option to
``True``. Then run:

.. code-block:: console

   snf-deploy synnefo --update --use-local-packages
   snf-deploy backend create --backend-name ganeti2 --update --use-local-packages

For advanced users, `snf-deploy` gives the ability to run one or more times
independently some of the supported actions. To find out which are those, run:

.. code-block:: console

   snf-deploy run --help
