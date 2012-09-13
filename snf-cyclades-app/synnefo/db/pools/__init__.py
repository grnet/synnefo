from bitarray import bitarray
from base64 import b64encode, b64decode
import ipaddr

AVAILABLE = True
UNAVAILABLE = False


class PoolManager(object):
    """PoolManager for DB PoolTable models.

    This class implements a persistent Pool mechanism based on rows of
    PoolTable objects. Values that are pooled by this class, are mapped to an
    index on a bitarray, which is the one that is stored on the DB.

    The object that will be used in order to initialize this pool, must have
    two string attributes (available_map and reserved_map) and the size of the
    pool.

    Subclasses of PoolManager must implement value_to_index and index_to_value
    method's in order to denote how the value will be mapped to the index in
    the bitarray.

    Important!!: Updates on a PoolManager object are not reflected to the DB,
    until save() method is called.

    """
    def __init__(self, pool_table):
        self.pool_table = pool_table

        if pool_table.available_map:
            self.available = _bitarray_from_string(pool_table.available_map)
            self.reserved = _bitarray_from_string(pool_table.reserved_map)
        else:
            size = self.pool_table.size
            padding = find_padding(size)
            size = size + padding
            self.pool_size = size
            self.available = self._create_empty_pool()
            self.reserved = self._create_empty_pool()
            for i in xrange(0, padding):
                self._reserve(size - i - 1, external=True)

    def _create_empty_pool(self):
        assert(self.pool_size % 8 == 0)
        ba = bitarray(self.pool_size)
        ba.setall(AVAILABLE)
        return ba

    @property
    def pool(self):
        return (self.available & self.reserved)

    def get(self):
        """Get a value from the pool."""
        if self.empty():
            raise EmptyPool
        # Get the first available index
        index = int(self.pool.index(AVAILABLE))
        self._reserve(index)
        return self.index_to_value(index)

    def put(self, value, external=False):
        """Return a value to the pool."""
        if value is None:
            raise ValueError
        index = self.value_to_index(value)
        self._release(index, external)

    def reserve(self, value, external=True):
        """Reserve a value."""
        index = self.value_to_index(value)
        self._reserve(index, external)
        return True

    def save(self, db=True):
        """Save changes to the DB."""
        self.pool_table.available_map = _bitarray_to_string(self.available)
        self.pool_table.reserved_map = _bitarray_to_string(self.reserved)
        if db:
            self.pool_table.save()

    def empty(self):
        """Return True when pool is empty."""
        return not self.pool.any()

    def size(self):
        return self.pool.length()

    def _reserve(self, index, external=False):
        if external:
            self.reserved[index] = UNAVAILABLE
        else:
            self.available[index] = UNAVAILABLE

    def _release(self, index, external=False):
        if external:
            self.reserved[index] = AVAILABLE
        else:
            self.available[index] = AVAILABLE

    def count_available(self):
        return self.pool.count(AVAILABLE)

    def count_unavailable(self):
        return self.pool.count(UNAVAILABLE)

    def count_reserved(self):
        return self.reserved.count(UNAVAILABLE)

    def count_unreserved(self):
        return self.size() - self.count_reserved()

    def is_available(self, value, index=False):
        if not index:
            idx = self.value_to_index(value)
        else:
            idx = value
        return self.pool[idx] == AVAILABLE

    def is_reserved(self, value, index=False):
        if not index:
            idx = self.value_to_index(value)
        else:
            idx = value
        return self.reserved[idx] == UNAVAILABLE

    def to_01(self):
        return self.pool.to01()

    def to_map(self):
        return self.to_01().replace("0", "X").replace("1", ".")

    def index_to_value(self, index):
        raise NotImplementedError

    def value_to_index(self, value):
        raise NotImplementedError


class EmptyPool(Exception):
    pass


def find_padding(size):
    extra = size % 8
    return extra and (8 - extra) or 0


def bitarray_to_01(bitarray_):
    return bitarray_.to01()


def bitarray_to_map(bitarray_):
    return bitarray_to_01(bitarray_).replace("0", "X").replace("1", ".")


def _bitarray_from_string(bitarray_):
    ba = bitarray()
    ba.fromstring(b64decode(bitarray_))
    return ba


def _bitarray_to_string(bitarray_):
    return b64encode(bitarray_.tostring())

##
## Custom pools
##


class BridgePool(PoolManager):
    def index_to_value(self, index):
        return self.pool_table.base + str(index)

    def value_to_index(self, value):
        return int(value.replace(self.pool_table.base, ""))


class MacPrefixPool(PoolManager):
    def __init__(self, pool_table):
        do_init = False if pool_table.available_map else True
        super(MacPrefixPool, self).__init__(pool_table)
        if do_init:
            for i in xrange(1, self.size()):
                if not self.validate_mac(self.index_to_value(i)):
                    self._reserve(i, external=True)
            # Reserve the first mac-prefix for public-networks
            self._reserve(0, external=True)

    def index_to_value(self, index):
        """Convert index to mac_prefix"""
        base = self.pool_table.base
        a = hex(int(base.replace(":", ""), 16) + index).replace("0x", '')
        mac_prefix = ":".join([a[x:x + 2] for x in xrange(0, len(a), 2)])
        return mac_prefix

    def value_to_index(self, value):
        base = self.pool_table.base
        return int(value.replace(":", ""), 16) - int(base.replace(":", ""), 16)

    @staticmethod
    def validate_mac(value):
        hex_ = value.replace(":", "")
        bin_ = bin(int(hex_, 16))[2:].zfill(8)
        return bin_[6] == '1' and bin_[7] == '0'


# class IPPool(PoolManager):
#     def __init__(self, network):
#         do_init = False if network.pool else True
#         self.net = ipaddr.IPNetwork(network.subnet)
#         network.size = self.net.numhosts
#         super(IPPool, self).__init__(network)
#         gateway = network.gateway
#         self.gateway = gateway and ipaddr.IPAddress(gateway) or None
#         if do_init:
#             self._reserve(0)
#             self.put(gateway)
#             self._reserve(self.size() - 1)
#
#     def value_to_index(self, value):
#         addr = ipaddr.IPAddress(value)
#         return int(addr) - int(self.net.network)
#
#     def index_to_value(self, index):
#         return str(self.net[index])

class IPPool(object):
    """IP pool class, based on a models.Network object

    Implementation of an IP address pool based on a models.Network
    object.

    """
    def __init__(self, network):
        self.net = network
        self.network = ipaddr.IPNetwork(self.net.subnet)

        gateway = self.net.gateway
        self.gateway = gateway and ipaddr.IPAddress(gateway) or None

        if self.net.reservations:
            self.reservations = bitarray()
            self.reservations.fromstring(b64decode(self.net.reservations))
        else:
            numhosts = self.network.numhosts
            self.reservations = bitarray(numhosts)
            self.reservations.setall(False)
            self.reservations[0] = True
            self.reservations[numhosts - 1] = True
            if self.gateway:
                self.reserve(self.gateway)

    def _contains(self, address):
        if address is None:
            return False
        addr = ipaddr.IPAddress(address)

        return (addr in self.network)

    def _address_index(self, address):
        """Convert IP address to bitarray index

        """
        if not self._contains(address):
            raise Exception("%s does not contain %s" %
                            (str(self.network), address))
        addr = ipaddr.IPAddress(address)

        return int(addr) - int(self.network.network)

    def _mark(self, address, value):
        index = self._address_index(address)
        self.reservations[index] = value

    def reserve(self, address):
        self._mark(address, True)

    def release(self, address):
        self._mark(address, False)

    def is_reserved(self, address):
        index = self._address_index(address)
        return self.reservations[index]

    def is_full(self):
            return self.reservations.all()

    def count_reserved(self):
        return self.reservations.count(True)

    def count_free(self):
        return self.reservations.count(False)

    def get_map(self):
        return self.reservations.to01().replace("1", "X").replace("0", ".")

    def get_free_address(self):
        """Get the first available address."""
        if self.is_full():
            raise IPPool.IPPoolExhausted("%s if full" % str(self.network))

        index = self.reservations.index(False)
        address = str(self.network[index])
        self.reserve(address)
        return address

    def save(self):
        """Update the Network model and save it to DB."""
        self._update_network()
        self.net.save()

    def _update_network(self):
        self.net.reservations = b64encode(self.reservations.tostring())

    class IPPoolExhausted(Exception):
        pass
