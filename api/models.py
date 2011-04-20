# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright (c) 2011 Greek Research and Technology Network
#

from django.db import models

class Container(models.Model):
    account = models.CharField(max_length = 256)
    name = models.CharField(max_length = 256)
    date_created = models.DateTimeField(auto_now_add = True)
    
    def __unicode__(self):
        return self.name

class Object(models.Model):
    container = models.ForeignKey(Container)
    name = models.CharField(max_length = 1024)
    length = models.IntegerField()
    type = models.CharField(max_length = 256)
    hash = models.CharField(max_length = 256)
    data = models.FileField(upload_to = 'data', max_length = 256)
    date_created = models.DateTimeField(auto_now_add = True)
    date_modified = models.DateTimeField(auto_now = True)
    
    def __unicode__(self):
        return self.name

class Metadata(models.Model):
    object = models.ForeignKey(Object)
    name = models.CharField(max_length = 256)
    value = models.CharField(max_length = 1024)
    date_created = models.DateTimeField(auto_now_add = True)
    date_modified = models.DateTimeField(auto_now = True)