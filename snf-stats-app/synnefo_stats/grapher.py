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

from django.http import HttpResponse
from django.utils.encoding import smart_str

import gd
import os
import os.path

from cStringIO import StringIO

import rrdtool

from Crypto.Cipher import AES
from base64 import urlsafe_b64decode
from hashlib import sha256

from synnefo_stats import settings

from snf_django.lib.api import faults, api_method

from logging import getLogger
log = getLogger(__name__)


def read_file(filepath):
    f = open(filepath, "r")

    try:
        data = f.read()
    finally:
        f.close()

    return data


def draw_cpu_bar(fname, outfname=None):
    fname = os.path.join(fname, "cpu", "virt_cpu_total.rrd")

    try:
        values = rrdtool.fetch(fname, "AVERAGE")[2][-20:]
    except rrdtool.error:
        values = [(0.0, )]

    v = [x[0] for x in values if x[0] is not None]
    if not v:
        # Fallback in case we only get NaNs
        v = [0.0]
    # Pick the last value
    value = v[-1]

    image = gd.image((settings.IMAGE_WIDTH, settings.HEIGHT))

    border_color = image.colorAllocate(settings.BAR_BORDER_COLOR)
    white = image.colorAllocate((0xff, 0xff, 0xff))
    background_color = image.colorAllocate(settings.BAR_BG_COLOR)

    if value >= 90.0:
        line_color = image.colorAllocate((0xff, 0x00, 0x00))
    elif value >= 75.0:
        line_color = image.colorAllocate((0xda, 0xaa, 0x00))
    else:
        line_color = image.colorAllocate((0x00, 0xa1, 0x00))

    image.rectangle((0, 0),
                    (settings.WIDTH - 1, settings.HEIGHT - 1),
                    border_color, background_color)
    image.rectangle((1, 1),
                    (int(value / 100.0 * (settings.WIDTH - 2)),
                     settings.HEIGHT - 2),
                    line_color, line_color)
    image.string_ttf(settings.FONT, 8.0, 0.0,
                     (settings.WIDTH + 1, settings.HEIGHT - 1),
                     "CPU: %.1f%%" % value, white)

    io = StringIO()
    image.writePng(io)
    io.seek(0)
    data = io.getvalue()
    io.close()
    return data


def draw_net_bar(fname, outfname=None):
    dname = os.path.join(fname, "interface")

    if not os.path.isdir(dname):
        raise faults.ItemNotFound("VM has no attached NICs")

    fnames = [os.path.join(dname, rrdfile) for rrdfile in os.listdir(dname)]

    if not fnames:
        raise faults.ItemNotFound("VM has no attached NICs")

    rx_value = 0
    tx_value = 0
    for fname in fnames:
        try:
            values = rrdtool.fetch(fname, "AVERAGE")[2][-20:]
        except rrdtool.error:
            values = [(0.0, 0.0)]

        v = [x for x in values if x[0] is not None and x[1] is not None]
        if not v:
            # Fallback in case we only get NaNs
            v = [(0.0, 0.0)]

        rxv, txv = v[-1]

        # Convert to bits
        rx_value += rxv * 8 / 10 ** 6
        tx_value += txv * 8 / 10 ** 6

    max_value = (int(max(rx_value, tx_value) / 50) + 1) * 50.0

    image = gd.image((settings.IMAGE_WIDTH, settings.HEIGHT))

    border_color = image.colorAllocate(settings.BAR_BORDER_COLOR)
    white = image.colorAllocate((0xff, 0xff, 0xff))
    background_color = image.colorAllocate(settings.BAR_BG_COLOR)

    tx_line_color = image.colorAllocate((0x00, 0xa1, 0x00))
    rx_line_color = image.colorAllocate((0x00, 0x00, 0xa1))

    image.rectangle((0, 0),
                    (settings.WIDTH - 1, settings.HEIGHT - 1),
                    border_color, background_color)
    image.rectangle((1, 1),
                    (int(tx_value / max_value * (settings.WIDTH - 2)),
                     settings.HEIGHT / 2 - 1),
                    tx_line_color, tx_line_color)
    image.rectangle((1, settings.HEIGHT / 2),
                    (int(rx_value / max_value * (settings.WIDTH - 2)),
                     settings.HEIGHT - 2),
                    rx_line_color, rx_line_color)
    image.string_ttf(settings.FONT, 8.0, 0.0,
                     (settings.WIDTH + 1, settings.HEIGHT - 1),
                     "TX/RX: %.2f/%.2f Mbps" % (tx_value, rx_value), white)

    io = StringIO()
    image.writePng(io)
    io.seek(0)
    data = io.getvalue()
    io.close()
    return data


def draw_cpu_ts(fname, outfname):
    fname = os.path.join(fname, "cpu", "virt_cpu_total.rrd")
    outfname += "-cpu.png"

    rrdtool.graph(outfname, "-s", "-1d", "-e", "-20s",
                  # "-t", "CPU usage",
                  "-v", "%",
                  # "--lazy",
                  "DEF:cpu=%s:value:AVERAGE" % fname,
                  "LINE1:cpu#00ff00:")

    return read_file(outfname)


def draw_cpu_ts_w(fname, outfname):
    fname = os.path.join(fname, "cpu", "virt_cpu_total.rrd")
    outfname += "-cpu-weekly.png"

    rrdtool.graph(outfname, "-s", "-1w", "-e", "-20s",
                  # "-t", "CPU usage",
                  "-v", "%",
                  # "--lazy",
                  "DEF:cpu=%s:value:AVERAGE" % fname,
                  "LINE1:cpu#00ff00:")

    return read_file(outfname)


def draw_net_ts(fname, outfname):
    outfname += "-net.png"

    dname = os.path.join(fname, "interface")

    if not os.path.isdir(dname):
        raise faults.ItemNotFound("VM has no attached NICs")

    fnames = [os.path.join(dname, rrdfile) for rrdfile in os.listdir(dname)]

    if not fnames:
        raise faults.ItemNotFound("VM has no attached NICs")

    args = ["DEF:rx%d=%s:rx:AVERAGE" % t for t in enumerate(fnames)]
    args += ["DEF:tx%d=%s:tx:AVERAGE" % t for t in enumerate(fnames)]

    rxsum = ""
    txsum = ""
    if len(fnames) > 1:
        rxsum = ",%s,+" % ',+,'.join(["rx%d" % i for i in range(1,
                                                                len(fnames))])
        txsum = ",%s,+" % ',+,'.join(["tx%d" % i for i in range(1,
                                                                len(fnames))])

    args += ["CDEF:rxbits=rx0%s,8,*" % rxsum]
    args += ["CDEF:txbits=tx0%s,8,*" % txsum]

    args += ["LINE1:rxbits#00ff00:Incoming",
             "GPRINT:rxbits:AVERAGE:\t%4.0lf%sbps\t\g",
             "LINE1:txbits#0000ff:Outgoing",
             "GPRINT:txbits:AVERAGE:\t%4.0lf%sbps\\n"]

    rrdtool.graph(outfname, "-s", "-1d", "-e", "-20s",
                  "--units", "si",
                  "-v", "Bits/s",
                  "COMMENT:\t\t\tAverage network traffic\\n",
                  *args)

    return read_file(outfname)


def draw_net_ts_w(fname, outfname):
    outfname += "-net-weekly.png"

    dname = os.path.join(fname, "interface")

    if not os.path.isdir(dname):
        raise faults.ItemNotFound("VM has no attached NICs")

    fnames = [os.path.join(dname, rrdfile) for rrdfile in os.listdir(dname)]

    if not fnames:
        raise faults.ItemNotFound("VM has no attached NICs")

    args = ["DEF:rx%d=%s:rx:AVERAGE" % t for t in enumerate(fnames)]
    args += ["DEF:tx%d=%s:tx:AVERAGE" % t for t in enumerate(fnames)]

    rxsum = ""
    txsum = ""
    if len(fnames) > 1:
        rxsum = ",%s,+" % ',+,'.join(["rx%d" % i for i in range(1,
                                                                len(fnames))])
        txsum = ",%s,+" % ',+,'.join(["tx%d" % i for i in range(1,
                                                                len(fnames))])

    args += ["CDEF:rxbits=rx0%s,8,*" % rxsum]
    args += ["CDEF:txbits=tx0%s,8,*" % txsum]

    args += ["LINE1:rxbits#00ff00:Incoming",
             "GPRINT:rxbits:AVERAGE:\t%4.0lf%sbps\t\g",
             "LINE1:txbits#0000ff:Outgoing",
             "GPRINT:txbits:AVERAGE:\t%4.0lf%sbps\\n"]

    rrdtool.graph(outfname, "-s", "-1w", "-e", "-20s",
                  "--units", "si",
                  "-v", "Bits/s",
                  "COMMENT:\t\t\tAverage network traffic\\n",
                  *args)

    return read_file(outfname)


def decrypt(secret):
    # Make sure key is 32 bytes long
    key = sha256(settings.STATS_SECRET_KEY).digest()

    aes = AES.new(key)
    return aes.decrypt(urlsafe_b64decode(secret)).rstrip('\x00')


available_graph_types = {'cpu-bar': draw_cpu_bar,
                         'net-bar': draw_net_bar,
                         'cpu-ts': draw_cpu_ts,
                         'net-ts': draw_net_ts,
                         'cpu-ts-w': draw_cpu_ts_w,
                         'net-ts-w': draw_net_ts_w
                         }


@api_method(http_method='GET', token_required=False, user_required=False,
            format_allowed=False, logger=log)
def grapher(request, graph_type, hostname):
    try:
        hostname = decrypt(smart_str(hostname))
    except (ValueError, TypeError):
        raise faults.BadRequest("Invalid encrypted virtual server name")
    fname = smart_str(os.path.join(settings.RRD_PREFIX, hostname))
    if not os.path.isdir(fname):
        raise faults.ItemNotFound('No such instance')

    outfname = smart_str(os.path.join(settings.GRAPH_PREFIX, hostname))
    draw_func = available_graph_types[graph_type]

    response = HttpResponse(draw_func(fname, outfname),
                            status=200, content_type="image/png")
    response.override_serialization = True

    return response
