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

from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.template import Context, Template
from django.template.loader import render_to_string

from django_tables2 import A
import django_tables2 as tables

from astakos.im.models import *
from astakos.im.util import truncatename
from astakos.im.functions import can_join_request, membership_allowed_actions


DEFAULT_DATE_FORMAT = "d/m/Y"


class LinkColumn(tables.LinkColumn):

    def __init__(self, *args, **kwargs):
        self.coerce = kwargs.pop('coerce', None)
        self.append = kwargs.pop('append', None)
        super(LinkColumn, self).__init__(*args, **kwargs)

    def get_value(self, value, record, bound_column):
        return value

    def render(self, value, record, bound_column):
        value = self.get_value(value, record, bound_column)
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


class ProjectNameColumn(LinkColumn):

    def get_value(self, value, record, bound_column):
        # inspect columnt context to resolve user, fallback to value
        # if failed
        try:
            table = getattr(bound_column, 'table', None)
            if table:
                user = getattr(table, 'request').user
                value = record.display_name_for_user(user)
        except:
            pass
        return value


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

    def get_template_context(self, record, table, value, bound_column,
                             **kwargs):
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


def action_extra_context(project, table, self):
    user = table.user
    url, action, confirm, prompt = '', '', True, ''

    membership = table.memberships.get(project.id)
    if membership is not None:
        allowed = membership_allowed_actions(membership, user)
        if 'leave' in allowed:
            url = reverse('astakos.im.views.project_leave',
                          args=(membership.project.uuid,))
            action = _('Leave')
            confirm = True
            prompt = _('Are you sure you want to leave from the project?')
        elif 'cancel' in allowed:
            url = reverse('project_cancel_join',
                          args=(project.uuid,))
            action = _('Cancel')
            confirm = True
            prompt = _('Are you sure you want to cancel the join request?')

    if can_join_request(project, user, membership):
        url = reverse('project_join', args=(project.uuid,))
        action = _('Join')
        confirm = True
        prompt = _('Are you sure you want to join this project?')

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


def project_name_append(project, column):
    if project.state != project.UNINITIALIZED and \
            project.last_application is not None and \
            project.last_application.state == ProjectApplication.PENDING:
        return mark_safe("<br /><i class='tiny'>%s</i>" %
                         _('modifications pending'))
    return u''


# Table classes
class UserProjectsTable(UserTable):

    _links = [
        {'url': '?show_base=1', 'label': 'Show system projects'},
        {'url': '?', 'label': 'Hide system projects'}
    ]
    links = []

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        if self.request and self.request.user.is_project_admin():
            self.links = [self._links[0]]
            if self.request and self.request.GET.get('show_base', False):
                self.links = [self._links[1]]
        self.pending_apps = kwargs.pop('pending_apps')
        self.memberships = kwargs.pop('memberships')
        self.accepted = kwargs.pop('accepted')
        self.requested = kwargs.pop('requested')
        super(UserProjectsTable, self).__init__(*args, **kwargs)

        if self.request and self.request.user.is_project_admin():
            self.caption = _("Projects")
            owner_col = dict(self.columns.items())['owner']
            setattr(owner_col.column, 'accessor', 'owner.realname_with_email')

    caption = _('My projects')

    name = ProjectNameColumn('project_detail',
                      coerce=lambda x: truncatename(x, 25),
                      append=project_name_append,
                      args=(A('uuid'),),
                      orderable=False,
                      accessor='display_name')

    creation_date = tables.DateColumn(verbose_name=_('Application'),
                                      format=DEFAULT_DATE_FORMAT,
                                      orderable=False,
                                      accessor='creation_date')
    end_date = tables.DateColumn(verbose_name=_('Expiration'),
                                 format=DEFAULT_DATE_FORMAT,
                                 orderable=False,
                                 accessor='end_date')
    members_count_f = tables.Column(verbose_name=_("Members"),
                                    empty_values=(),
                                    orderable=False)
    owner = tables.Column(verbose_name=_("Owner"),
                          accessor='owner.realname')
    membership_status = tables.Column(verbose_name=_("Status"),
                                      empty_values=(),
                                      orderable=False)
    project_action = RichLinkColumn(verbose_name=_('Action'),
                                    extra_context=action_extra_context,
                                    orderable=False)

    def render_membership_status(self, record, *args, **kwargs):
        if self.user.owns_project(record) or self.user.is_project_admin():
            return record.state_display()
        else:
            m = self.memberships.get(record.id)
            if m:
                return m.user_friendly_state_display()
            return _('Not a member')

    def render_members_count_f(self, record, *args, **kwargs):
        append = ""
        project = record
        if project is None:
            append = mark_safe("<i class='tiny'>%s</i>" % (_('pending'),))

        c = len(self.requested.get(project.id, []))
        if c > 0:
            pending_members_url = reverse(
                'project_pending_members',
                kwargs={'project_uuid': record.uuid})

            pending_members = "<i class='tiny'> - %d %s</i>" % (
                c, _('pending'))
            if (
                self.user.owns_project(record) or
                self.user.is_project_admin()
            ):
                pending_members = ("<i class='tiny'>" +
                                   " - <a href='%s'>%d %s</a></i>" %
                                   (pending_members_url, c, _('pending')))
            append = mark_safe(pending_members)
        members_url = reverse('project_approved_members',
                              kwargs={'project_uuid': record.uuid})
        members_count = len(self.accepted.get(project.id, []))
        if self.user.owns_project(record) or self.user.is_project_admin():
            if project.is_alive:
                members_count = '<a href="%s">%d</a>' % (members_url,
                                                         members_count)
        return mark_safe(str(members_count) + append)

    class Meta:
        sequence = ('name', 'membership_status', 'owner', 'creation_date',
                    'end_date', 'members_count_f', 'project_action')
        attrs = {'id': 'projects-list', 'class': 'my-projects alt-style'}
        template = "im/table_render.html"
        empty_text = _('No projects')


def member_action_extra_context(membership, table, col):

    context = []
    urls, actions, prompts, confirms = [], [], [], []

    if membership.project.is_deactivated():
        return context

    if membership.state == ProjectMembership.REQUESTED:
        urls = ['project_reject_member',
                'project_accept_member']
        actions = [_('Reject'), _('Accept')]
        prompts = [_('Are you sure you want to reject this member?'),
                   _('Are you sure you want to accept this member?')]
        confirms = [True, True]

    if membership.state in ProjectMembership.ACCEPTED_STATES:
        urls = ['project_remove_member']
        actions = [_('Remove')]
        prompts = [_('Are you sure you want to remove this member?')]
        confirms = [True, True]

    for i, url in enumerate(urls):
        context.append(dict(url=reverse(url, args=(membership.project.uuid,
                                                   membership.pk,)),
                            action=actions[i], prompt=prompts[i],
                            confirm=confirms[i]))
    return context


class ProjectMembersTable(UserTable):
    input = "<input type='checkbox' name='all-none'/>"
    check = tables.Column(accessor="person.id", verbose_name=mark_safe(input),
                          orderable=False)
    email = tables.Column(accessor="person.email", verbose_name=_('Email'),
                          orderable=False)
    status = tables.Column(accessor="state", verbose_name=_('Status'),
                           orderable=False)
    project_action = RichLinkColumn(verbose_name=_('Action'),
                                    extra_context=member_action_extra_context,
                                    orderable=False)

    def __init__(self, project, *args, **kwargs):
        self.project = project
        super(ProjectMembersTable, self).__init__(*args, **kwargs)
        if not self.user.owns_project(self.project):
            self.exclude = ('project_action', )

    def render_check(self, value, record, *args, **kwargs):
        checkbox = ("<input type='checkbox' value='%d' name ='actions'>" %
                    record.id)
        return mark_safe(checkbox)

    def render_status(self, value, record, *args, **kwargs):
        return record.state_display()

    class Meta:
        template = "im/table_render.html"
        attrs = {'id': 'members-table', 'class': 'members-table alt-style'}
        empty_text = _('No members')
