# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def project_holder(self, project):
        return "project:" + project

    def user_holder(self, user):
        return "user:" + user

    def forwards(self, orm):
        provisions = list(orm.Provision.objects.filter(source="system"))
        if provisions:
            new_provisions = []
            for provision in provisions:
                uuid = provision.holder
                h1 = orm.Provision(serial=provision.serial,
                                   holder=self.user_holder(uuid),
                                   source=self.project_holder(uuid),
                                   resource=provision.resource,
                                   quantity=provision.quantity)
                h2 = orm.Provision(serial=provision.serial,
                                   holder=self.project_holder(uuid),
                                   source=None,
                                   resource=provision.resource,
                                   quantity=provision.quantity)
                new_provisions.extend([h1, h2])
            orm.Provision.objects.bulk_create(new_provisions)
            orm.Provision.objects.filter(source="system").delete()

    def backwards(self, orm):
        "Write your backwards methods here."

    models = {
        'quotaholder_app.commission': {
            'Meta': {'object_name': 'Commission'},
            'clientkey': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'issue_datetime': ('django.db.models.fields.DateTimeField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '4096'}),
            'serial': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'quotaholder_app.holding': {
            'Meta': {'unique_together': "(('holder', 'source', 'resource'),)", 'object_name': 'Holding'},
            'holder': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'limit': ('django.db.models.fields.BigIntegerField', [], {}),
            'resource': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'null': 'True'}),
            'usage_max': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'usage_min': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
        'quotaholder_app.provision': {
            'Meta': {'object_name': 'Provision'},
            'holder': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.BigIntegerField', [], {}),
            'resource': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'serial': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provisions'", 'to': "orm['quotaholder_app.Commission']"}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'null': 'True'})
        },
        'quotaholder_app.provisionlog': {
            'Meta': {'object_name': 'ProvisionLog'},
            'delta_quantity': ('django.db.models.fields.BigIntegerField', [], {}),
            'holder': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issue_time': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'limit': ('django.db.models.fields.BigIntegerField', [], {}),
            'log_time': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'resource': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'serial': ('django.db.models.fields.BigIntegerField', [], {}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'null': 'True'}),
            'usage_max': ('django.db.models.fields.BigIntegerField', [], {}),
            'usage_min': ('django.db.models.fields.BigIntegerField', [], {})
        }
    }

    complete_apps = ['quotaholder_app']
    symmetrical = True
