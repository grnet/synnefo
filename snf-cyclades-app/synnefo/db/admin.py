# Copyright 2011 GRNET S.A. All rights reserved.
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

from django.contrib import admin
from django import forms
from synnefo.db.models import  *

class LimitForm(forms.ModelForm):
    class Meta:
        model = Limit

class LimitAdmin(admin.ModelAdmin):
    ""    

    form = LimitForm


class FlavorForm(forms.ModelForm):
    class Meta:
        model = Flavor

class FlavorAdmin(admin.ModelAdmin):
    ""    

    form = FlavorForm


class VirtualMachineForm(forms.ModelForm):
    class Meta:
        model = VirtualMachine

class VirtualMachineAdmin(admin.ModelAdmin):
    ""    

    form = VirtualMachineForm

class VirtualMachineGroupForm(forms.ModelForm):
    class Meta:
        model = VirtualMachineGroup

class VirtualMachineGroupAdmin(admin.ModelAdmin):
    ""    

    form = VirtualMachineGroupForm

class DebitForm(forms.ModelForm):
    class Meta:
        model = Debit

class DebitAdmin(admin.ModelAdmin):
    ""    

    form = DebitForm

class SynnefoUserForm(forms.ModelForm):
    class Meta:
        model = SynnefoUser

class SynnefoUserAdmin(admin.ModelAdmin):
    ""
    form = SynnefoUserForm

class ImageForm(forms.ModelForm):
    class Meta:
        model = Image

class ImageAdmin(admin.ModelAdmin):
    ""
    form = ImageForm



class VirtualMachineMetadataForm(forms.ModelForm):
    class Meta:
        model = VirtualMachineMetadata

class VirtualMachineMetadataAdmin(admin.ModelAdmin):
    ""
    form = VirtualMachineMetadataForm



admin.site.register(Limit, LimitAdmin)
admin.site.register(VirtualMachineMetadata, VirtualMachineMetadataAdmin)
admin.site.register(SynnefoUser, SynnefoUserAdmin)
admin.site.register(Flavor, FlavorAdmin)
admin.site.register(VirtualMachine, VirtualMachineAdmin)
admin.site.register(VirtualMachineGroup, VirtualMachineGroupAdmin)
admin.site.register(Debit, DebitAdmin)
admin.site.register(Image, ImageAdmin)

