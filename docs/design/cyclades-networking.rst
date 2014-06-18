===================
Cyclades Networking
===================

Networks
========

A Cyclades network is a virtual network that can be, depending on it's Network
Flavor, either an isolated Layer-2 broadcast domain or a Layer-3 network.
Networks can either be private or public. Private networks are reserved for the
user who created it, while public networks are created by the administrator and
are visible to all users. Also, networks can be marked with the
`--router:external` attribute to indicate that are external networks (public
internet)

Currently there are four available Networks Flavors:

* IP_LESS_ROUTED: A Layer-3 network where host routes traffic to the external network.
* PHYSICAL_VLAN: A Layer-2 network where a physical VLAN is assigned to the
  network.
* MAC_FILTERED: A Layer-2 network. All networks of this type share the same
  physical VLAN, but isolation is achieved by filtering rules based on a
  unique MAC prefix that is assigned to each network.

The administrator can limit which networks can be created via API with the
`API_ENABLED_NETOWRK_FLAVORS` setting.

The attributes for network objects are the following:

* id: A string representing the UUID for the network.
* name: A human readable name.
* status: String representing the state of the network. Possible values for the
  state include: ACTIVE, DOWN, BUILD, ERROR or 'SNF:DRAINED' (no new ports
  or floating IPs can be created from this network).
* subnets: List of subnet UUIDs that are associated with this network.
* public: Whether network is visible to other users or not.
* user_id/tenant_id: The UUID of the owner of the network.
* admin_state_up: Boolean value indicating the administrative state of the
  network. If 'down' the network does not forward packets.
* router:external: Whether the network is connected to an external router or
  not. (/router API extension)
* SNF:floating_ip_pool: Whether the network can be used to allocate floating
  IPs.

Note: The 'admin_state_up' value is used only for compatibility with Neutron
API. It will be read-only, and will always be True.

Create a new network
^^^^^^^^^^^^^^^^^^^^

Method: POST

URI: /networks

The body of the request must contain the 'type' of the network. Also it can
contain a 'name' attribute.

List Networks
^^^^^^^^^^^^^

Method: GET

URI: /networks

Get details about a network
^^^^^^^^^^^^^^^^^^^^^^^^^^^

METHOD: GET

URI: /networks/$(network_id)

Example response:

+-----------------+-----------------------------------+
| Field           | Value                             |
+=================+===================================+
| admin_state_up  | True                              |
+-----------------+-----------------------------------+
| id              | 42                                |
+-----------------+-----------------------------------+
| name            | Test_network                      |
+-----------------+-----------------------------------+
| network_type    | MAC_FILTERED                      |
+-----------------+-----------------------------------+
| router:external | False                             |
+-----------------+-----------------------------------+
| public          | False                             |
+-----------------+-----------------------------------+
| status          | ACTIVE                            |
+-----------------+-----------------------------------+
| subnets         | []                                |
+-----------------+-----------------------------------+
| SNF:floating_ip | False                             |
+-----------------+-----------------------------------+
| user_id         | 1012fd8c72284c00b133832cd179f896  |
+-----------------+-----------------------------------+
| tenant_id       | 1012fd8c72284c00b133832cd179f896  |
+-----------------+-----------------------------------+

Delete a network
^^^^^^^^^^^^^^^^

METHOD: DELETE

URI:  /networks/$(network_id)

The network cannot be deleted if there are any Ports connected to it or
any FloatingIPs reserved from this network. The subnets that are connected
to this network are automatically deleted upon network deletion.

Update a network
^^^^^^^^^^^^^^^^

METHOD: PUT

URI:  /networks/$(network_id)

Only the name of the network can be updated.


Subnets
=======

A subnet represents L3-Layer characteristics of the network that is associated
with. Specifically, it represents an IP address block that is used in order to
assign addresses to virtual machines. A subnet is associated with a network
when created.


The attributes for subnet objects are the following:

* id: A string representing the UUID for the subnet.
* name: A human readable name.
* network_id: The UUID of the network that the subnet is associated with.
* ip_version: The IP version of the subnet. Can either be 4 or 6, default is 4.
* cidr: cidr representing IP range for this subnet, based on the IP version.
* gateway_ip: Default gateway used by devices in this subnet. If not specified
  the gateway will be the first available IP address. Set to None in order to
  get no gateway.
* enable_dhcp(CR): Boolean value indicating whether nfdhcpd is enabled for this
  subnet or not.
* enable_slaac: Boolean value indicating whether SLAAC is enabled for this
  subnet or not.
* allocation_pools(CR): Subranges of cidr available for dynamic allocation.
  A list of dictionaries of the form {"start": "192.168.2.0", "end": 192.168.2.10"}
* user_id/tenant_id: The UUID of the owner of the network.
* host_routes(R): List of routes that should be used by devices with IPs from
  this subnet.
* dns_nameservers(R): List of DNS name servers used by hosts in this subnet.

Note: 'host_routes' and 'dns_nameservers' is used only for compatibility with
Neutron. These values will be read-only and always be [].


Create a Subnet
^^^^^^^^^^^^^^^

METHOD: POST

URI:  /subnets/

To create a subnet the user must specify the network_id and the cidr for the
subnet. If the CIDR is an IPv6 subnet, the user must set the ip_version to 6.
If allocation pools overlap, or gateway overlaps with allocation_pools then 409
conflict is returned.

Finally, the user can create maximum one subnet of each ip_version, meaning
that a network can have no subnets, or one IPv4 subnet or one IPv6 subnet, or
one IPv4 and one IPv6 subnet. Also the user cannot create a subnet for a
network that has or had a port connected to it.

Note: Bulk creation of subnets, is not supported.

List user subnets
^^^^^^^^^^^^^^^^^

METHOD: GET

URI:  /subnets/

Get details about a subnet
^^^^^^^^^^^^^^^^^^^^^^^^^^^

METHOD: GET

URI:  /subnets/$(subnet_id)

Example response:

+------------------+--------------------------------------------------+
| Field            | Value                                            |
+==================+==================================================+
| allocation_pools | {"start": "192.168.2.2", "end": "192.168.2.254"} |
+------------------+--------------------------------------------------+
| cidr             | 192.168.2.0/24                                   |
+------------------+--------------------------------------------------+
| dns_nameservers  | []                                               |
+------------------+--------------------------------------------------+
| enable_dhcp      | False                                            |
+------------------+--------------------------------------------------+
| gateway_ip       | 192.168.2.1                                      |
+------------------+--------------------------------------------------+
| host_routes      | []                                               |
+------------------+--------------------------------------------------+
| id               | 49ce3872-446c-43e9-aa22-68dbc2bac0b5             |
+------------------+--------------------------------------------------+
| ip_version       | 4                                                |
+------------------+--------------------------------------------------+
| name             | test1                                            |
+------------------+--------------------------------------------------+
| network_id       | 8fc5e2bf-9c1b-4458-8f71-e38177ed23a5             |
+------------------+--------------------------------------------------+
| tenant_id        | 11a65261147d462b998eafb7f696f0ba                 |
+------------------+--------------------------------------------------+
| user_id          | 11a65261147d462b998eafb7f696f0ba                 |
+------------------+--------------------------------------------------+


Delete a subnet
^^^^^^^^^^^^^^^^

METHOD: DELETE

URI:  /subnets/$(subnet_id)

We do not allow deletion of subnets. Subnets will be deleted when the network
is deleted. This call will return 400 (badRequest).


Update a subnet
^^^^^^^^^^^^^^^^

METHOD: PUT

URI:  /subnets/$(subnet_id)


Only the name of the subnet can be updated. This call will return 400 (badRequest)
if the user tries to update any other field.


Ports
=====

A port represents a virtual switch port on a network switch. Virtual machines
attach their interfaces to ports. A port that is connected to a network
gets an IP address for each subnet that is associated with the network. If the
network has no subnets, then the port will have no IP.


The attributes for port objects are the following:

* id: A string representing the UUID for the port.
* network_id: The UUID of the network that this port is associated with.
* name: A human readable name.
* status: String representing the state of the port. Possible values for the
  state include: ACTIVE, DOWN, BUILD, ERROR.
* mac_address: MAC address.
* fixed_ips(R): List of dictionaries subnet_id->ip_address.
* device_id(CR): Device using this port (VM id or Router id).
* device_owner(CR): Entity using this port. e.g., network:router,
  network:router_gateway.
* user_id/tenant_id: The UUID of the owner of the port.
* security_groups(CRUD): List of security groups IDs associated with this port.
* admin_state_up: Boolean value indicating the administrative state of the
  port. If 'down' the port does not forward packets.

.. note:: Due to the way ports are implementing to Ganeti, a port will get an
  IPv6 address from a subnet only when the state of the port becomes 'ACTIVE'.

.. note:: The 'admin_state_up' value is used only for compatibility with
 Neutron API. It will be read-only, and will always be True.

Create a new Port
^^^^^^^^^^^^^^^^^^^^

Method: POST

URI: /ports

The body of the request must contain the 'network_id' of the network that
the port will be associated with. If the request contains a 'device_Id', the
port will be connected to that device.

The new port will get an IPv4 address from each of the subnets that are
associated with that network. If the network has an IPv4 subnet the request
can also contain the 'fixed_ips' attribute containing a specific IPv4 address
to use.

Creating a port to a public network is only supported if the user has a
floating IP from this network (see /floatingips extension) and the 'fixed_ip'
attribute of the request contains the IPv4 address of this floating IP.
Otherwise, badRequest(400) is returned.

Finally, the request can contain the following optional attributes:

* security_groups
* name

Example request:

.. code-block:: json

 {"port": {
     "name": "port1",
     "network_id": "42",
     "device_id": "2",
     "fixed_ips": [
         {
             "ip_address": "192.168.2.20"
         }
      ]
  }



List ports
^^^^^^^^^^^^^

Method: GET

URI: /ports

Get details about a port
^^^^^^^^^^^^^^^^^^^^^^^^^^^

METHOD: GET

URI:  /ports/$(port_id)

Example response:

+-----------------------+---------------------------------------------------------------------------------+
| Field                 | Value                                                                           |
+=======================+=================================================================================+
| admin_state_up        | True                                                                            |
+-----------------------+---------------------------------------------------------------------------------+
| device_id             | 39a02a66-33be-478a-8e9f-012141258678                                            |
+-----------------------+---------------------------------------------------------------------------------+
| device_owner          | network:router_interface                                                        |
+-----------------------+---------------------------------------------------------------------------------+
| fixed_ips             | {"subnet_id": "2313705f-68c1-4e16-80e3-c9fd8c0a5170", "ip_address": "10.0.2.1"} |
+-----------------------+---------------------------------------------------------------------------------+
| id                    | ff15e3fe-7b39-4adc-ae98-a7e29588977e                                            |
+-----------------------+---------------------------------------------------------------------------------+
| mac_address           | fa:16:3e:c1:63:06                                                               |
+-----------------------+---------------------------------------------------------------------------------+
| name                  | "test_port"                                                                     |
+-----------------------+---------------------------------------------------------------------------------+
| network_id            | 2f04b49f-ca49-4b93-9139-11a4eca35fdd                                            |
+-----------------------+---------------------------------------------------------------------------------+
| security_groups       | []                                                                              |
+-----------------------+---------------------------------------------------------------------------------+
| status                | DOWN                                                                            |
+-----------------------+---------------------------------------------------------------------------------+
| tenant_id             | 1012fd8c72284c00b133832cd179f896                                                |
+-----------------------+---------------------------------------------------------------------------------+
| user_id               | 1012fd8c72284c00b133832cd179f896                                                |
+-----------------------+---------------------------------------------------------------------------------+

Delete a port
^^^^^^^^^^^^^^^^

METHOD: DELETE

URI:  /ports/$(port_id)

Deleting a port from a public network is only allowed if the port has
been creating using a floating IP address.

Update a port
^^^^^^^^^^^^^^^^

METHOD: PUT

URI:  /ports/$(port_id)

Only the name of the port can be updated.



Floating IPs
============

Floating IPs are addresses on external networks (and so can be defined only on
networks on which the attribute `router:external` has been set to True) that
are marked as floating IP pools (`SNF:floating_ip_pool`). In the Neutron API,
floating IPs are associated with specific ports and IP addresses on private
networks and are used to allow an instance from a private network to access the
external network. Cyclades are able to associate a floating IP with an instance
without the restriction that the instance must already have a port and a
private IP from a private network. In order to avoid this limitation of Neutron
API, Cyclades are using a slightly modified and extended API.

The attributes of floating IP objects are the following:

* id: A string representing the UUID for the floating IP.
* floating_network_id: The UUID of the external network with which the floating
  IP is associated.
* floating_ip_address: The IPv4 address of the floating IP.
* fixed_ip_address: The value of this option is always `None`.
* port_id: The port that is currently using this floating IP.
* instance_id: The device that is currently using this floating IP.
* user_id/tenant_id: The UUID of the owner of the floating IP.


Floating IPs can be used via the /ports API. In order to attach a floating IP
to a server, the user must create a port that specified the IPv4 address
of the floating IP in the `fixed_ips` attribute of the port creation request.
Also, the floating IP can be detached from the server by destroying the
port that the floating IP is attached to.

Create(reserve) a floating IP
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

METHOD: POST

URI: /floatingips

The body of the request contains the id of the external network
(`floating_network_id`). If no address is specified (`floating_ip_address`),
an address will automatically be allocated from the pool addresses of the
external network.

List floating IPs
^^^^^^^^^^^^^^^^^

METHOD: GET

URI: /floatingips

Show a floating IP
^^^^^^^^^^^^^^^^^^

METHOD: GET

URI: /floatingips/$(floatingip_id)

Example response:

.. code-block:: console

 {
   "floatingip": {
     "id": "5923c02a-a162-4044-a432-9e52d6d819ce",
     "floating_ip_address": 192.168.1.227,
     "floating_network_id": 00983314-2f3c-43e9-acb0-9fd7cdb32231,
     "router_id": null,
     "device_id": 42,
     "tenant_id: "1012fd8c72284c00b133832cd179f896",
     "user_id": "1012fd8c72284c00b133832cd179f896"
   }
 }


Delete a Floating IP
^^^^^^^^^^^^^^^^^^^^

METHOD: DELETE

URI: /floatingips/$(floatingip_id)

This operation removes(releases) the floating IP. If it associated with a
device(port), the port is automatically removed.


Routers
=======


.. note:: This section contains a draft design document for virtual routers,
 and currently there is no implementation for this API.

A router is a logical entity that can be used to:

* interconnect subnets and forward traffic among them, and
* NAT internal traffic to external networks.

A router is associated with subnets through interfaces. The router gets an
interface with each subnet that is associated with. By default, the IP address
of such interface is the gateway of the subnet. Besides the interfaces, the
router also gets a Port for each network that is associated with (through
the corresponding subnets). These ports are created automatically when
interfaces are added to the router, have as device_owner the router, and
can not be managed with the Port API.

Besides the internal subnets, the router, can also be associated with an
external network in order to NAT traffic from internal networks to the external
one. The id of the external network is specified in the `external_gateway_info`
attribute of the network, and a port will be created for the router with an
IP address from the range of the public network. Besides the network id, the
user can also specify a floating IP from this network, to use as the router IP.
This port can also not be managed with the Port API.

The attributes for Router objects are the following:

* id: A string representing the UUID for the router.
* name: A human readable name.
* status: String representing the state of the network. Possible values for the
  state include: ACTIVE, DOWN, BUILD, ERROR.
* user_id/tenant_id: The UUID of the owner of the router.
* admin_state_up: Boolean value indicating the administrative state of the
  router. If 'down' the router does not forward packets.
* external_gateway_info: Dictionary with the information about the external
  gateway for the router.

Create a new router
^^^^^^^^^^^^^^^^^^^^

Method: POST

URI: /routers

The body of the request contains the name of the router. The new router that
is created does not have any internal interface and so it is not associated
with any subnet.

Also, the used can specify an external gateway for the router at create time.
This is done by specifying the network_id in the `external_gateway_info`
attribute. This network must have the attribute `router:external` set to
`True`. Besides the id of the network, the used can also specify one of his
floating IPs to use. An example request is the following


.. code-block:: console

  {
    "router":
    {
      "name": "example_router",
      "external_gateway_info":
      {
        "network_id": "42",
        "floating_ip_id": "142"
      }
    }
  }

List routers
^^^^^^^^^^^^^

Method: GET

URI: /routers

Get details about a router
^^^^^^^^^^^^^^^^^^^^^^^^^^^

METHOD: GET

URI: /routers/$(router_id)

Example response:

.. code-block:: console

  {
    "id": "5",
    "name": "example_router",
    "status": "ACTIVE",
    "user_id": "1012fd8c72284c00b133832cd179f896",
    "tenant_id": "1012fd8c72284c00b133832cd179f896",
    "external_gateway_info": {
      "network_id": "42",
      "floating_ip_id": "142"
    }
  }

Delete a router
^^^^^^^^^^^^^^^^

METHOD: DELETE

URI:  /routers/$(router_id)

This operation removes a logical router;
the operation will fail if the router still has some internal interfaces.

Update a router
^^^^^^^^^^^^^^^^

METHOD: PUT

URI:  /routers/$(router_id)

Only the `name` of the router and the `external_gateway_info` can be updated.

Add interface to router
^^^^^^^^^^^^^^^^^^^^^^^

METHOD: PUT

URI: /routers/$(router_id)/add_router_interface

The body of the request contains only the id of the subnet that the router
will be associated to.

Remove interface from router
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

METHOD: PUT

URI: /routers/$(router_id)/remove_router_interface

The body of the request contains only the id of the subnet that the router
will be detached from.




General Implementation Details
==============================

Creation of a network corresponds to only creating a Network object in the
Cyclades DB. Also, creation of a subnet corresponds to creation of a Subnet in
the Cyclades DB and the of the corresponding allocation pools. The Ganeti
network will only be created in the Ganeti backend when a port is connected to
this network.  Updating fields of Ganeti networks is really hard (e.g.,
changing the dhcp option) or impossible (e.g., changing the subnet). For this
reason, if the network has been created in a Ganeti backend, then it will be
marked as read-only!

A port is mapped to a Ganeti NIC directly. The port will be created in DB in
the "BUILD" state and an OP_INSTANCE_MODIFY will be issued to Ganeti to create
the NIC in the specified VM. When the job successfully completes, the NIC will
be updated to state "ACTIVE" in the DB. Also the MAC address that was allocated
from Ganeti will be stored in the updated NIC.
