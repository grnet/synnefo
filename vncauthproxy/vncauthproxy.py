#!/usr/bin/env python
#

# Copyright (c) 2010 GRNET SA
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.


import os
import sys
import logging
import gevent

import rfb

from gevent import socket
from gevent.select import select

class VncAuthProxy(gevent.Greenlet):
    """
    Simple class implementing a VNC Forwarder with MITM authentication as a
    Greenlet

    VncAuthProxy forwards VNC traffic from a specified port of the local host
    to a specified remote host:port. Furthermore, it implements VNC
    Authentication, intercepting the client/server handshake and asking the
    client for authentication even if the backend requires none.

    It is primarily intended for use in virtualization environments, as a VNC
    ``switch''.

    """
    id = 1

    def __init__(self, sport, daddr, dport, password, connect_timeout=30):
        """
        @type sport: int
        @param sport: source port
        @type daddr: str
        @param daddr: destination address (IPv4, IPv6 or hostname)
        @type dport: int
        @param dport: destination port
        @type password: str
        @param password: password to request from the client
        @type connect_timeout: int
        @param connect_timeout: how long to wait for client connections
                                (seconds)

        """
        gevent.Greenlet.__init__(self)
        self.id = VncAuthProxy.id
        VncAuthProxy.id += 1
        self.sport = sport
        self.daddr = daddr
        self.dport = dport
        self.password = password
        self.log = logging
        self.server = None
        self.client = None
        self.timeout = connect_timeout

    def _cleanup(self):
        """Close all active sockets and exit gracefully"""
        if self.server:
            self.server.close()
        if self.client:
            self.client.close()
        raise gevent.GreenletExit

    def info(self, msg):
        logging.info("[C%d] %s" % (self.id, msg))

    def debug(self, msg):
        logging.debug("[C%d] %s" % (self.id, msg))

    def warn(self, msg):
        logging.warn("[C%d] %s" % (self.id, msg))

    def error(self, msg):
        logging.error("[C%d] %s" % (self.id, msg))

    def critical(self, msg):
        logging.critical("[C%d] %s" % (self.id, msg))

    def __str__(self):
        return "VncAuthProxy: %d -> %s:%d" % (self.sport, self.daddr, self.dport)

    def _forward(self, source, dest):
        """
        Forward traffic from source to dest

        @type source: socket
        @param source: source socket
        @type dest: socket
        @param dest: destination socket

        """

        while True:
            d = source.recv(8096)
            if d == '':
                if source == self.client:
                    self.info("Client connection closed")
                else:
                    self.info("Server connection closed")
                break
            dest.sendall(d)
        source.close()
        dest.close()


    def _handshake(self):
        """
        Perform handshake/authentication with a connecting client

        Outline:
        1. Client connects
        2. We fake RFB 3.8 protocol and require VNC authentication
        3. Client accepts authentication method
        4. We send an authentication challenge
        5. Client sends the authentication response
        6. We check the authentication
        7. We initiate a connection with the backend server and perform basic
           RFB 3.8 handshake with it.
        8. If the above is successful, "bridge" both connections through two
           "fowrarder" greenlets.

        """
        self.client.send(rfb.RFB_VERSION_3_8 + "\n")
        client_version = self.client.recv(1024)
        if not rfb.check_version(client_version):
            self.error("Invalid version: %s" % client_version)
            self._cleanup()
        self.debug("Requesting authentication")
        auth_request = rfb.make_auth_request(rfb.RFB_AUTHTYPE_VNC)
        self.client.send(auth_request)
        res = self.client.recv(1024)
        type = rfb.parse_client_authtype(res)
        if type == rfb.RFB_AUTHTYPE_ERROR:
            self.warn("Client refused authentication: %s" % res[1:])
        else:
            self.debug("Client requested authtype %x" % type)

        if type != rfb.RFB_AUTHTYPE_VNC:
            self.error("Wrong auth type: %d" % type)
            self.client.send(rfb.to_u32(rfb.RFB_AUTH_ERROR))
            self._cleanup()

        # Generate the challenge
        challenge = os.urandom(16)
        self.client.send(challenge)
        response = self.client.recv(1024)
        if len(response) != 16:
            self.error("Wrong response length %d, should be 16" % len(response))
            self._cleanup()

        if rfb.check_password(challenge, response, password):
            self.debug("Authentication successful!")
        else:
            self.warn("Authentication failed")
            self.client.send(rfb.to_u32(rfb.RFB_AUTH_ERROR))
            self._cleanup()

        # Accept the authentication
        self.client.send(rfb.to_u32(rfb.RFB_AUTH_SUCCESS))

        # Try to connect to the server
        tries = 50

        while tries:
            tries -= 1

            # Initiate server connection
            for res in socket.getaddrinfo(self.daddr, self.dport, socket.AF_UNSPEC,
                                          socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
                af, socktype, proto, canonname, sa = res
                try:
                    self.server = socket.socket(af, socktype, proto)
                except socket.error, msg:
                    self.server = None
                    continue

                try:
                    self.debug("Connecting to %s:%s" % sa[:2])
                    self.server.connect(sa)
                    self.debug("Connection to %s:%s successful" % sa[:2])
                except socket.error, msg:
                    self.server.close()
                    self.server = None
                    continue

                # We succesfully connected to the server
                tries = 0
                break

            # Wait and retry
            gevent.sleep(0.2)

        if self.server is None:
            self.error("Failed to connect to server")
            self._cleanup()

        version = self.server.recv(1024)
        if not rfb.check_version(version):
            self.error("Unsupported RFB version: %s" % version.strip())
            self._cleanup()

        self.server.send(rfb.RFB_VERSION_3_8 + "\n")

        res = self.server.recv(1024)
        types = rfb.parse_auth_request(res)
        if not types:
            self.error("Error handshaking with the server")
            self._cleanup()

        else:
            self.debug("Supported authentication types: %s" %
                           " ".join([str(x) for x in types]))

        if rfb.RFB_AUTHTYPE_NONE not in types:
            self.error("Error, server demands authentication")
            self._cleanup()

        self.server.send(rfb.to_u8(rfb.RFB_AUTHTYPE_NONE))

        # Check authentication response
        res = self.server.recv(4)
        res = rfb.from_u32(res)

        if res != 0:
            self.error("Authentication error")
            self._cleanup()

        # Bridge client/server connections
        self.workers = [gevent.spawn(self._forward, self.client, self.server),
                        gevent.spawn(self._forward, self.server, self.client)]
        gevent.joinall(self.workers)

        del self.workers
        self._cleanup()

    def _run(self):
        sockets = []

        # Use two sockets, one for IPv4, one for IPv6. IPv4-to-IPv6 mapped
        # addresses do not work reliably everywhere (under linux it may have
        # been disabled in /proc/sys/net/ipv6/bind_ipv6_only).
        for res in socket.getaddrinfo(None, self.sport, socket.AF_UNSPEC,
                                      socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
            af, socktype, proto, canonname, sa = res
            try:
                s = socket.socket(af, socktype, proto)
                if af == socket.AF_INET6:
                    # Bind v6 only when AF_INET6, otherwise either v4 or v6 bind
                    # will fail.
                    s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            except socket.error, msg:
                s = None
                continue;

            try:
                s.bind(sa)
                s.listen(1)
                self.debug("Listening on %s:%d" % sa[:2])
            except socket.error, msg:
                self.error("Error binding to %s:%d: %s" %
                               (sa[0], sa[1], msg[1]))
                s.close()
                s = None
                continue

            if s:
                sockets.append(s)

        if not sockets:
            self.error("Failed to listen for connections")
            self._cleanup()

        self.log.debug("Waiting for client to connect")
        rlist, _, _ = select(sockets, [], [], timeout=self.timeout)

        if not rlist:
            self.info("Timed out, no connection after %d sec" % self.timeout)
            self._cleanup()

        for sock in rlist:
            self.client, addrinfo = sock.accept()
            self.info("Connection from %s:%d" % addrinfo[:2])

            # Close all listening sockets, we only want a one-shot connection
            # from a single client.
            for listener in sockets:
                listener.close()
            break

        self._handshake()


if __name__ == '__main__':
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-s", "--socket", dest="ctrl_socket",
                      help="UNIX socket path for control connections",
                      default="/tmp/vncproxy.sock",
                      metavar="PATH")
    parser.add_option("-d", "--debug", action="store_true", dest="debug",
                      help="Enable debugging information")
    parser.add_option("-l", "--log", dest="logfile", default=None,
                      help="Write log to FILE instead of stdout",
                      metavar="FILE")
    parser.add_option("-t", "--connect-timeout", dest="connect_timeout",
                      default=30, type="int", metavar="SECONDS",
                      help="How long to listen for clients to forward")

    (opts, args) = parser.parse_args(sys.argv[1:])

    lvl = logging.DEBUG if opts.debug else logging.INFO

    logging.basicConfig(level=lvl, filename=opts.logfile,
                        format="%(asctime)s %(levelname)s: %(message)s",
                        datefmt="%m/%d/%Y %H:%M:%S")

    if os.path.exists(opts.ctrl_socket):
        logging.critical("Socket '%s' already exists" % opts.ctrl_socket)
        sys.exit(1)

    # TODO: make this tunable? chgrp as well?
    old_umask = os.umask(0077)

    ctrl = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    ctrl.bind(opts.ctrl_socket)

    os.umask(old_umask)

    ctrl.listen(1)
    logging.info("Initalized, waiting for control connections at %s" %
                 opts.ctrl_socket)

    while True:
        try:
            client, addr = ctrl.accept()
        except KeyboardInterrupt:
            break

        logging.info("New control connection")
        line = client.recv(1024).strip()
        try:
            # Control message format:
            # TODO: make this json-based?
            # TODO: support multiple forwardings in the same message?
            # <source_port>:<destination_address>:<destination_port>:<password>
            # <password> will be used for MITM authentication of clients
            # connecting to <source_port>, who will subsequently be forwarded
            # to a VNC server at <destination_address>:<destination_port>
            sport, daddr, dport, password = line.split(':', 3)
            logging.info("New forwarding [%d -> %s:%d]" %
                         (int(sport), daddr, int(dport)))
        except:
            logging.warn("Malformed request: %s" % line)
            client.send("FAILED\n")
            client.close()
            continue

        client.send("OK\n")
        VncAuthProxy.spawn(sport, daddr, dport, password, opts.connect_timeout)
        client.close()

    os.unlink(opts.ctrl_socket)
    sys.exit(0)
