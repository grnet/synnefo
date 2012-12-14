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
        self.pool_size = pool_table.size
        if pool_table.available_map:
            self.available = _bitarray_from_string(pool_table.available_map)
            self.reserved = _bitarray_from_string(pool_table.reserved_map)
        else:
            self.available = self._create_empty_pool(self.pool_size)
            self.reserved = self._create_empty_pool(self.pool_size)
            self.add_padding(self.pool_size)

    def _create_empty_pool(self, size):
        ba = bitarray(size)
        ba.setall(AVAILABLE)
        return ba

    def add_padding(self, pool_size):
        bits = find_padding(pool_size)
        self.available.extend([UNAVAILABLE] * bits)
        self.reserved.extend([UNAVAILABLE] * bits)

    def cut_padding(self, pool_size):
        bits = find_padding(pool_size)
        self.available = self.available[:-bits]
        self.reserved = self.reserved[:-bits]

    @property
    def pool(self):
        return (self.available & self.reserved)

    def get(self):
        """Get a value from the pool."""
        if self.empty():
            raise EmptyPool
        # Get the first available index
        index = int(self.pool.index(AVAILABLE))
        assert(index < self.pool_size)
        self._reserve(index)
        return self.index_to_value(index)

    def put(self, value, external=False):
        """Return a value to the pool."""
        if value is None:
            raise ValueError
        index = self.value_to_index(value)
        self._release(index, external)

    def reserve(self, value, external=False):
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
        """Return the size of the bitarray(original size + padding)."""
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
        return self.reserved[:self.pool_size].count(UNAVAILABLE)

    def count_unreserved(self):
        return self.pool_size - self.count_reserved()

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
        return self.pool[:self.pool_size].to01()

    def to_map(self):
        return self.to_01().replace("0", "X").replace("1", ".")

    def extend(self, bits_num):
        assert(bits_num >= 0)
        self.resize(bits_num)

    def shrink(self, bits_num):
        assert(bits_num >= 0)
        size = self.pool_size
        tmp = self.available[(size - bits_num): size]
        if tmp.count(UNAVAILABLE):
            raise Exception("Can not shrink. In use")
        self.resize(-bits_num)

    def resize(self, bits_num):
        if bits_num == 0:
            return
        # Cut old padding
        self.cut_padding(self.pool_size)
        # Do the resize
        if bits_num > 0:
            self.available.extend([AVAILABLE] * bits_num)
            self.reserved.extend([AVAILABLE] * bits_num)
        else:
            self.available = self.available[:bits_num]
            self.reserved = self.reserved[:bits_num]
        # Add new padding
        self.pool_size = self.pool_size + bits_num
        self.add_padding(self.pool_size)
        self.pool_table.size = self.pool_size

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
    ba.frombytes(b64decode(bitarray_))
    return ba


def _bitarray_to_string(bitarray_):
    return b64encode(bitarray_.tobytes())

##
## Custom pools
##


class BridgePool(PoolManager):
    def index_to_value(self, index):
        # Bridge indexes should start from 1
        return self.pool_table.base + str(index + 1)

    def value_to_index(self, value):
        return int(value.replace(self.pool_table.base, "")) - 1


class MacPrefixPool(PoolManager):
    def __init__(self, pool_table):
        do_init = False if pool_table.available_map else True
        super(MacPrefixPool, self).__init__(pool_table)
        if do_init:
            for i in xrange(1, self.pool_size):
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


class IPPool(PoolManager):
    def __init__(self, pool_table):
        do_init = False if pool_table.available_map else True
        network = pool_table.network
        self.net = ipaddr.IPNetwork(network.subnet)
        if not pool_table.size:
            pool_table.size = self.net.numhosts
        super(IPPool, self).__init__(pool_table)
        gateway = network.gateway
        self.gateway = gateway and ipaddr.IPAddress(gateway) or None
        if do_init:
            self._reserve(0, external=True)
            if gateway:
                self.reserve(gateway, external=True)
            self._reserve(self.pool_size - 1, external=True)

    def value_to_index(self, value):
        addr = ipaddr.IPAddress(value)
        return int(addr) - int(self.net.network)

    def index_to_value(self, index):
        return str(self.net[index])
