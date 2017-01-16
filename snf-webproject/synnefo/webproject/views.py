# Copyright (C) 2010-2016 GRNET S.A.
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

from django.views.generic import TemplateView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView


class TemplateViewExtra(TemplateView):
    """ TemplateView subclass that supports extra_context. """
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(TemplateViewExtra, self).get_context_data(**kwargs)
        context.update(self.extra_context)
        return context

    def post(self, *args, **kwargs):
        return self.get(*args, **kwargs)


class ListViewExtra(ListView):
    """ ListView subclass that supports extra_context. """
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(ListViewExtra, self).get_context_data(**kwargs)
        context.update(self.extra_context)
        return context

    def post(self, *args, **kwargs):
        return self.get(*args, **kwargs)


class DetailViewExtra(DetailView):
    """ DetailView subclass that supports extra_context. """
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(DetailViewExtra, self).get_context_data(**kwargs)
        context.update(self.extra_context)
        return context

    def post(self, *args, **kwargs):
        return self.get(*args, **kwargs)
