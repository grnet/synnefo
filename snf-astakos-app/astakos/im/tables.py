import django_tables2 as tables

from django.utils.translation import ugettext as _
from django_tables2 import A
from astakos.im.models import *
from django.utils.safestring import mark_safe

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

class UserProjectApplicationsTable(tables.Table):

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
    membership_status = tables.Column(verbose_name=_("Status"), empty_values=(),
                                      orderable=False)
    members_count = tables.Column(verbose_name=_("Enrolled"), default=0,
                                  sortable=False)
    


    def render_membership_status(self, record, *args, **kwargs):
        status = record.member_status(self.user)
        if status == 100:
            return record.state
        else:
            return MEMBER_STATUS_DISPLAY.get(status, 'Unknown')

    class Meta:
        model = ProjectApplication
        fields = ('name', 'membership_status', 'issue_date', 'start_date', 'members_count')
        attrs = {'id': 'projects-list', 'class': 'my-projects alt-style'}
        caption = _('My projects')
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

