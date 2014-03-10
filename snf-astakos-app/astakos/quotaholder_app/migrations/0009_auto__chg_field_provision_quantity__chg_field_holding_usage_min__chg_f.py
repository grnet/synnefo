# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Provision.quantity'
        db.alter_column('quotaholder_app_provision', 'quantity', self.gf('django.db.models.fields.BigIntegerField')())

        # Changing field 'Holding.usage_min'
        db.alter_column('quotaholder_app_holding', 'usage_min', self.gf('django.db.models.fields.BigIntegerField')())

        # Changing field 'Holding.usage_max'
        db.alter_column('quotaholder_app_holding', 'usage_max', self.gf('django.db.models.fields.BigIntegerField')())

        # Changing field 'Holding.limit'
        db.alter_column('quotaholder_app_holding', 'limit', self.gf('django.db.models.fields.BigIntegerField')())

        # Changing field 'ProvisionLog.usage_max'
        db.alter_column('quotaholder_app_provisionlog', 'usage_max', self.gf('django.db.models.fields.BigIntegerField')())

        # Changing field 'ProvisionLog.delta_quantity'
        db.alter_column('quotaholder_app_provisionlog', 'delta_quantity', self.gf('django.db.models.fields.BigIntegerField')())

        # Changing field 'ProvisionLog.limit'
        db.alter_column('quotaholder_app_provisionlog', 'limit', self.gf('django.db.models.fields.BigIntegerField')())

        # Changing field 'ProvisionLog.usage_min'
        db.alter_column('quotaholder_app_provisionlog', 'usage_min', self.gf('django.db.models.fields.BigIntegerField')())

    def backwards(self, orm):

        # Changing field 'Provision.quantity'
        db.alter_column('quotaholder_app_provision', 'quantity', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0))

        # Changing field 'Holding.usage_min'
        db.alter_column('quotaholder_app_holding', 'usage_min', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0))

        # Changing field 'Holding.usage_max'
        db.alter_column('quotaholder_app_holding', 'usage_max', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0))

        # Changing field 'Holding.limit'
        db.alter_column('quotaholder_app_holding', 'limit', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0))

        # Changing field 'ProvisionLog.usage_max'
        db.alter_column('quotaholder_app_provisionlog', 'usage_max', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0))

        # Changing field 'ProvisionLog.delta_quantity'
        db.alter_column('quotaholder_app_provisionlog', 'delta_quantity', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0))

        # Changing field 'ProvisionLog.limit'
        db.alter_column('quotaholder_app_provisionlog', 'limit', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0))

        # Changing field 'ProvisionLog.usage_min'
        db.alter_column('quotaholder_app_provisionlog', 'usage_min', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0))

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