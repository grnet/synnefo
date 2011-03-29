from django.contrib import admin
from django import forms
from django.db import models
from django.utils.encoding import iri_to_uri
from django.utils.translation import gettext_lazy as _
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

