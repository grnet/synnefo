#
# Copyright (C) 2010-2017 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import factory
from synnefo.userdata import models


class PublicKeyPairFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.PublicKeyPair
    name = factory.Sequence(lambda n: 'keypair-%d' % n)
    content = 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCkF3MX59OrlBs3dH5CU7lNmvpbrgZxSpyGjlnE8Flkirnc/Up22lpjznoxqeoTAwTW034k7Dz6aYIrZGmQwe\2TkE084yqvlj45Dkyoj95fW/sZacm0cZNuL69EObEGHdprfGJQajrpz22NQoCD8TFB8Wv+8om9NH9Le6s+WPe98WC77KLw8qgfQsbIey+JawPWl4O67ZdL5xrypuRjfIPWjgy/VH85IXg/Z/GONZ2nxHgSShMkwqSFECAC5L3PHB+0+/12M/iikdatFSVGjpuHvkLOs3oe7m6HlOfluSJ85BzLWBbvva93qkGmLg4ZAc8rPh2O+YIsBUHNLLMM/oQp'
    fingerprint = '7e:eb:ab:24:ba:d1:e1:88:ae:9a:fb:66:53:df:d3:bd'
    type = 'ssh'
