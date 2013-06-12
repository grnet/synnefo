# Copyright 2011-2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

from django.http import HttpResponse

import gd
import os
import sys
import subprocess

from cgi import escape
from cStringIO import StringIO

import rrdtool

from synnefo_stats import settings

from synnefo.util.text import uenc
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
    except rrdtool.error, e:
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
    fname = os.path.join(fname, "interface", "if_octets-eth0.rrd")

    try:
        values = rrdtool.fetch(fname, "AVERAGE")[2][-20:]
    except rrdtool.error, e:
        values = [(0.0, 0.0)]

    v = [x for x in values if x[0] is not None and x[1] is not None]
    if not v:
        # Fallback in case we only get NaNs
        v = [(0.0, 0.0)]

    rx_value, tx_value = v[-1]

    # Convert to bits
    rx_value = rx_value * 8 / 10 ** 6
    tx_value = tx_value * 8 / 10 ** 6

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
                  #"-t", "CPU usage",
                  "-v", "%",
                  #"--lazy",
                  "DEF:cpu=%s:ns:AVERAGE" % fname,
                  "LINE1:cpu#00ff00:")

    return read_file(outfname)


def draw_cpu_ts_w(fname, outfname):
    fname = os.path.join(fname, "cpu", "virt_cpu_total.rrd")
    outfname += "-cpu-weekly.png"

    rrdtool.graph(outfname, "-s", "-1w", "-e", "-20s",
                  #"-t", "CPU usage",
                  "-v", "%",
                  #"--lazy",
                  "DEF:cpu=%s:ns:AVERAGE" % fname,
                  "LINE1:cpu#00ff00:")

    return read_file(outfname)


def draw_net_ts(fname, outfname):
    fname = os.path.join(fname, "interface", "if_octets-eth0.rrd")
    outfname += "-net.png"

    rrdtool.graph(outfname, "-s", "-1d", "-e", "-20s",
              #"-t", "Network traffic",
              "--units", "si",
              "-v", "Bits/s",
              #"--lazy",
              "COMMENT:\t\t\tAverage network traffic\\n",
              "DEF:rx=%s:rx:AVERAGE" % fname,
              "DEF:tx=%s:tx:AVERAGE" % fname,
              "CDEF:rxbits=rx,8,*",
              "CDEF:txbits=tx,8,*",
              "LINE1:rxbits#00ff00:Incoming",
              "GPRINT:rxbits:AVERAGE:\t%4.0lf%sbps\t\g",
              "LINE1:txbits#0000ff:Outgoing",
              "GPRINT:txbits:AVERAGE:\t%4.0lf%sbps\\n")

    return read_file(outfname)


def draw_net_ts_w(fname, outfname):
    fname = os.path.join(fname, "interface", "if_octets-eth0.rrd")
    outfname += "-net-weekly.png"

    rrdtool.graph(outfname, "-s", "-1w", "-e", "-20s",
              #"-t", "Network traffic",
              "--units", "si",
              "-v", "Bits/s",
              #"--lazy",
              "COMMENT:\t\t\tAverage network traffic\\n",
              "DEF:rx=%s:rx:AVERAGE" % fname,
              "DEF:tx=%s:tx:AVERAGE" % fname,
              "CDEF:rxbits=rx,8,*",
              "CDEF:txbits=tx,8,*",
              "LINE1:rxbits#00ff00:Incoming",
              "GPRINT:rxbits:AVERAGE:\t%4.0lf%sbps\t\g",
              "LINE1:txbits#0000ff:Outgoing",
              "GPRINT:txbits:AVERAGE:\t%4.0lf%sbps\\n")

    return read_file(outfname)


available_graph_types = {
        'cpu-bar': draw_cpu_bar,
        'net-bar': draw_net_bar,
        'cpu-ts': draw_cpu_ts,
        'net-ts': draw_net_ts,
        'cpu-ts-w': draw_cpu_ts_w,
        'net-ts-w': draw_net_ts_w,
        }


@api_method(http_method='GET', token_required=False, user_required=False,
            format_allowed=False, logger=log)
def grapher(request, graph_type, hostname):
    fname = uenc(os.path.join(settings.RRD_PREFIX, hostname))
    if not os.path.isdir(fname):
        raise faults.ItemNotFound('No such instance')

    outfname = uenc(os.path.join(settings.GRAPH_PREFIX, hostname))
    draw_func = available_graph_types[graph_type]

    response = HttpResponse(draw_func(fname, outfname),
                            status=200, content_type="image/png")
    response.override_serialization = True

    return response
