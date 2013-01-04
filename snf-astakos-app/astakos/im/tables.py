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

from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.template import Context, Template
from django.template.loader import render_to_string

from django_tables2 import A
import django_tables2 as tables

from astakos.im.models import *

DEFAULT_DATE_FORMAT = "d/m/Y"


MEMBER_STATUS_DISPLAY = {
    100: _('Owner'),
      0: _('Requested'),
      1: _('Pending'),
      2: _('Accepted'),
      3: _('Removing'),
      4: _('Removed'),
     -1: _('Unregistered'),
}

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
        context = getattr(table, 'context', Context())
        context.update(self.get_template_context(record, table, value,
                                                 bound_column, **kwargs))
        try:
            if self.template_code:
                return Template(self.template_code).render(context)
            else:
                return render_to_string(self.template_name, context)
        finally:
            context.pop()

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

        if self.extra_context:
            context.update(self.extra_context(record, table, self))

        return context


def action_extra_context(project, table, self):
    user = table.user
    url, action, confirm, prompt = '', '', True, ''
    append_url = ''

    if user.owns_project(project):
        url = 'astakos.im.views.project_update'
        action = _('Update')
        confirm = False
        prompt = ''
    elif user.is_project_accepted_member(project):
        url = 'astakos.im.views.project_leave'
        action = _('- Leave')
        confirm = True
        prompt = _('Are you sure you want to leave from the project ?')
    elif not user.is_project_member(project):
        url = 'astakos.im.views.project_join'
        action = _('+ Join')
        confirm = True
        prompt = _('Are you sure you want to join this project ?')
    else:
        action = _('Pending')

    url = reverse(url, args=(project.pk, )) + append_url if url else ''
    return {'action': action,
            'confirm': confirm,
            'url': url,
            'prompt': prompt}


# Table classes
class UserProjectApplicationsTable(tables.Table):
    caption = _('My projects')

    def __init__(self, *args, **kwargs):
        self.user = None

        if 'request' in kwargs and kwargs.get('request').user:
            self.user = kwargs.get('request').user

        if 'user' in kwargs:
            self.user = kwargs.pop('user')

        super(UserProjectApplicationsTable, self).__init__(*args, **kwargs)

    name = tables.LinkColumn('astakos.im.views.project_detail', args=(A('pk'),))
    issue_date = tables.DateColumn(format=DEFAULT_DATE_FORMAT)
    start_date = tables.DateColumn(format=DEFAULT_DATE_FORMAT)
    end_date = tables.DateColumn(format=DEFAULT_DATE_FORMAT)
    members_count = tables.Column(verbose_name=_("Enrolled"), default=0,
                                  sortable=False)
    membership_status = tables.Column(verbose_name=_("Status"), empty_values=(),
                                      sortable=False)
    project_action = RichLinkColumn(verbose_name=_('Action'),
                                    extra_context=action_extra_context,
                                    sortable=False)


    def render_membership_status(self, record, *args, **kwargs):
        status = record.user_status(self.user)
        if status == 100:
            return record.state
        else:
            return MEMBER_STATUS_DISPLAY.get(status, 'Unknown')

    class Meta:
        model = ProjectApplication
        fields = ('name', 'membership_status', 'issue_date', 'start_date','end_date', 'members_count')
        attrs = {'id': 'projects-list', 'class': 'my-projects alt-style'}
        template = "im/table_render.html"


class ProjectApplicationMembersTable(tables.Table):
    name = tables.Column(accessor="person.last_name", verbose_name=_('Name'))
    status = tables.Column(accessor="state", verbose_name=_('Status'))


    def render_name(self, value, record, *args, **kwargs):
        return record.person.realname

    def render_status(self, value, *args, **kwargs):
        return MEMBER_STATUS_DISPLAY.get(value, 'Unknown')

    class Meta:
        template = "im/table_render.html"
        model = ProjectMembership
        fields = ('name', 'status')
        attrs = {'id': 'members-table', 'class': 'members-table alt-style'}

