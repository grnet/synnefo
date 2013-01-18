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

from collections import defaultdict

from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.template import Context, Template
from django.template.loader import render_to_string
from django.core.exceptions import PermissionDenied

from django_tables2 import A
import django_tables2 as tables

from astakos.im.models import *
from astakos.im.templatetags.filters import truncatename
from astakos.im.functions import do_join_project_checks, \
                                 do_leave_project_checks

DEFAULT_DATE_FORMAT = "d/m/Y"


class LinkColumn(tables.LinkColumn):

    def __init__(self, *args, **kwargs):
        self.coerce = kwargs.pop('coerce', None)
        self.append = kwargs.pop('append', None)
        super(LinkColumn, self).__init__(*args, **kwargs)

    def render(self, value, record, bound_column):
        link = super(LinkColumn, self).render(value, record, bound_column)
        extra = ''
        if self.append:
            if callable(self.append):
                extra = self.append(record, bound_column)
            else:
                extra = self.append
        return mark_safe(link + extra)

    def render_link(self, uri, text, attrs=None):
        if self.coerce:
            text = self.coerce(text)
        return super(LinkColumn, self).render_link(uri, text, attrs)


# Helper columns
class RichLinkColumn(tables.TemplateColumn):

    method = 'POST'

    confirm_prompt = _('Yes')
    cancel_prompt = _('No')
    confirm = True

    prompt = _('Confirm action ?')

    action_tpl = None
    action = _('Action')
    extra_context = lambda record, table, column: {}

    url = None
    url_args = ()
    resolve_func = None

    def __init__(self, *args, **kwargs):
        kwargs['template_name'] = kwargs.get('template_name',
                                             'im/table_rich_link_column.html')
        for attr in ['method', 'confirm_prompt',
                     'cancel_prompt', 'prompt', 'url',
                     'url_args', 'action', 'confirm',
                     'resolve_func', 'extra_context']:
            setattr(self, attr, kwargs.pop(attr, getattr(self, attr)))

        super(RichLinkColumn, self).__init__(*args, **kwargs)

    def render(self, record, table, value, bound_column, **kwargs):
        # If the table is being rendered using `render_table`, it hackily
        # attaches the context to the table as a gift to `TemplateColumn`. If
        # the table is being rendered via `Table.as_html`, this won't exist.
        content = ''
        for extra_context in self.get_template_context(record, table, value,
                                                       bound_column, **kwargs):
            context = getattr(table, 'context', Context())
            context.update(extra_context)
            try:
                if self.template_code:
                    content += Template(self.template_code).render(context)
                else:
                    content += render_to_string(self.template_name, context)
            finally:
                context.pop()

        return mark_safe(content)

    def get_confirm(self, record, table):
        if callable(self.confirm):
            return self.confirm(record, table)
        return self.confirm

    def resolved_url(self, record, table):
        if callable(self.url):
            return self.url(record, table)

        if not self.url:
            return '#'

        args = list(self.url_args)
        for index, arg in enumerate(args):
            if isinstance(arg, A):
                args[index] = arg.resolve(record)
        return reverse(self.url, args=args)

    def get_action(self, record, table):
        if callable(self.action):
            return self.action(record, table)
        return self.action

    def get_prompt(self, record, table):
        if callable(self.prompt):
            return self.prompt(record, table)
        return self.prompt

    def get_template_context(self, record, table, value, bound_column, **kwargs):
        context = {'default': bound_column.default,
                   'record': record,
                   'value': value,
                   'col': self,
                   'url': self.resolved_url(record, table),
                   'prompt': self.get_prompt(record, table),
                   'action': self.get_action(record, table),
                   'confirm': self.get_confirm(record, table)
                  }

        # decide whether to return dict or a list of dicts in case we want to
        # display multiple actions within a cell.
        if self.extra_context:
            contexts = []
            extra_contexts = self.extra_context(record, table, self)
            if isinstance(extra_contexts, list):
                for extra_context in extra_contexts:
                    newcontext = dict(context)
                    newcontext.update(extra_context)
                    contexts.append(newcontext)
            else:
                context.update(extra_contexts)
                contexts = [context]
        else:
            contexts = [context]

        return contexts


def action_extra_context(application, table, self):
    user = table.user
    url, action, confirm, prompt = '', '', True, ''
    append_url = ''

    can_join = can_leave = False
    project = application.get_project()

    if project:
        try:
            do_join_project_checks(project)
            can_join = True
        except PermissionDenied, e:
            pass

        try:
            do_leave_project_checks(project)
            can_leave = True
        except PermissionDenied:
            pass

    if can_leave and user.is_project_member(application):
        url = 'astakos.im.views.project_leave'
        action = _('Leave')
        confirm = True
        prompt = _('Are you sure you want to leave from the project ?')
    elif can_join and not user.is_project_member(application):
        url = 'astakos.im.views.project_join'
        action = _('Join')
        confirm = True
        prompt = _('Are you sure you want to join this project ?')
    else:
        action = ''
        confirm = False
        url = None

    url = reverse(url, args=(application.pk, )) + append_url if url else ''

    return {'action': action,
            'confirm': confirm,
            'url': url,
            'prompt': prompt}


class UserTable(tables.Table):

    def __init__(self, *args, **kwargs):
        self.user = None

        if 'request' in kwargs and kwargs.get('request').user:
            self.user = kwargs.get('request').user

        if 'user' in kwargs:
            self.user = kwargs.pop('user')

        super(UserTable, self).__init__(*args, **kwargs)


def project_name_append(application, column):
    if application.has_pending_modifications():
        return mark_safe("<br /><i class='tiny'>%s</i>" % \
                                                _('modifications pending'))
    return u''

# Table classes
class UserProjectApplicationsTable(UserTable):
    caption = _('My projects')

    name = LinkColumn('astakos.im.views.project_detail',
                      coerce=lambda x: truncatename(x, 25),
                      append=project_name_append,
                      args=(A('pk'),))
    issue_date = tables.DateColumn(verbose_name=_('Application'), format=DEFAULT_DATE_FORMAT)
    start_date = tables.DateColumn(format=DEFAULT_DATE_FORMAT)
    end_date = tables.DateColumn(verbose_name=_('Expiration'), format=DEFAULT_DATE_FORMAT)
    members_count = tables.Column(verbose_name=_("Members"), default=0,
                                  orderable=False)
    membership_status = tables.Column(verbose_name=_("Status"), empty_values=(),
                                      orderable=False)
    project_action = RichLinkColumn(verbose_name=_('Action'),
                                    extra_context=action_extra_context,
                                    orderable=False)


    def render_membership_status(self, record, *args, **kwargs):
        if self.user.owns_project(record):
            return record.state_display()
        else:
            status = record.user_status(self.user)
            return record.user_status_display(self.user)

    def render_members_count(self, record, *args, **kwargs):
        append = ""
	application = record
        project = application.get_project()
        if project is None:
            append = mark_safe("<i class='tiny'>%s</i>" % (_('pending'),))

        c = project.count_pending_memberships()
        if c > 0:
            append = mark_safe("<i class='tiny'> - %d %s</i>"
                                % (c, _('pending')))

        return mark_safe(str(record.members_count()) + append)
        
    class Meta:
        model = ProjectApplication
        fields = ('name', 'membership_status', 'issue_date', 'end_date', 'members_count')
        attrs = {'id': 'projects-list', 'class': 'my-projects alt-style'}
        template = "im/table_render.html"
        empty_text = _('No projects')
        exclude = ('start_date', )

class ProjectModificationApplicationsTable(UserProjectApplicationsTable):
    name = LinkColumn('astakos.im.views.project_detail',
                      verbose_name=_('Action'),
                      coerce= lambda x: 'review',
                      args=(A('pk'),))
    class Meta:
        attrs = {'id': 'projects-list', 'class': 'my-projects alt-style'}
        fields = ('issue_date', 'membership_status')
        exclude = ('start_date', 'end_date', 'members_count', 'project_action')

def member_action_extra_context(membership, table, col):

    context = []
    urls, actions, prompts, confirms = [], [], [], []

    if membership.state == ProjectMembership.REQUESTED:
        urls = ['astakos.im.views.project_reject_member',
                'astakos.im.views.project_accept_member']
        actions = [_('Reject'), _('Accept')]
        prompts = [_('Are you sure you want to reject this member ?'),
                   _('Are you sure you want to accept this member ?')]
        confirms = [True, True]

    if membership.state == ProjectMembership.ACCEPTED:
        urls = ['astakos.im.views.project_remove_member']
        actions = [_('Remove')]
        if table.user == membership.person:
            actions = [_('Leave')]
        prompts = [_('Are you sure you want to remove this member ?')]
        confirms = [True, True]


    for i, url in enumerate(urls):
        context.append(dict(url=reverse(url, args=(table.project.pk,
                                                   membership.person.pk)),
                            action=actions[i], prompt=prompts[i],
                            confirm=confirms[i]))
    return context

class ProjectApplicationMembersTable(UserTable):
    name = tables.Column(accessor="person.last_name", verbose_name=_('Name'))
    status = tables.Column(accessor="state", verbose_name=_('Status'))
    project_action = RichLinkColumn(verbose_name=_('Action'),
                                    extra_context=member_action_extra_context,
                                    orderable=False)


    def __init__(self, project, *args, **kwargs):
        self.project = project
        super(ProjectApplicationMembersTable, self).__init__(*args, **kwargs)
        if not self.user.owns_project(self.project):
            self.exclude = ('project_action', )


    def render_name(self, value, record, *args, **kwargs):
        return record.person.realname

    def render_status(self, value, *args, **kwargs):
        return USER_STATUS_DISPLAY.get(value, 'Unknown')

    class Meta:
        template = "im/table_render.html"
        model = ProjectMembership
        fields = ('name', 'status')
        attrs = {'id': 'members-table', 'class': 'members-table alt-style'}
        empty_text = _('No members')

