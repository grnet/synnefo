# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

from django.db import IntegrityError, transaction
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from functools import wraps
from smtplib import SMTPException

from astakos.im.models import (
    AstakosUser, AstakosGroup, GroupKind, Resource, Service, RESOURCE_SEPARATOR,
    Project, ProjectApplication, ProjectMembership, filter_queryset_by_property
)
from astakos.im.api.backends.base import BaseBackend, SuccessResult, FailureResult
from astakos.im.api.backends.errors import (
    ItemNotExists, ItemExists, MissingIdentifier, MultipleItemsExist
)
# from astakos.im.api.backends.lib.notifications import EmailNotification

from astakos.im.util import reserved_email, model_to_dict
from astakos.im.endpoints.qh import get_quota, send_quota
from astakos.im.settings import SITENAME
try:
    from astakos.im.messages import astakos_messages
except:
    pass

import logging

logger = logging.getLogger(__name__)

DEFAULT_CONTENT_TYPE = None


def safe(func):
    """Decorator function for views that implement an API method."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        logger.debug('%s %s %s' % (func, args, kwargs))
        try:
            data = func(self, *args, **kwargs) or ()
        except Exception, e:
            logger.exception(e)
            return FailureResult(e)
        else:
            return SuccessResult(data)
    return wrapper


class DjangoBackend(BaseBackend):
    def _lookup_object(self, model, **kwargs):
        """
        Returns an object of the specific model matching the given lookup
        parameters.
        """
        if not kwargs:
            raise MissingIdentifier
        try:
            return model.objects.get(**kwargs)
        except model.DoesNotExist:
            raise ItemNotExists(model._meta.verbose_name, **kwargs)
        except model.MultipleObjectsReturned:
            raise MultipleItemsExist(model._meta.verbose_name, **kwargs)

    def _lookup_user(self, id):
        """
        Returns an AstakosUser having this id.
        """
        if not isinstance(id, int):
            raise TypeError('User id should be of type int')
        return self._lookup_object(AstakosUser, id=id)

    def _lookup_service(self, id):
        """
        Returns an Service having this id.
        """
        if not isinstance(id, int):
            raise TypeError('Service id should be of type int')
        return self._lookup_object(Service, id=id)

    def _list(self, model, filter=()):
        q = model.objects.all()
        if filter:
            q = q.filter(id__in=filter)
        return map(lambda o: self._details(o), q)

    def _details(self, obj):
        return model_to_dict(obj, exclude=[])

    def _create_object(self, model, **kwargs):
        o = model.objects.create(**kwargs)
        o.save()
        return o

    def _update_object(self, model, id, save=True, **kwargs):
        o = self._lookup_object(model, id=id)
        if kwargs:
            o.__dict__.update(kwargs)
        if save:
            o.save()
        return o

    @safe
    def update_user(self, user_id, renew_token=False, **kwargs):
        user = self._update_object(AstakosUser, user_id, save=False, **kwargs)
        if renew_token:
            user.renew_token()
        if kwargs or renew_token:
            user.save()

    @safe
    def create_user(self, **kwargs):
        policies = kwargs.pop('policies', ())
        permissions = kwargs.pop('permissions', ())
        groups = kwargs.pop('groups', ())
        password = kwargs.pop('password', None)
        provider = kwargs.pop('provider', 'local')

        u = self._create_object(AstakosUser, **kwargs)

        if password:
            u.set_password(password)
        u.permissions = permissions
        u.policies = policies
        u.extended_groups = groups

        if not u.has_auth_provider(provider):
            u.add_auth_provider(provider)

        return self._details(u)

    @safe
    def add_policies(self, user_id, update=False, policies=()):
        user = self._lookup_user(user_id)
        rejected = []
        append = rejected.append
        for p in policies:
            service = p.get('service')
            resource = p.get('resource')
            uplimit = p.get('uplimit')
            try:
                user.add_policy(service, resource, uplimit, update)
            except (ObjectDoesNotExist, IntegrityError), e:
                append((service, resource, e))
        return rejected

    @safe
    def remove_policies(self, user_id, policies=()):
        user = self._lookup_user(user_id)
        if not user:
            return user_id
        rejected = []
        append = rejected.append
        for p in policies:
            service = p.get('service')
            resource = p.get('resource')
            try:
                user.delete_policy(service, resource)
            except ObjectDoesNotExist, e:
                append((service, resource, e))
        return rejected
    
    @safe
    def add_permissions(self, user_id, permissions=()):
        user = self._lookup_user(user_id)
        rejected = []
        append = rejected.append
        for p in permissions:
            try:
                user.add_permission(p)
            except IntegrityError, e:
                append((p, e))
        return rejected

    @safe
    def remove_permissions(self, user_id, permissions=()):
        user = self._lookup_user(user_id)
        rejected = []
        append = rejected.append
        for p in permissions:
            try:
                user.remove_permission(p)
            except (ObjectDoesNotExist, IntegrityError), e:
                append((p, e))
        return rejected

    @safe
    def invite_users(self, senderid, recipients=()):
        user = self._lookup_user(senderid)
        rejected = []
        append = rejected.append
        for r in recipients:
            email = r.get('email')
            realname = r.get('realname')
            try:
                user.invite(email, realname)
            except (IntegrityError, SMTPException), e:
                append((email, e))
        return rejected

    @safe
    def list_users(self, filter=()):
        return self._list(AstakosUser, filter=filter)

    @safe
    def get_resource_usage(self, user_id):
        user = self._lookup_user(user_id)
        c, data = get_quota((user,))
        resources = []
        append = resources.append
        for t in data:
            t = (i if i else 0 for i in t)
            (entity, name, quantity, capacity, importLimit, exportLimit,
             imported, exported, returned, released, flags) = t
            service, sep, resource = name.partition(RESOURCE_SEPARATOR)
            resource = Resource.objects.select_related().get(
                service__name=service, name=resource)
            d = dict(name=name,
                     description=resource.desc,
                     unit=resource.unit or '',
                     maxValue=quantity + capacity,
                     currValue=quantity + imported - released - exported + returned)
            append(d)
        return resources

    @safe
    def list_resources(self, filter=()):
        return self._list(Resource, filter=filter)

    @safe
    def create_service(self, **kwargs):
        resources = kwargs.pop('resources', ())
        s = self._create_object(Service, **kwargs)
        s.resources = resources
        return self._details(s)

    @safe
    def remove_services(self, ids=()):
        # TODO return information for unknown ids
        q = Service.objects.filter(id__in=ids)
        q.delete()

    @safe
    def update_service(self, service_id, renew_token=False, **kwargs):
        s = self._update_object(Service, service_id, save=False, **kwargs)
        if renew_token:
            s.renew_token()

        if kwargs or renew_token:
            s.save()

    @safe
    def add_resources(self, service_id, update=False, resources=()):
        s = self._lookup_service(service_id)
        rejected = []
        append = rejected.append
        for r in resources:
            try:
                rr = r.copy()
                resource_id = rr.pop('id', None)
                if update:
                    if not resource_id:
                        raise MissingIdentifier
                    resource = self._update_object(Resource, resource_id, **rr)
                else:
                    resource = self._create_object(Resource, service=s, **rr)
            except Exception, e:
                append((r, e))
        return rejected

    @safe
    def remove_resources(self, service_id, ids=()):
        # TODO return information for unknown ids
        q = Resource.objects.filter(service__id=service_id,
                                id__in=ids)
        q.delete()

    @safe
    def create_group(self, **kwargs):
        policies = kwargs.pop('policies', ())
        permissions = kwargs.pop('permissions', ())
        members = kwargs.pop('members', ())
        owners = kwargs.pop('owners', ())

        g = self._create_object(AstakosGroup, **kwargs)

        g.permissions = permissions
        g.policies = policies
#        g.members = members
        g.owners = owners
        return self._details(g)
    
    
    @safe
    def submit_application(self, **kwargs):
        app = self._create_object(ProjectApplication, **kwargs)
        notification = build_notification(
            settings.SERVER_EMAIL,
            [settings.ADMINS],
            _(GROUP_CREATION_SUBJECT) % {'group':app.definition.name},
            _('An new project application identified by %(serial)s has been submitted.') % app.serial
        )
        notification.send()
    
    @safe
    def list_applications(self):
        return self._list(ProjectAppication)
    
    @safe
    def approve_application(self, serial):
        app = self._lookup_object(ProjectAppication, serial=serial)
        notify = False
        if not app.precursor_application:
            kwargs = {
                'application':app,
                'creation_date':datetime.now(),
                'last_approval_date':datetime.now(),
            }
            project = self._create_object(Project, **kwargs)
        else:
            project = app.precursor_application.project
            last_approval_date = project.last_approval_date
            if project.is_valid:
                project.application = app
                project.last_approval_date = datetime.now()
                project.save()
            else:
                raise Exception(_(astakos_messages.INVALID_PROJECT) % project.__dict__)
        
        r = _synchonize_project(project.serial)
        if not r.is_success:
            # revert to precursor
            project.appication = app.precursor_application
            if project.application:
                project.last_approval_date = last_approval_date
            project.save()
            r = synchonize_project(project.serial)
            if not r.is_success:
                raise Exception(_(astakos_messages.QH_SYNC_ERROR))
        else:
            project.last_application_synced = app
            project.save()
            sender, recipients, subject, message
            notification = build_notification(
                settings.SERVER_EMAIL,
                [project.owner.email],
                _('Project application has been approved on %s alpha2 testing' % SITENAME),
                _('Your application request %(serial)s has been apporved.')
            )
            notification.send()
    
    
    @safe
    def list_projects(self, filter_property=None):
        if filter_property:
            q = filter_queryset_by_property(
                Project.objects.all(),
                filter_property
            )
            return map(lambda o: self._details(o), q)
        return self._list(Project)
        

    
    @safe
    def add_project_member(self, serial, user_id, request_user):
        project = self._lookup_object(Project, serial=serial)
        user = self.lookup_user(user_id)
        if not project.owner == request_user:
            raise Exception(_(astakos_messages.NOT_PROJECT_OWNER))
        
        if not project.is_alive:
            raise Exception(_(astakos_messages.NOT_ALIVE_PROJECT) % project.__dict__)
        if len(project.members) + 1 > project.limit_on_members_number:
            raise Exception(_(astakos_messages.MEMBER_NUMBER_LIMIT_REACHED))
        m = self._lookup_object(ProjectMembership, person=user, project=project)
        if m.is_accepted:
            return
        m.is_accepted = True
        m.decision_date = datetime.now()
        m.save()
        notification = build_notification(
            settings.SERVER_EMAIL,
            [user.email],
            _('Your membership on project %(name)s has been accepted.') % project.definition.__dict__, 
            _('Your membership on project %(name)s has been accepted.') % project.definition.__dict__,
        )
        notification.send()
    
    @safe
    def remove_project_member(self, serial, user_id, request_user):
        project = self._lookup_object(Project, serial=serial)
        if not project.is_alive:
            raise Exception(_(astakos_messages.NOT_ALIVE_PROJECT) % project.__dict__)
        if not project.owner == request_user:
            raise Exception(_(astakos_messages.NOT_PROJECT_OWNER))
        user = self.lookup_user(user_id)
        m = self._lookup_object(ProjectMembership, person=user, project=project)
        if not m.is_accepted:
            return
        m.is_accepted = False
        m.decision_date = datetime.now()
        m.save()
        notification = build_notification(
            settings.SERVER_EMAIL,
            [user.email],
            _('Your membership on project %(name)s has been removed.') % project.definition.__dict__, 
            _('Your membership on project %(name)s has been removed.') % project.definition.__dict__,
        )
        notification.send()    
    
    @safe
    def suspend_project(self, serial):
        project = self._lookup_object(Project, serial=serial)
        project.suspend()
        notification = build_notification(
            settings.SERVER_EMAIL,
            [project.owner.email],
            _('Project %(name)s has been suspended on %s alpha2 testing' % SITENAME),
            _('Project %(name)s has been suspended on %s alpha2 testing' % SITENAME)
        )
        notification.send()
    
    @safe
    def terminate_project(self, serial):
        project = self._lookup_object(Project, serial=serial)
        project.termination()
        notification = build_notification(
            settings.SERVER_EMAIL,
            [project.owner.email],
            _('Project %(name)s has been terminated on %s alpha2 testing' % SITENAME),
            _('Project %(name)s has been terminated on %s alpha2 testing' % SITENAME)
        )
        notification.send()
    
    @safe
    def synchonize_project(self, serial):
        project = self._lookup_object(Project, serial=serial)
        project.sync()