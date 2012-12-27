import django_tables2 as tables

from django.utils.translation import ugettext as _
from django_tables2 import A
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
    state = tables.Column(verbose_name="Status")
    members_count = tables.Column(verbose_name="Enrolled", default=0)
    membership_status = tables.Column(verbose_name="My status", empty_values=(),
                                      orderable=False)

    def render_membership_status(self, *args, **kwargs):
        return MEMBER_STATUS_DISPLAY.get(kwargs.get('record').member_status(self.user))

    class Meta:
        model = ProjectApplication
        fields = ('name', 'membership_status', 'issue_date', 'start_date',
                  'state', 'members_count')

