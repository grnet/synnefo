.. _stats-api-guide:

Statistics API guide
********************

Overview
========

Synnefo exposes basic statistics about Cyclades and Astakos services via the
`admin` API endpoint of each service. Access to `admin` endpoint is only
allowed to users that belong to Astakos groups defined in the
`ADMIN_STATS_PERMITTED_GROUPS` setting for Cyclades and
`ASTAKOS_STATS_PERMITTED_GROUPS` setting for Astakos, which by default contain
the `admin-stats` group. For example, to allow <user_id> to access stats,
you should run the following commands in the Astakos node:

.. code-block:: console

  snf-manage group-add admin-stats
  snf-manage user-modify --add-group=admin-stats <user_id>


Astakos Statistics
==================

Astakos Service exposes basic statistics by the `admin/stats/detail` endpoint.
The response is a JSON document containing basic information about the
available authentication providers, users and allocated resources.

Information about users and resources is exposed per authentication provider.
However, because some users may using more than one authentication providers,
the special keyword `all` is used to denote the total number of
users/resources, no matter which combination of authentication providers is
used.


Example Response:

.. code-block:: javascript

 {
     "providers": [          # List of available authentication providers
         "local",
         "shibboleth",
     ],
     "users": {
         "all": {            # Statistics about users (using any provider(s))
             "total": 1,     # Total number of users
             "verified": 1,  # Number of users with verified e-mail
             "active": 1     # Number of active users
         },
         "local": {          # Statistics about users using the 'local' provider
             "total": 1,     # Total number of users
             "verified": 1   # Number of users with verified e-mail
             "active": 1,    # Number of active users
             "exclusive": 1, # Number of active users using *only* the local provider
         }
         "shibboleth": {
            ...
         }
         ...
     },
     "resources": {
        "all": {                 # Statistics about resources allocated to all users (using any provider(s))
             "cyclades.vm": {
                 "allocated": 4, # Maximum number of VMs that can be created (quota limit)
                 "used": 1,      # Number of VMs that currently exist (quota usage)
                 "description": "Number of virtual machines",
                 "unit": null
             },
             "cyclades.ram": {
                 "allocated": 8589934592,
                 "used": 134217728,
                 "description": "Virtual machine memory size of running servers",
                 "unit": "bytes"
             },
             ....
         },
         "local": {              # Statistics about resources allocated to users that are using
                                 # *only* the 'local' provider
             "cyclades.vm": {
                 "allocated": 4,
                 "used": 1,
                 "description": "Number of virtual machines",
                 "unit": null
             },
             "cyclades.ram": {
                 "allocated": 8589934592,
                 "used": 134217728,
                 "description": "Virtual machine memory size of running servers",
                 "unit": "bytes"
             },
             ...
         }
         ...
     },
     "datetime": "Thu May  8 13:44:44 2014"
 }


Cyclades Statistics
===================

Cyclades Service exposes basic statistics by the `admin/stats/detail` endpoint.
The response is a JSON document containing basic information about the physical
infastructure (Ganeti clusters) and Cyclades virtual servers and networks.

Specifically the response contains the following fields:

 * `clusters`: Information about each Ganeti cluster
 * `servers`: Information about Cyclades Virtual Servers
 * `networks`: Information about Cyclades Virtual Networks
 * `ip_pools`: Information about Cyclades public IPv4 address pools
 * `images`: Information about the images are used by Cyclades Virtual Servers


.. code-block:: javascript

 {
    "clusters": {
      "ganeti-cluster-1": {  # Name of the Ganeti cluster
         "disk_templates": [ # List of enabled disk templates
            "drbd",
            "plain",
            "ext",
            "sharedfile",
            "file"
          ],
            "drained": true,      # If the cluster is marked as drained in Cyclades DB
            "offline": false,     # If the cluster is marked as offline in Cyclades DB
            "hypervisor": "kvm",  # The cluster's hypervisor
            "virtual_servers": 10,       # Number of of Cyclades VMs
            "virtual_cpu": 14,           # Number of CPUs of Cyclades VMs
            "virtual_disk": 472446402560 # Size (bytes) of disk of Cyclades VMs of all disk templates
            "virtual_ram": 26843545600   # Size (bytes) of RAM of Cyclades VMs
            "nodes": { # The nodes of the Ganeti cluster
                "node0-ganeti-cluster-1": {
                    "cpu": 24,          # Number of Physical CPUs
                    "vm_capable": true, # If the node is capable to host VMs
                    "drained": false,   # If the node is marked as drained
                    "offline": false,   # If the node is marked as offline
                    "instances": 61,    # Number of Ganeti instances
                                        # (including instances that do not belong to Cyclades)
                    "disk": {
                        "free": 973430849536,  # Size of the node's free disk
                        "total": 4200159248384 # Size of the node's total disk
                    },
                    "ram": {
                        "free": 91246034944,   # Size of the node's free RAM
                        "total": 203226611712  # Size of the node's total RAM
                    }
                },
    "servers": { # Statistics about Cyclades VMs based on the operational state (started, stopped, error)
        "started": {
            "count": 10,  # Number of started VMs
            "cpu": {
                "1": 6,   # Number of started VMs with 1 CPU
                "2": 4    # Number of started VMs with 2 CPUs
            },
            "disk": { # Statistics about started VMs based on disk template
                "drbd": { # Statistics about started VMs with DRBD disk template based on disk size
                    "10737418240": 2 # Number of started VMs with 10GB DRBD disk
                    "21474836480": 3 # Number of started VMs with 20GB DRBD disk
                },
                "ext_vlmc": {
                    "107374182400": 3, # Number of started VMs with 100GB ext_vlmc disk
                    "32212254720": 2   # Number of started VMs with 30GB ext_vlmc disk
                }
            },
            "ram": { # Statistics about started VMs based on RAM
                "1073741824": 5, # Number of stared VMs with 1GB RAM
                "4294967296": 5, # Number of started VMs with 4GB RAM
            }
        },
        "stopped": {
          ...
        }
        "error": {
          ...
        }
    "networks": { # Statistics about Cyclades networks based on the network's flavor
        "CUSTOM": {
            "active": 0,
            "error": 0
        },
        "IP_LESS_ROUTED": {
            "active": 15,
            "error": 0
        },
        "MAC_FILTERED": {
            "active": 882,  # Number of MAC_FILTERED active networks
            "error": 0
        },
        "PHYSICAL_VLAN": {
            "active": 0,
            "error": 0
        }
    },
    "ip_pools": { # Statistics about Cyclades public IPv4 pools based on the pools state (active, drained)
        "active": {
            "count": 13, # Number of active public IPv4 pools
            "free": 1195, # Number of free IPv4 addresses in all active IPv4 pools
            "total": 8701 # Number of total IPv4 addresses in all active IPv4 pools

        },
        "drained": {
            "count": 1, # Number of drained public IPv4 pools
            "free": 1195, # Number of free IPv4 addresses in all drained IPv4 pools
            "total": 8701 # Number of total IPv4 addresses in all drained IPv4 pools
        }
    },
    "images": { # Statistics about the images of non-deleted Cyclades VMs
        "system:centos": 1, # Number of VMs that have been created with a 'centos' image of the system user
        "system:debian": 4,
        "unknown:unknown": 4, # Number of VMs that have been created with an unknown image (includes deleted images)
        "user:debian": 1,
        "user:unknown": 1
    },
 }


Finally, to retrieve statistics per Ganeti backend, the backend ID should be
included in the query parameters: `admin/stats/detail?backend=<backend_id>`.
In this case, the response will not contain the 'networks' and 'ip_pools'
sections which are not available per Ganeti backend.
