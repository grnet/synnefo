.. _networks:

Network Service (part of Cyclades)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Network setup overview
======================

Currently the Network Service is part of Cyclades and comes along with the
Cyclades software components.

Networking is deployment-specific and must be customized based on the specific
needs of the system administrator. However, to do so, the administrator needs
to understand how each level handles Virtual Networks, to be able to setup the
backend appropriately.

Network @ Cyclades level
------------------------

Cyclades understands two types of Virtual Networks:

a) One common Public Network (Internet)
b) One or more distinct Private Networks (L2)

a) When a new VM is created, it instantly gets connected to the Public Network
   (Internet). This means it gets a public IPv4 and IPv6 and has access to the
   public Internet.

b) Then each user, is able to create one or more Private Networks manually and
   add VMs inside those Private Networks. Private Networks provide Layer 2
   connectivity. All VMs inside a Private Network are completely isolated.

From the VM perspective, every Network corresponds to a distinct NIC. So, the
above are translated as follows:

a) Every newly created VM, needs at least one NIC. This NIC, connects the VM
   to the Public Network and thus should get a public IPv4 and IPv6.

b) For every Private Network, the VM gets a new NIC, which is added during the
   connection of the VM to the Private Network (without an IP). This NIC should
   have L2 connectivity with all other NICs connected to this Private Network.

To achieve the above, first of all, we need Network and IP Pool management support
at Ganeti level, for Cyclades to be able to issue the corresponding commands.

Network @ Ganeti level
----------------------

Currently, Ganeti does not support IP Pool management. However, we've been
actively in touch with the official Ganeti team, who are reviewing a relatively
big patchset that implements this functionality (you can find it at the
ganeti-devel mailing list). We hope that the functionality will be merged to
the Ganeti master branch soon and appear on Ganeti 2.7.

Furthermore, currently the `~okeanos service <http://okeanos.grnet.gr>`_ uses
the same patchset with slight differencies on top of Ganeti 2.4.5. Cyclades
0.9 are compatible with this old patchset and we do not guarantee that will
work with the updated patchset sent to ganeti-devel.

We do *NOT* recommend you to apply the patchset yourself on the current Ganeti
master, unless you are an experienced Cyclades and Ganeti integrator and you
really know what you are doing.

Instead, be a little patient and we hope that everything will work out of the
box, once the patchset makes it into the Ganeti master. When so, Cyclades will
get updated to become compatible with that Ganeti version.

Network @ Physical host level
-----------------------------

We talked about the two types of Network from the Cyclades perspective, from the
VMs perspective and from Ganeti's perspective. Finally, we need to talk about
the Networks from the physical (VM container) host's perspective.

If your version of Ganeti supports IP pool management, then you need to setup
your physical hosts for the two types of Networks. For the second type
(Private Networks), our reference installation uses a number of pre-provisioned
bridges (one for each Network), which are connected to the corresponding number
of pre-provisioned vlans on each physical host (node1 and node2). For the first
type (Public Network), our reference installation uses routing over one
preprovisioned vlan on each host (node1 and node2). It also uses the `NFDHCPD`
package for dynamically serving specific public IPs managed by Ganeti.
