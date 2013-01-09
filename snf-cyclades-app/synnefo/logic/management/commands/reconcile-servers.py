# Copyright 2011-2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.
#
"""Reconciliation management command

Management command to reconcile the contents of the Synnefo DB with
the state of the Ganeti backend. See docstring on top of
logic/reconciliation.py for a description of reconciliation rules.

"""
import sys
import datetime
import subprocess

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from synnefo.db.models import VirtualMachine, Network, pooled_rapi_client
from synnefo.logic import reconciliation, utils
from synnefo.logic import backend as backend_mod
from synnefo.management.common import get_backend


class Command(BaseCommand):
    can_import_settings = True

    help = 'Reconcile contents of Synnefo DB with state of Ganeti backend'
    output_transaction = True  # The management command runs inside
                               # an SQL transaction
    option_list = BaseCommand.option_list + (
        make_option('--detect-stale', action='store_true', dest='detect_stale',
                    default=False, help='Detect stale VM entries in DB'),
        make_option('--detect-orphans', action='store_true',
                    dest='detect_orphans',
                    default=False, help='Detect orphan instances in Ganeti'),
        make_option('--detect-unsynced', action='store_true',
                    dest='detect_unsynced',
                    default=False, help='Detect unsynced operstate between ' +
                                        'DB and Ganeti'),
        make_option('--detect-build-errors', action='store_true',
                    dest='detect_build_errors', default=False,
                    help='Detect instances with build error'),
        make_option('--detect-unsynced-nics', action='store_true',
                    dest='detect_unsynced_nics', default=False,
                    help='Detect unsynced nics between DB and Ganeti'),
        make_option('--detect-all', action='store_true',
                    dest='detect_all',
                    default=False, help='Enable all --detect-* arguments'),
        make_option('--fix-stale', action='store_true', dest='fix_stale',
                    default=False, help='Fix (remove) stale DB entries in DB'),
        make_option('--fix-orphans', action='store_true', dest='fix_orphans',
                    default=False, help='Fix (remove) orphan Ganeti VMs'),
        make_option('--fix-unsynced', action='store_true', dest='fix_unsynced',
                    default=False, help='Fix server operstate in DB, set ' +
                                        'from Ganeti'),
        make_option('--fix-build-errors', action='store_true',
                    dest='fix_build_errors', default=False,
                    help='Fix (remove) instances with build errors'),
         make_option('--fix-unsynced-nics', action='store_true',
                    dest='fix_unsynced_nics', default=False,
                    help='Fix unsynced nics between DB and Ganeti'),
        make_option('--fix-all', action='store_true', dest='fix_all',
                    default=False, help='Enable all --fix-* arguments'),
        make_option('--backend-id', default=None, dest='backend-id',
                    help='Reconcilie VMs only for this backend'),
        )

    def _process_args(self, options):
        keys_detect = [k for k in options.keys() if k.startswith('detect_')]
        keys_fix = [k for k in options.keys() if k.startswith('fix_')]

        if not reduce(lambda x, y: x or y,
                      map(lambda x: options[x], keys_detect)):
            options['detect_all'] = True

        if options['detect_all']:
            for kd in keys_detect:
                options[kd] = True
        if options['fix_all']:
            for kf in keys_fix:
                options[kf] = True

        for kf in keys_fix:
            kd = kf.replace('fix_', 'detect_', 1)
            if (options[kf] and not options[kd]):
                raise CommandError("Cannot use --%s without corresponding "
                                   "--%s argument" % (kf, kd))

    def handle(self, **options):
        verbosity = int(options['verbosity'])
        self._process_args(options)
        backend_id = options['backend-id']
        backend = get_backend(backend_id) if backend_id else None

        D = reconciliation.get_servers_from_db(backend)
        G, GNics = reconciliation.get_instances_from_ganeti(backend)

        DBNics = reconciliation.get_nics_from_db(backend)

        #
        # Detect problems
        #
        if options['detect_stale']:
            stale = reconciliation.stale_servers_in_db(D, G)
            if len(stale) > 0:
                print >> sys.stderr, "Found the following stale server IDs: "
                print "    " + "\n    ".join(
                    [str(x) for x in stale])
            elif verbosity == 2:
                print >> sys.stderr, "Found no stale server IDs in DB."

        if options['detect_orphans']:
            orphans = reconciliation.orphan_instances_in_ganeti(D, G)
            if len(orphans) > 0:
                print >> sys.stderr, "Found orphan Ganeti instances with IDs: "
                print "    " + "\n    ".join(
                    [str(x) for x in orphans])
            elif verbosity == 2:
                print >> sys.stderr, "Found no orphan Ganeti instances."

        if options['detect_unsynced']:
            unsynced = reconciliation.unsynced_operstate(D, G)
            if len(unsynced) > 0:
                print >> sys.stderr, "The operstate of the following server" \
                                     " IDs is out-of-sync:"
                print "    " + "\n    ".join(
                    ["%d is %s in DB, %s in Ganeti" %
                     (x[0], x[1], ('UP' if x[2] else 'DOWN'))
                     for x in unsynced])
            elif verbosity == 2:
                print >> sys.stderr, "The operstate of all servers is in sync."

        if options['detect_build_errors']:
            build_errors = reconciliation.instances_with_build_errors(D, G)
            if len(build_errors) > 0:
                print >> sys.stderr, "The os for the following server IDs was "\
                                     "not build successfully:"
                print "    " + "\n    ".join(
                    ["%d" % x for x in build_errors])
            elif verbosity == 2:
                print >> sys.stderr, "Found no instances with build errors."

        if options['detect_unsynced_nics']:
            def pretty_print_nics(nics):
                if not nics:
                    print ''.ljust(18) + 'None'
                for index, info in nics.items():
                    print ''.ljust(18) + 'nic/' + str(index) + ': MAC: %s, IP: %s, Network: %s' % \
                      (info['mac'], info['ipv4'], info['network'])

            unsynced_nics = reconciliation.unsynced_nics(DBNics, GNics)
            if len(unsynced_nics) > 0:
                print >> sys.stderr, "The NICs of servers with the following IDs "\
                                     "are unsynced:"
                for id, nics in unsynced_nics.items():
                    print ''.ljust(2) + '%6d:' % id
                    print ''.ljust(8) + '%8s:' % 'DB'
                    pretty_print_nics(nics[0])
                    print ''.ljust(8) + '%8s:' % 'Ganeti'
                    pretty_print_nics(nics[1])
            elif verbosity == 2:
                print >> sys.stderr, "All instance nics are synced."

        #
        # Then fix them
        #
        if options['fix_stale'] and len(stale) > 0:
            print >> sys.stderr, \
                "Simulating successful Ganeti removal for %d " \
                "servers in the DB:" % len(stale)
            for vm in VirtualMachine.objects.filter(pk__in=stale):
                event_time = datetime.datetime.now()
                backend_mod.process_op_status(vm=vm, etime=event_time, jobid=-0,
                    opcode='OP_INSTANCE_REMOVE', status='success',
                    logmsg='Reconciliation: simulated Ganeti event')
            print >> sys.stderr, "    ...done"

        if options['fix_orphans'] and len(orphans) > 0:
            print >> sys.stderr, \
                "Issuing OP_INSTANCE_REMOVE for %d Ganeti instances:" % \
                len(orphans)
            for id in orphans:
                try:
                    vm = VirtualMachine.objects.get(pk=id)
                    with pooled_rapi_client(vm) as client:
                        client.DeleteInstance(utils.id_to_instance_name(id))
                except VirtualMachine.DoesNotExist:
                    print >> sys.stderr, "No entry for VM %d in DB !!" % id
            print >> sys.stderr, "    ...done"

        if options['fix_unsynced'] and len(unsynced) > 0:
            print >> sys.stderr, "Setting the state of %d out-of-sync VMs:" % \
                len(unsynced)
            for id, db_state, ganeti_up in unsynced:
                vm = VirtualMachine.objects.get(pk=id)
                opcode = "OP_INSTANCE_REBOOT" if ganeti_up \
                         else "OP_INSTANCE_SHUTDOWN"
                event_time = datetime.datetime.now()
                backend_mod.process_op_status(vm=vm, etime=event_time, jobid=-0,
                    opcode=opcode, status='success',
                    logmsg='Reconciliation: simulated Ganeti event')
            print >> sys.stderr, "    ...done"

        if options['fix_build_errors'] and len(build_errors) > 0:
            print >> sys.stderr, "Setting the state of %d build-errors VMs:" % \
                len(build_errors)
            for id in build_errors:
                vm = VirtualMachine.objects.get(pk=id)
                event_time = datetime.datetime.now()
                backend_mod.process_op_status(vm=vm, etime=event_time, jobid=-0,
                    opcode="OP_INSTANCE_CREATE", status='error',
                    logmsg='Reconciliation: simulated Ganeti event')
            print >> sys.stderr, "    ...done"

        if options['fix_unsynced_nics'] and len(unsynced_nics) > 0:
            print >> sys.stderr, "Setting the nics of %d out-of-sync VMs:" % \
                                  len(unsynced_nics)
            for id, nics in unsynced_nics.items():
                vm = VirtualMachine.objects.get(pk=id)
                nics = nics[1]  # Ganeti nics
                if nics == {}:  # No nics
                    vm.nics.all.delete()
                    continue
                for index, nic in nics.items():
                    net_id = utils.id_from_network_name(nic['network'])
                    subnet6 = Network.objects.get(id=net_id).subnet6
                    # Produce ipv6
                    ipv6 = subnet6 and mac2eui64(nic['mac'], subnet6) or None
                    nic['ipv6'] = ipv6
                    # Rename ipv4 to ip
                    nic['ip'] = nic['ipv4']
                # Dict to sorted list
                final_nics = []
                nics_keys = nics.keys()
                nics_keys.sort()
                for i in nics_keys:
                    if nics[i]['network']:
                        final_nics.append(nics[i])
                    else:
                        print 'Network of nic %d of vm %s is None. ' \
                              'Can not reconcile' % (i, vm.backend_vm_id)
                event_time = datetime.datetime.now()
                backend_mod.process_net_status(vm=vm, etime=event_time, nics=final_nics)
            print >> sys.stderr, "    ...done"


def mac2eui64(mac, prefixstr):
    process = subprocess.Popen(["mac2eui64", mac, prefixstr],
                                stdout=subprocess.PIPE)
    return process.stdout.read().rstrip()
