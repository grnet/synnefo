from django.db import models

class Limits(models.Model):
    lim_id = models.IntegerField(primary_key=True)
    lim_desc = models.CharField(max_length=45)

class Users(models.Model):
    user_id = models.IntegerField(primary_key=True)
    user_name = models.CharField(max_length=255)
    user_credit = models.IntegerField()
    user_quota = models.IntegerField()
    user_created = models.DateField()
    limits = models.ManyToManyField(Limits, through='UserLimit')

class UserLimit(models.Model):
    lim_id = models.ForeignKey(Limits, primary_key=True)
    user_id = models.ForeignKey(Users, primary_key=True)
    ul_value = models.IntegerField()

class Flavor(models.Model):
    flv_id = models.IntegerField(primary_key=True)
    flv_desc = models.CharField(max_length=255)
    flv_cost_active = models.IntegerField()
    flv_cost_inactive = models.IntegerField()
    flv_detailed = models.CharField(max_length=1000)

class VMachine(models.Model):
    vm_id = models.IntegerField(primary_key=True)
    vm_alias = models.CharField(max_length=255)
    vm_created = models.DateTimeField()
    vm_state = models.IntegerField()
    vm_started = models.DateTimeField()
    user_id = models.ForeignKey(Users)
    flv_id = models.ForeignKey(Flavor)

class ChargingLog(models.Model):
    cl_id = models.IntegerField(primary_key=True)
    vm_id = models.ForeignKey(VMachine)
    cl_date = models.DateTimeField()
    cl_credit = models.IntegerField()
    cl_message = models.CharField(max_length=1000)
