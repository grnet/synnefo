class Resource(models.Model):
	res_desc = models.CharField(max_length=255)
	res_unitcost = models.IntegerField()
	res_max = models.IntegerField()
	res_quantum = models.IntegerField()

class Users(models.Model):
	user_name = models.CharField(max_length=255)
	user_credit = models.IntegerField()
	user_quota = models.IntegerField()
	user_created = models.DateField()
	resources = models.ManyToManyField(Resource)
	groups = models.ManyToManyField(Group, through='UserGroup')
	
class VMachine(models.Model):
	vm_alias = models.CharField(max_length=255)
	vm_created = models.DateTimeField()
	vm_active = models.BooleanField()
	vm_started = models.DateTimeField()
	users = models.ManyToManyField(Users)
	resources = models.ManyToManyField(Resource)
	
class ChargingLog(models.Model):
	vm_id = models.ForeignKey(VMachine)
	cl_date = models.DateTimeField()
	cl_credit = models.IntegerField()
	cl_message = models.CharField(max_length=1000)
	
class Groups(models.Model):
	gr_name = models.CharField(max_length=45)
	gr_credit = models.IntegerField()
	gr_quota = models.IntegerField()
	gr_created = models.DateTimeField()
	resources = models.ManyToManyField(Resource)
	
class UserGroup(models.Model):
	user = models.ForeignKey(Users)
	group = models.ForeignKey(Groups)
	ug_credit = models.IntegerField()
