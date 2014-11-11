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


def set_signal_trap():
    from os import getpid
    from traceback import format_stack, print_exc
    from signal import signal, SIGTRAP
    from sys import stderr
    import gc

    def greenlet_trace(arg):
        i = 0
        stderr.write("--- Greenlet trace: %s\n" % arg)
        for ob in gc.get_objects():
            if not isinstance(ob, greenlet):
                continue
            if not ob:
                continue
            i = i + 1
            stderr.write(("--- > Greenlet %d:\n" % i +
                          "".join(format_stack(ob.gr_frame)) + "\n\n"))
        stderr.write("--- End of trace: %s\n" % arg)

    try:
        from greenlet import greenlet
    except ImportError:

        def greenlet_trace(arg):
            return

    def handle_trap(*args):
        try:
            import trap_inject
            reload(trap_inject)
            trap_inject.inject()
        except ImportError:
            pass
        except:
            print_exc()

        msg = ('=== pid: %s' % getpid()) + '\n'.join(format_stack()) + '\n'
        stderr.write(msg)
        greenlet_trace('TRAP')

    signal(SIGTRAP, handle_trap)
