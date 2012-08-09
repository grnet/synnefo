#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2011 GRNET S.A. All rights reserved.
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
#
"""Utility to monitor the progress of image deployment

A small utility to monitor the progress of image deployment
by watching the contents of /proc/<pid>/io and producing
notifications of type 'ganeti-create-progress' to the rest
of the Synnefo infrastructure over AMQP.

"""

import os
import sys
import time
import json
import prctl
import signal
import socket

from synnefo import settings
from synnefo.lib.amqp import AMQPClient
from synnefo.lib.utils import split_time


def parse_arguments(args):
    from optparse import OptionParser

    kw = {}
    kw['usage'] = "%prog [options] command [args...]"
    kw['description'] = \
        "%prog runs 'command' with the specified arguments, monitoring the " \
        "number of bytes read and written by it. 'command' is assumed to be " \
        "A program used to install the OS for a Ganeti instance. %prog " \
        "periodically issues notifications of type 'ganeti-create-progress' " \
        "to the rest of the Synnefo infrastructure over AMQP."

    parser = OptionParser(**kw)
    parser.disable_interspersed_args()
    parser.add_option("-r", "--read-bytes",
                      action="store", type="int", dest="read_bytes",
                      metavar="BYTES_TO_READ",
                      help="The expected number of bytes to be read, " \
                           "used to compute input progress",
                      default=0)
    parser.add_option("-w", "--write-bytes",
                      action="store", type="int", dest="write_bytes",
                      metavar="BYTES_TO_WRITE",
                      help="The expected number of bytes to be written, " \
                           "used to compute output progress",
                      default=0)
    parser.add_option("-i", "--instance-name",
                      dest="instance_name",
                      metavar="GANETI_INSTANCE",
                      help="The Ganeti instance name to be used in AMQP " \
                           "notifications")

    (opts, args) = parser.parse_args(args)

    if opts.instance_name is None or (opts.read_bytes == 0 and
                                      opts.write_bytes == 0):
        sys.stderr.write("Fatal: Options '-i' and at least one of '-r' " \
                         "or '-w' are mandatory.\n")
        parser.print_help()
        sys.exit(1)

    if len(args) == 0:
        sys.stderr.write("Fatal: You need to specify the command to run.\n")
        parser.print_help()
        sys.exit(1)

    return (opts, args)


def report_wait_status(pid, status):
    if os.WIFEXITED(status):
        sys.stderr.write("Child PID = %d exited, status = %d\n" %
                         (pid, os.WEXITSTATUS(status)))
    elif os.WIFSIGNALED(status):
        sys.stderr.write("Child PID = %d died by signal, signal = %d\n" %
                         (pid, os.WTERMSIG(status)))
    elif os.WIFSTOPPED(status):
        sys.stderr.write("Child PID = %d stopped by signal, signal = %d\n" %
                         (pid, os.WSTOPSIG(status)))
    else:
        sys.stderr.write("Internal error: Unhandled case, " \
                         "PID = %d, status = %d\n" % (pid, status))
        sys.exit(1)
    sys.stderr.flush()


def main():
    (opts, args) = parse_arguments(sys.argv[1:])

    # WARNING: This assumes that instance names
    # are of the form prefix-id, and uses prefix to
    # determine the routekey for AMPQ
    prefix = opts.instance_name.split('-')[0]
    routekey = "ganeti.%s.event.progress" % prefix
    amqp_client = AMQPClient(hosts=settings.AMQP_HOSTS, confirm_buffer=2)
    amqp_client.connect()
    amqp_client.exchange_declare(settings.EXCHANGE_GANETI, type='topic')

    pid = os.fork()
    if pid == 0:
        # In child process:

        # Make sure we die with the parent and are not left behind
        # WARNING: This uses the prctl(2) call and is Linux-specific.
        prctl.set_pdeathsig(signal.SIGHUP)

        # exec command specified in arguments,
        # searching the $PATH, keeping all environment
        os.execvpe(args[0], args, os.environ)
        sys.stderr.write("execvpe failed, exiting with non-zero status")
        os.exit(1)

    # In parent process:
    iofname = "/proc/%d/io" % pid
    iof = open(iofname, "r", 0)   # 0: unbuffered open
    sys.stderr.write("%s: created child PID = %d, monitoring file %s\n" %
                     (sys.argv[0], pid, iofname))

    while True:
        # check if the child process is still alive
        (wpid, status) = os.waitpid(pid, os.WNOHANG)
        if wpid == pid:
            report_wait_status(pid, status)
            if (os.WIFEXITED(status) or os.WIFSIGNALED(status)):
                if not (os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0):
                    return 1
                else:
                    # send a final notification
                    final_msg = dict(type="ganeti-create-progress",
                                     instance=opts.instance_name)
                    final_msg['event_time'] = split_time(time.time())
                    if opts.read_bytes:
                        final_msg['rprogress'] = float(100)
                    if opts.write_bytes:
                        final_msg['wprogress'] = float(100)
                    amqp_client.basic_publish(exchange=settings.EXCHANGE_GANETI,
                                              routing_key=routekey,
                                              body=json.dumps(final_msg))
                    return 0

        # retrieve the current values of the read/write byte counters
        iof.seek(0)
        for l in iof.readlines():
            if l.startswith("rchar:"):
                rchar = int(l.split(': ')[1])
            if l.startswith("wchar:"):
                wchar = int(l.split(': ')[1])

        # Construct notification of type 'ganeti-create-progress'
        msg = dict(type="ganeti-create-progress",
                   instance=opts.instance_name)
        msg['event_time'] = split_time(time.time())
        if opts.read_bytes:
            msg['rprogress'] = float("%2.2f" %
                                     (rchar * 100.0 / opts.read_bytes))
        if opts.write_bytes:
            msg['wprogress'] = float("%2.2f" %
                                     (wchar * 100.0 / opts.write_bytes))

        # and send it over AMQP
        amqp_client.basic_publish(exchange=settings.EXCHANGE_GANETI,
                                  routing_key=routekey,
                                  body=json.dumps(msg))

        # Sleep for a while
        time.sleep(3)

    amqp_client.close()


if __name__ == "__main__":
    sys.exit(main())
