# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

MAX = 2**63 - 1

class Migration(DataMigration):

    def forwards(self, orm):
        orm.Provision.objects.filter(quantity__gt=MAX).update(quantity=MAX)
        orm.Holding.objects.filter(usage_min__gt=MAX).update(usage_min=MAX)
        orm.Holding.objects.filter(usage_max__gt=MAX).update(usage_max=MAX)
        orm.Holding.objects.filter(limit__gt=MAX).update(limit=MAX)
        orm.ProvisionLog.objects.filter(delta_quantity__gt=MAX).\
            update(delta_quantity=MAX)
        orm.ProvisionLog.objects.filter(usage_min__gt=MAX).\
            update(usage_min=MAX)
        orm.ProvisionLog.objects.filter(usage_max__gt=MAX).\
            update(usage_max=MAX)
        orm.ProvisionLog.objects.filter(limit__gt=MAX).update(limit=MAX)

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
            'limit': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'resource': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'null': 'True'}),
            'usage_max': ('snf_django.lib.db.fields.IntDecimalField', [], {'default': '0', 'max_digits': '38', 'decimal_places': '0'}),
            'usage_min': ('snf_django.lib.db.fields.IntDecimalField', [], {'default': '0', 'max_digits': '38', 'decimal_places': '0'})
        },
        'quotaholder_app.provision': {
            'Meta': {'object_name': 'Provision'},
            'holder': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'resource': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'serial': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provisions'", 'to': "orm['quotaholder_app.Commission']"}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'null': 'True'})
        },
        'quotaholder_app.provisionlog': {
            'Meta': {'object_name': 'ProvisionLog'},
            'delta_quantity': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'holder': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issue_time': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'limit': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'log_time': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'resource': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'serial': ('django.db.models.fields.BigIntegerField', [], {}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'null': 'True'}),
            'usage_max': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'usage_min': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'})
        }
    }

    complete_apps = ['quotaholder_app']
    symmetrical = True
