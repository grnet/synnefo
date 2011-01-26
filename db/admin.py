from django.contrib import admin
from django import forms
from django.db import models
from django.utils.encoding import iri_to_uri
from django.utils.translation import gettext_lazy as _
from models import  *

class LimitForm(forms.ModelForm):
    class Meta:
        model = Limit

class LimitAdmin(admin.ModelAdmin):
    ""    

    form = LimitForm

class UserLimitForm(forms.ModelForm):
    class Meta:
        model = UserLimit

class UserLimitAdmin(admin.ModelAdmin):
    ""    

    form = UserLimitForm

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


class AccountingLogForm(forms.ModelForm):
    class Meta:
        model = AccountingLog

class AccountingLogAdmin(admin.ModelAdmin):
    ""    

    form = AccountingLogForm

class OceanUserForm(forms.ModelForm):
    class Meta:
        model = OceanUser

class OceanUserAdmin(admin.ModelAdmin):
    ""
    form = OceanUserForm

class ImageForm(forms.ModelForm):
    class Meta:
        model = Image

class ImageAdmin(admin.ModelAdmin):
    ""
    form = ImageForm


admin.site.register(Limit, LimitAdmin)
admin.site.register(OceanUser, OceanUserAdmin)
admin.site.register(UserLimit, UserLimitAdmin)
admin.site.register(Flavor, FlavorAdmin)
admin.site.register(VirtualMachine, VirtualMachineAdmin)
admin.site.register(AccountingLog, AccountingLogAdmin)
admin.site.register(Image, ImageAdmin)

