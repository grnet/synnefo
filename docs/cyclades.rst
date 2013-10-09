.. _cyclades:

Compute/Network/Image Service (Cyclades)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Cyclades is the Synnefo component that implements the Compute, Network, Image
and Volume services. It exposes the associated OpenStack REST APIs: OpenStack
Compute, Network, Glance and soon also Cinder. Cyclades is the part which
manages multiple Ganeti clusters at the backend. Cyclades issues commands to a
Ganeti cluster using Ganeti's Remote API (RAPI). The administrator can expand
the infrastructure dynamically by adding new Ganeti clusters to reach
datacenter scale. Cyclades knows nothing about low-level VM management
operations, e.g., handling of VM creations, migrations among physical nodes,
and handling of node downtimes; the design and implementation of the end-user
API is orthogonal to VM handling at the backend.

There are two distinct, asynchronous paths in the interaction between Synnefo
and Ganeti. The `effect` path is activated in response to a user request;
Cyclades issues VM control commands to Ganeti over RAPI. The `update` path is
triggered whenever the state of a VM changes, due to Synnefo- or
administrator-initiated actions happening at the Ganeti level. In the update
path, we exploit Ganeti’s hook mechanism to produce notifications to the rest
of the Synnefo infrastructure over a message queue.

Users have full control over their VMs: they can create new ones, start them,
shutdown, reboot, and destroy them. For the configuration of their VMs they can
select number of CPUs, size of RAM and system disk, and operating system from
pre-defined Images including popular Linux distros (Debian, Ubuntu, CentOS,
Fedora, Gentoo, Archlinux, OpenSuse), MS-Windows Server 2008 R2 and 2012 as
well as FreeBSD.

The REST API for VM management, being OpenStack compatible, can interoperate
with 3rd party tools and client libraries.

The *Cyclades* UI is written in Javascript/jQuery and runs entirely on the
client side for maximum reponsiveness. It is just another API client; all UI
operations happen with asynchronous calls over the API.

The networking functionality includes dual IPv4/IPv6 connectivity for each VM,
easy, platform-provided firewalling either through an array of pre-configured
firewall profiles, or through a roll-your-own firewall inside the VM. Users may
create multiple private, virtual L2 networks, so that they construct arbitrary
network topologie, e.g., to deploy VMs in multi-tier configurations. The
networking functionality is exported all the way from the backend to the API and
the UI.

Please also see the :ref:`Admin Guide <admin-guide>` for more information and
the :ref:`Installation Guide <quick-install-admin-guide>` for installation
instructions.
