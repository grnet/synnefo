#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
#

"""Ganeti notification daemon with AMQP support

A daemon to monitor the Ganeti job queue and publish job progress
and Ganeti VM state notifications to the ganeti exchange
"""

OLD_GANETI_PATH = "/usr/share/ganeti"
NEW_GANETI_PATH = "/etc/ganeti/share"

import sys
import os
path = os.path.normpath(os.path.join(os.getcwd(), '..'))
sys.path.append(path)
# Since Ganeti 2.7, debian package ships the majority of the python code in
# a private module under '/usr/share/ganeti'. Add this directory to path
# in order to be able to import ganeti. Also, add it to the start of path
# to allow conflicts with Ganeti RAPI client.
# Since Ganeti 2.10 the python module is installed (linked) under
# /etc/ganeti/share
# Favor latest ganeti if found
if os.path.exists(NEW_GANETI_PATH):
    GANETI_PATH = NEW_GANETI_PATH
else:
    GANETI_PATH = OLD_GANETI_PATH

sys.path.insert(0, GANETI_PATH)

try:
    import ganeti  # NOQA
except ImportError:
    raise Exception("Cannot import ganeti module. Please check if installed"
                    " under %s for 2.8 or under %s for 2.10 or later." %
                    (OLD_GANETI_PATH, NEW_GANETI_PATH))

import json
import logging
import pyinotify
import daemon
import daemon.pidlockfile
import daemon.runner
from lockfile import LockTimeout
from signal import signal, SIGINT, SIGTERM
import setproctitle

from ganeti import utils, jqueue, constants, serializer, pathutils, cli
from ganeti import errors as ganeti_errors
from ganeti.ssconf import SimpleStore


from synnefo import settings
from synnefo.lib.amqp import AMQPClient


def get_time_from_status(op, job):
    """Generate a unique message identifier for a ganeti job.

    The identifier is based on the timestamp of the job. Since a ganeti
    job passes from multiple states, we need to pick the timestamp that
    corresponds to each state.

    """
    status = op.status
    if status == constants.JOB_STATUS_QUEUED:
        time = job.received_timestamp
    try:  # Compatibility with Ganeti version
        if status == constants.JOB_STATUS_WAITLOCK:
            time = op.start_timestamp
    except AttributeError:
        if status == constants.JOB_STATUS_WAITING:
            time = op.start_timestamp
    if status == constants.JOB_STATUS_CANCELING:
        time = op.start_timestamp
    if status == constants.JOB_STATUS_RUNNING:
        time = op.exec_timestamp
    if status in constants.JOBS_FINALIZED:
        time = op.end_timestamp

    return time and time or job.end_timestamp

    raise InvalidBackendStatus(status, job)


def get_instance_attachments(instance, logger):
    """Query Ganeti to a get the instance's attachments (NICs and Disks)

    Get instance's attachments from Ganeti configuration data. If running on
    master, query Ganeti via Ganeti CLI client. Otherwise, get attachments
    straight from Ganeti's configuration file.

    @type instance: string
    @param instance: the name of the instance
    @rtype: instance's NICs and Disks
    @return: Dictionary containing the 'nics' and 'disks' of the instance.

    """
    try:
        client = cli.GetClient()
        q_fields = ["nic.names", "nic.networks.names", "nic.ips", "nic.macs",
                    "nic.modes", "nic.links", "nic.uuids", "tags",
                    "disk.names", "disk.sizes", "disk.uuids"]
        info = client.QueryInstances([instance], q_fields, use_locking=False)
        # Parse NICs
        names, networks, ips, macs, modes, links, uuids, tags = info[0][:-3]
        nic_keys = ["name", "network", "ip", "mac", "mode", "link", "uuid"]
        nics = zip(names, networks, ips, macs, modes, links, uuids)
        nics = map(lambda x: dict(zip(nic_keys, x)), nics)
        # Parse Disks
        names, sizes, uuids = info[0][-3:]
        disk_keys = ["name", "size", "uuid"]
        disks = zip(names, sizes, uuids)
        disks = map(lambda x: dict(zip(disk_keys, x)), disks)
    except ganeti_errors.OpPrereqError:
        # Not running on master! Load the conf file
        raw_data = utils.ReadFile(pathutils.CLUSTER_CONF_FILE)
        config = serializer.LoadJson(raw_data)
        i = config["instances"][instance]
        # Parse NICs
        nics = []
        for index, nic in enumerate(i["nics"]):
            params = nic.pop("nicparams")
            nic["mode"] = params["mode"]
            nic["link"] = params["link"]
            nic["index"] = index
            nics.append(nic)
        # Parse Disks
        disks = []
        for index, disk in enumerate(i["disks"]):
            disks.append({"name": disk.pop("name"),
                          "size": disk["size"],
                          "uuid": disk["uuid"],
                          "index": index})
        tags = i.get("tags", [])
    # Get firewall from instance Tags
    # Tags are of the form synnefo:network:N:firewall_mode
    for tag in tags:
        t = tag.split(":")
        if t[0:2] == ["synnefo", "network"]:
            if len(t) != 4:
                logger.error("Malformed synefo tag %s", tag)
                continue
            nic_name = t[2]
            firewall = t[3]
            [nic.setdefault("firewall", firewall)
             for nic in nics if nic["name"] == nic_name]
    attachments = {"nics": nics,
                   "disks": disks}
    return attachments


class InvalidBackendStatus(Exception):
    def __init__(self, status, job):
        self.status = status
        self.job = job

    def __str__(self):
        return repr("Invalid backend status: %s in job %s"
                    % (self.status, self.job))


def prefix_from_name(name):
    return name.split('-')[0]


def get_field(from_, field):
    try:
        return getattr(from_, field)
    except AttributeError:
        None


class JobFileHandler(pyinotify.ProcessEvent):
    def __init__(self, logger, cluster_name):
        pyinotify.ProcessEvent.__init__(self)
        self.logger = logger
        self.cluster_name = cluster_name

        # Set max_retries to 0 for unlimited retries.
        self.client = AMQPClient(hosts=settings.AMQP_HOSTS, confirm_buffer=25,
                                 max_retries=0, logger=logger)

        handler_logger.info("Attempting to connect to RabbitMQ hosts")

        self.client.connect()
        handler_logger.info("Connected succesfully")

        self.client.exchange_declare(settings.EXCHANGE_GANETI, type='topic')

        self.op_handlers = {"INSTANCE": self.process_instance_op,
                            "NETWORK": self.process_network_op,
                            "CLUSTER": self.process_cluster_op,
                            # "GROUP": self.process_group_op}
                            "TAGS": self.process_tag_op}

    def process_IN_CLOSE_WRITE(self, event):
        self.process_IN_MOVED_TO(event)

    def process_IN_MOVED_TO(self, event):
        jobfile = os.path.join(event.path, event.name)
        if not event.name.startswith("job-"):
            self.logger.debug("Not a job file: %s" % event.path)
            return

        try:
            data = utils.ReadFile(jobfile)
        except IOError:
            return

        data = serializer.LoadJson(data)
        job = jqueue._QueuedJob.Restore(None, data, False, False)

        job_id = int(job.id)

        for op in job.ops:
            op_id = op.input.OP_ID

            msg = None
            try:
                handler_fn = self.op_handlers[op_id.split('_')[1]]
                msg, routekey = handler_fn(op, job_id)
            except KeyError:
                pass

            if not msg:
                self.logger.debug("Ignoring job: %s: %s", job_id, op_id)
                continue

            # Generate a unique message identifier
            event_time = get_time_from_status(op, job)

            # Get the last line of the op log as message
            try:
                logmsg = op.log[-1][-1]
            except IndexError:
                logmsg = None

            # Add shared attributes for all operations
            msg.update({"event_time": event_time,
                        "operation": op_id,
                        "status": op.status,
                        "cluster": self.cluster_name,
                        "logmsg": logmsg,
                        "result": op.result,
                        "jobId": job_id})

            if op.status == "success":
                msg["result"] = op.result

            if op_id == "OP_INSTANCE_CREATE" and op.status == "error":
                # In case an instance creation fails send the job input
                # so that the job can be retried if needed.
                msg["job_fields"] = op.Serialize()["input"]

            msg = json.dumps(msg)

            self.logger.debug("Delivering msg: %s (key=%s)", msg, routekey)

            # Send the message to RabbitMQ
            self.client.basic_publish(settings.EXCHANGE_GANETI,
                                      routekey,
                                      msg)

    def process_instance_op(self, op, job_id):
        """ Process OP_INSTANCE_* opcodes.

        """
        input = op.input
        op_id = input.OP_ID

        instances = None
        instances = get_field(input, 'instance_name')
        if not instances:
            instances = get_field(input, 'instances')
            if not instances or len(instances) > 1:
                # Do not publish messages for jobs with no or multiple
                # instances.  Currently snf-dispatcher can not normally handle
                # these messages
                return None, None
            else:
                instances = instances[0]

        self.logger.debug("Job: %d: %s(%s) %s", job_id, op_id,
                          instances, op.status)

        job_fields = {}
        if op_id in ["OP_INSTANCE_SET_PARAMS", "OP_INSTANCE_CREATE"]:
            job_fields = {"nics": get_field(input, "nics"),
                          "disks": get_field(input, "disks"),
                          "beparams": get_field(input, "beparams")}
        elif op_id == "OP_INSTANCE_SNAPSHOT":
            # Cyclades store the UUID of the snapshot as the 'reason' attribute
            # of the Ganeti job in order to be able to update the status of
            # the snapshot based on the result of the Ganeti job. Parse this
            # attribute and include it in the msg.
            # NOTE: This will fill the 'snapshot_info' attribute only for the
            # first disk, but this is ok because Cyclades do not issue jobs to
            # create snapshots of many disks.
            disks = get_field(input, "disks")
            if disks:
                reason = get_field(input, "reason")
                snapshot_info = None
                try:
                    reason = reason[0]
                    assert (reason[0] == "gnt:user")
                    snapshot_info = reason[1]
                    disks[0][1]["snapshot_info"] = snapshot_info
                except:
                    self.logger.warning("Malformed snapshot job '%s'", job_id)
                job_fields = {"disks": disks}

        msg = {"type": "ganeti-op-status",
               "instance": instances,
               "operation": op_id,
               "job_fields": job_fields}

        if ((op_id in ["OP_INSTANCE_CREATE", "OP_INSTANCE_STARTUP"] and
             op.status == "success") or
            (op_id in ["OP_INSTANCE_SET_PARAMS", "OP_INSTANCE_GROW_DISK"] and
             op.status in ["success", "error", "cancelled"])):
                attachments = get_instance_attachments(msg["instance"],
                                                       self.logger)
                msg["instance_nics"] = attachments["nics"]
                msg["instance_disks"] = attachments["disks"]

        routekey = "ganeti.%s.event.op" % prefix_from_name(instances)

        return msg, routekey

    def process_network_op(self, op, job_id):
        """ Process OP_NETWORK_* opcodes.

        """

        input = op.input
        op_id = input.OP_ID
        network_name = get_field(input, 'network_name')

        if not network_name:
            return None, None

        self.logger.debug("Job: %d: %s(%s) %s", job_id, op_id,
                          network_name, op.status)

        job_fields = {
            'subnet': get_field(input, 'network'),
            'gateway': get_field(input, 'gateway'),
            "add_reserved_ips": get_field(input, "add_reserved_ips"),
            "remove_reserved_ips": get_field(input, "remove_reserved_ips"),
            # 'network_mode': get_field(input, 'network_mode'),
            # 'network_link': get_field(input, 'network_link'),
            'group_name': get_field(input, 'group_name')}

        msg = {'operation':    op_id,
               'type':         "ganeti-network-status",
               'network':      network_name,
               'job_fields':   job_fields}

        routekey = "ganeti.%s.event.network" % prefix_from_name(network_name)

        return msg, routekey

    def process_cluster_op(self, op, job_id):
        """ Process OP_CLUSTER_* opcodes.

        """

        input = op.input
        op_id = input.OP_ID

        self.logger.debug("Job: %d: %s %s", job_id, op_id, op.status)

        if op_id != "OP_CLUSTER_SET_PARAMS":
            # Send only modifications of cluster
            return None, None

        msg = {'operation':    op_id,
               'type':         "ganeti-cluster-status"}

        routekey = "ganeti.event.cluster"

        return msg, routekey

    def process_tag_op(self, op, job_id):
        """ Process OP_TAGS_* opcodes.

        """
        input = op.input
        op_id = input.OP_ID
        if op_id == "OP_TAGS_SET":
            # NOTE: Check 'dry_run' after 'cluster' because networks and groups
            # do not support the 'dry_run' option.
            if (op.status == "waiting" and input.tags and
               input.kind == "cluster" and input.dry_run):
                # Special where a prefixed cluster tag operation in dry-run
                # mode is used in order to trigger eventd to send a
                # heartbeat message.
                tag = input.tags[0]
                if tag.startswith("snf:eventd:heartbeat"):
                    self.logger.debug("Received heartbeat tag '%s'."
                                      " Sending response.", tag)
                    msg = {"type": "eventd-heartbeat",
                           "cluster": self.cluster_name}
                    return msg, "eventd.heartbeat"

        return None, None


def find_cluster_name():
    global handler_logger
    try:
        ss = SimpleStore()
        name = ss.GetClusterName()
    except Exception as e:
        handler_logger.error('Can not get the name of the Cluster: %s' % e)
        raise e

    return name


handler_logger = None


def fatal_signal_handler(signum, frame):
    global handler_logger

    handler_logger.info("Caught fatal signal %d, will raise SystemExit",
                        signum)
    raise SystemExit


def parse_arguments(args):
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-d", "--debug", action="store_true", dest="debug",
                      help="Enable debugging information")
    parser.add_option("-l", "--log", dest="log_file",
                      default="/var/log/snf-ganeti-eventd.log",
                      metavar="FILE",
                      help="Write log to FILE instead of %s" %
                           "/var/log/snf-ganeti-eventd.log")
    parser.add_option('--pid-file', dest="pid_file",
                      default="/var/run/snf-ganeti-eventd.pid",
                      metavar='PIDFILE',
                      help="Save PID to file (default: %s)" %
                           "/var/run/snf-ganeti-eventd.pid")

    return parser.parse_args(args)


def main():
    global handler_logger

    (opts, args) = parse_arguments(sys.argv[1:])

    # Initialize logger
    lvl = logging.DEBUG if opts.debug else logging.INFO
    logger = logging.getLogger("ganeti.eventd")
    logger.setLevel(lvl)
    formatter = logging.Formatter(
        "%(asctime)s %(module)s[%(process)d] %(levelname)s: %(message)s",
        "%Y-%m-%d %H:%M:%S")
    handler = logging.FileHandler(opts.log_file)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    handler_logger = logger

    # Rename this process so 'ps' output looks like this is a native
    # executable.  Can not seperate command-line arguments from actual name of
    # the executable by NUL bytes, so only show the name of the executable
    # instead.  setproctitle.setproctitle("\x00".join(sys.argv))
    setproctitle.setproctitle(sys.argv[0])

    # Create pidfile
    pidf = daemon.pidlockfile.TimeoutPIDLockFile(opts.pid_file, 10)

    # Remove any stale PID files, left behind by previous invocations
    if daemon.runner.is_pidfile_stale(pidf):
        logger.warning("Removing stale PID lock file %s", pidf.path)
        pidf.break_lock()

    # Become a daemon:
    # Redirect stdout and stderr to handler.stream to catch
    # early errors in the daemonization process [e.g., pidfile creation]
    # which will otherwise go to /dev/null.
    daemon_context = daemon.DaemonContext(
        pidfile=pidf,
        umask=022,
        stdout=handler.stream,
        stderr=handler.stream,
        files_preserve=[handler.stream])
    try:
        daemon_context.open()
    except (daemon.pidlockfile.AlreadyLocked, LockTimeout):
        logger.critical("Failed to lock pidfile %s, another instance running?",
                        pidf.path)
        sys.exit(1)

    logger.info("Became a daemon")

    # Catch signals to ensure graceful shutdown
    signal(SIGINT, fatal_signal_handler)
    signal(SIGTERM, fatal_signal_handler)

    # Monitor the Ganeti job queue, create and push notifications
    wm = pyinotify.WatchManager()
    mask = (pyinotify.EventsCodes.ALL_FLAGS["IN_MOVED_TO"] |
            pyinotify.EventsCodes.ALL_FLAGS["IN_CLOSE_WRITE"])

    cluster_name = find_cluster_name()

    handler = JobFileHandler(logger, cluster_name)
    notifier = pyinotify.Notifier(wm, handler)

    try:
        # Fail if adding the inotify() watch fails for any reason
        res = wm.add_watch(pathutils.QUEUE_DIR, mask)
        if res[pathutils.QUEUE_DIR] < 0:
            raise Exception("pyinotify add_watch returned negative descriptor")

        logger.info("Now watching %s of %s" % (pathutils.QUEUE_DIR,
                    cluster_name))

        while True:    # loop forever
            # process the queue of events as explained above
            try:
                notifier.process_events()
            except StandardError:
                logger.exception("Unhandled exception")
            if notifier.check_events():
                # read notified events and enqeue them
                notifier.read_events()
    except SystemExit:
        logger.info("SystemExit")
    except:
        logger.exception("Caught exception, terminating")
    finally:
        # destroy the inotify's instance on this interrupt (stop monitoring)
        notifier.stop()
        raise

if __name__ == "__main__":
    sys.exit(main())

# vim: set sta sts=4 shiftwidth=4 sw=4 et ai :
