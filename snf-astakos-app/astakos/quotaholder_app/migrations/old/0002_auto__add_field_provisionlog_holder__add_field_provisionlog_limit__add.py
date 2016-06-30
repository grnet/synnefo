# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'ProvisionLog.holder'
        db.add_column('quotaholder_app_provisionlog', 'holder', self.gf('django.db.models.fields.CharField')(default='', max_length=4096), keep_default=False)

        # Adding field 'ProvisionLog.limit'
        db.add_column('quotaholder_app_provisionlog', 'limit', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0), keep_default=False)

        # Adding field 'ProvisionLog.usage_min'
        db.add_column('quotaholder_app_provisionlog', 'usage_min', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0), keep_default=False)

        # Adding field 'ProvisionLog.usage_max'
        db.add_column('quotaholder_app_provisionlog', 'usage_max', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0), keep_default=False)

        # Adding field 'Holding.holder'
        db.add_column('quotaholder_app_holding', 'holder', self.gf('django.db.models.fields.CharField')(default='', max_length=4096, db_index=True), keep_default=False)

        # Adding field 'Holding.source'
        db.add_column('quotaholder_app_holding', 'source', self.gf('django.db.models.fields.CharField')(max_length=4096, null=True), keep_default=False)

        # Adding field 'Holding.limit'
        db.add_column('quotaholder_app_holding', 'limit', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0), keep_default=False)

        # Adding field 'Holding.usage_min'
        db.add_column('quotaholder_app_holding', 'usage_min', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0), keep_default=False)

        # Adding field 'Holding.usage_max'
        db.add_column('quotaholder_app_holding', 'usage_max', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0), keep_default=False)

        # Adding field 'Provision.holder'
        db.add_column('quotaholder_app_provision', 'holder', self.gf('django.db.models.fields.CharField')(default='', max_length=4096, db_index=True), keep_default=False)

        # Adding field 'Provision.source'
        db.add_column('quotaholder_app_provision', 'source', self.gf('django.db.models.fields.CharField')(max_length=4096, null=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'ProvisionLog.holder'
        db.delete_column('quotaholder_app_provisionlog', 'holder')

        # Deleting field 'ProvisionLog.limit'
        db.delete_column('quotaholder_app_provisionlog', 'limit')

        # Deleting field 'ProvisionLog.usage_min'
        db.delete_column('quotaholder_app_provisionlog', 'usage_min')

        # Deleting field 'ProvisionLog.usage_max'
        db.delete_column('quotaholder_app_provisionlog', 'usage_max')

        # Deleting field 'Holding.holder'
        db.delete_column('quotaholder_app_holding', 'holder')

        # Deleting field 'Holding.source'
        db.delete_column('quotaholder_app_holding', 'source')

        # Deleting field 'Holding.limit'
        db.delete_column('quotaholder_app_holding', 'limit')

        # Deleting field 'Holding.usage_min'
        db.delete_column('quotaholder_app_holding', 'usage_min')

        # Deleting field 'Holding.usage_max'
        db.delete_column('quotaholder_app_holding', 'usage_max')

        # Deleting field 'Provision.holder'
        db.delete_column('quotaholder_app_provision', 'holder')

        # Deleting field 'Provision.source'
        db.delete_column('quotaholder_app_provision', 'source')


    models = {
        'quotaholder_app.callserial': {
            'Meta': {'unique_together': "(('serial', 'clientkey'),)", 'object_name': 'CallSerial'},
            'clientkey': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'serial': ('django.db.models.fields.BigIntegerField', [], {})
        },
        'quotaholder_app.commission': {
            'Meta': {'object_name': 'Commission'},
            'clientkey': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['quotaholder_app.Entity']"}),
            'issue_time': ('django.db.models.fields.CharField', [], {'default': "'2013-04-29T09:16:51.7763'", 'max_length': '24'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'null': 'True'}),
            'serial': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'quotaholder_app.entity': {
            'Meta': {'object_name': 'Entity'},
            'entity': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entities'", 'to': "orm['quotaholder_app.Entity']"})
        },
        'quotaholder_app.holder': {
            'Meta': {'object_name': 'Holder'},
            'attribute': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'primary_key': 'True'}),
            'intval': ('django.db.models.fields.BigIntegerField', [], {}),
            'strval': ('django.db.models.fields.CharField', [], {'max_length': '4096'})
        },
        'quotaholder_app.holding': {
            'Meta': {'unique_together': "(('entity', 'resource'),)", 'object_name': 'Holding'},
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['quotaholder_app.Entity']"}),
            'exported': ('snf_django.lib.db.fields.IntDecimalField', [], {'default': '0', 'max_digits': '38', 'decimal_places': '0'}),
            'exporting': ('snf_django.lib.db.fields.IntDecimalField', [], {'default': '0', 'max_digits': '38', 'decimal_places': '0'}),
            'flags': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'holder': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imported': ('snf_django.lib.db.fields.IntDecimalField', [], {'default': '0', 'max_digits': '38', 'decimal_places': '0'}),
            'importing': ('snf_django.lib.db.fields.IntDecimalField', [], {'default': '0', 'max_digits': '38', 'decimal_places': '0'}),
            'limit': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'policy': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['quotaholder_app.Policy']"}),
            'released': ('snf_django.lib.db.fields.IntDecimalField', [], {'default': '0', 'max_digits': '38', 'decimal_places': '0'}),
            'releasing': ('snf_django.lib.db.fields.IntDecimalField', [], {'default': '0', 'max_digits': '38', 'decimal_places': '0'}),
            'resource': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'returned': ('snf_django.lib.db.fields.IntDecimalField', [], {'default': '0', 'max_digits': '38', 'decimal_places': '0'}),
            'returning': ('snf_django.lib.db.fields.IntDecimalField', [], {'default': '0', 'max_digits': '38', 'decimal_places': '0'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'null': 'True'}),
            'usage_max': ('snf_django.lib.db.fields.IntDecimalField', [], {'default': '0', 'max_digits': '38', 'decimal_places': '0'}),
            'usage_min': ('snf_django.lib.db.fields.IntDecimalField', [], {'default': '0', 'max_digits': '38', 'decimal_places': '0'})
        },
        'quotaholder_app.policy': {
            'Meta': {'object_name': 'Policy'},
            'capacity': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'export_limit': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'import_limit': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'policy': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'primary_key': 'True'}),
            'quantity': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'})
        },
        'quotaholder_app.provision': {
            'Meta': {'object_name': 'Provision'},
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['quotaholder_app.Entity']"}),
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
            'source': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'source_capacity': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'source_export_limit': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'source_exported': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'source_import_limit': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'source_imported': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'source_quantity': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'source_released': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'source_returned': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'target': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'target_capacity': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'target_export_limit': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'target_exported': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'target_import_limit': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'target_imported': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'target_quantity': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'target_released': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'target_returned': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'usage_max': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'usage_min': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'})
        }
    }

    complete_apps = ['quotaholder_app']
