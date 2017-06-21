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

"""Cyclades-specific support for transactions in multiple databases.
"""

import logging
from functools import wraps

from snf_django.utils.transaction import atomic as snf_atomic
from synnefo import quotas

log = logging.getLogger(__name__)


def atomic(using=None, savepoint=True):
    return snf_atomic("db", using, savepoint)


class SerialContext(object):
    def __init__(self, *args, **kwargs):
        self._serial = None

    def set_serial(self, serial):
        if self._serial is not None:
            raise ValueError("Cannot set multiple serials")
        self._serial = serial

    def handle(self, success):
        serial = self._serial
        if success:
            if not serial.pending:
                if serial.accept:
                    quotas.accept_serial(serial)
                else:
                    quotas.reject_serial(serial)
        else:
            if serial.pending:
                quotas.reject_serial(serial)


class Job(object):
    description = None
    fn = None
    args = None
    kwargs = None

    def __init__(self, fn, args=None, kwargs=None, description=None):
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.description = description

    def run(self):
        try:
            args = self.args if self.args is not None else []
            kwargs = self.kwargs if self.kwargs is not None else {}
            return self.fn(*args, **kwargs)
        except:
            log.exception("Failed to execute Job (%s %s)", self.description,
                          self.fn)

    __call__ = run


def handle_serial_success(serial):
    if serial.accept and not serial.pending:
        quotas.accept_serial(serial)


def handle_serial_fail(serial):
    if serial.pending:
        quotas.reject_serial(serial)


class DeferredJobContext(object):
    def __init__(self, *args, **kwargs):
        self._serial = None
        self._deferred_jobs = []
        self._on_success = []
        self._on_failure = []

    def set_serial(self, serial):
        if self._serial is not None:
            raise ValueError("Cannot set multiple serials")
        self._serial = serial
        self.add_on_success_job(
            Job(handle_serial_success, args=(serial,)))
        self.add_on_failure_job(Job(handle_serial_fail, args=(serial,)))

    def add_deferred_job(self, def_job):
        self.add_on_success_job(def_job)
        self.add_on_failure_job(def_job)

    def add_deferred_jobs(self, def_jobs):
        self.add_on_success_jobs(def_jobs)
        self.add_on_failure_jobs(def_jobs)

    def add_on_success_job(self, def_job):
        self._on_success.append(def_job)

    def add_on_success_jobs(self, def_jobs):
        self._on_success += def_jobs

    def add_on_failure_job(self, def_job):
        self._on_failure.append(def_job)

    def add_on_failure_jobs(self, def_jobs):
        self._on_failure += def_jobs

    def _run_jobs(self, jobs):
        # Run each job independently and let jobs declare/run their dependecies
        for job in jobs:
            try:
                job.run()
            except:
                log.exception("Failed to execute job (%s)", job)

    def handle(self, success):
        if success:
            self._run_jobs(self._on_success)
        else:
            self._run_jobs(self._on_failure)


def atomic_context(func):
    @wraps(func)
    def inner(*args, **kwargs):
        ARG_NAME = "atomic_context"
        handle_context = False
        context = kwargs.get(ARG_NAME)
        if context is None:
            handle_context = True
            context = DeferredJobContext()
            kwargs[ARG_NAME] = context
        try:
            with atomic():
                res = func(*args, **kwargs)
        except:
            try:
                if handle_context:
                    context.handle(success=False)
            finally:
                raise
        else:
            if handle_context:
                context.handle(success=True)
            return res
    return inner
