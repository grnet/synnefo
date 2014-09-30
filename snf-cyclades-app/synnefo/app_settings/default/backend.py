# -*- coding: utf-8 -*-
#
# Ganeti backend configuration
###################################

# This prefix gets used when determining the instance names
# of Synnefo VMs at the Ganeti backend.
# The dash must always appear in the name!
BACKEND_PREFIX_ID = "snf-"

# The following dictionary defines deployment-specific
# arguments to the RAPI CreateInstance call.
# At a minimum it should contain the
# 'os' and 'hvparams' keys.
#
# More specifically:
# a) os:
#    The OS provider to use (customized Ganeti Instance Image)
# b) hvparams:
#    Hypervisor-specific parameters (serial_console = False, see #785),
#    for each hypervisor(currently 'kvm', 'xen-pvm' and 'xen-hvm').
# c) If using the DRBD disk_template, you may want to include
#    wait_for_sync = False (see #835).
#
GANETI_CREATEINSTANCE_KWARGS = {
    'os': 'snf-image+default',
    'hvparams': {"kvm": {'serial_console': False},
                 "xen-pvm": {},
                 "xen-hvm": {}},
}

# If True, qemu-kvm will hotplug a NIC when connecting a vm to
# a network. This requires qemu-kvm=1.0.
GANETI_USE_HOTPLUG = True

# If True, Ganeti will try to allocate new instances only on nodes that are
# not already locked. This might result in slightly unbalanced clusters.
GANETI_USE_OPPORTUNISTIC_LOCKING = True

# If False, Ganeti will not wait for the disk mirror to sync
# (--no-wait-for-sync option in Ganeti). Useful only for DRBD template.
GANETI_DISKS_WAIT_FOR_SYNC = False

# This module implements the strategy for allocating a vm to a backend
BACKEND_ALLOCATOR_MODULE = "synnefo.logic.allocators.default_allocator"
# Refresh backend statistics timeout, in minutes, used in backend allocation
BACKEND_REFRESH_MIN = 15

# Maximum number of NICs per Ganeti instance. This value must be less or equal
# than 'max:nic-count' option of Ganeti's ipolicy.
GANETI_MAX_NICS_PER_INSTANCE = 8

# Maximum number of disks per Ganeti instance. This value must be less or equal
# than 'max:disk-count' option of Ganeti's ipolicy.
GANETI_MAX_DISKS_PER_INSTANCE = 8

# The following setting defines a dictionary with key-value parameters to be
# passed to each Ganeti ExtStorage provider. The setting defines a mapping from
# the provider name, e.g. 'archipelago' to a dictionary with the actual
# arbitrary parameters.
GANETI_DISK_PROVIDER_KWARGS = {}

# List of ExtStorage providers that support cloning. For these providers, the
# hashmap of the image is passed as an ExtStorage disk parameter('origin') and,
# since disk will be already filled with data, 'snf-image' performs only
# customization (no data copying).
GANETI_CLONE_PROVIDERS = ['vlmc', 'archipelago']
