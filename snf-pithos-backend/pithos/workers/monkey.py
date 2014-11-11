# -*- coding: utf-8 -
#
# Copyright (C) 2010-2014 GRNET S.A.
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


from archipelago import common
from archipelago.common import posixfd_signal_desc
from ctypes import cast, POINTER
import os

try:
    from gevent import select
except ImportError:
    import select


def pithos_xseg_wait_signal_green(ctx, sd, timeout):
    posixfd_sd = cast(sd, POINTER(posixfd_signal_desc))
    fd = posixfd_sd.contents.fd
    select.select([fd], [], [], timeout / 1000000.0)
    while True:
        try:
            os.read(fd, 512)
        except OSError as (e, msg):
            if e == 11:
                break
            else:
                raise OSError(e, msg)


def patch_Request():
    common.xseg_wait_signal_green = pithos_xseg_wait_signal_green
