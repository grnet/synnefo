import ipaddr

from bitarray import bitarray
from base64 import b64encode, b64decode


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
