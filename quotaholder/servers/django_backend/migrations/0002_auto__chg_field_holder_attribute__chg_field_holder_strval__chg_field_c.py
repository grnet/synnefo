# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Holder.attribute'
        db.alter_column('django_backend_holder', 'attribute', self.gf('django.db.models.fields.CharField')(max_length=4096, primary_key=True))

        # Changing field 'Holder.strval'
        db.alter_column('django_backend_holder', 'strval', self.gf('django.db.models.fields.CharField')(max_length=4096))

        # Changing field 'Commission.clientkey'
        db.alter_column('django_backend_commission', 'clientkey', self.gf('django.db.models.fields.CharField')(max_length=4096))

        # Changing field 'Commission.name'
        db.alter_column('django_backend_commission', 'name', self.gf('django.db.models.fields.CharField')(max_length=4096, null=True))

        # Changing field 'Holding.resource'
        db.alter_column('django_backend_holding', 'resource', self.gf('django.db.models.fields.CharField')(max_length=4096))

        # Changing field 'Entity.key'
        db.alter_column('django_backend_entity', 'key', self.gf('django.db.models.fields.CharField')(max_length=4096))

        # Changing field 'Entity.entity'
        db.alter_column('django_backend_entity', 'entity', self.gf('django.db.models.fields.CharField')(max_length=4096, primary_key=True))

        # Changing field 'Provision.resource'
        db.alter_column('django_backend_provision', 'resource', self.gf('django.db.models.fields.CharField')(max_length=4096))

        # Changing field 'ProvisionLog.source'
        db.alter_column('django_backend_provisionlog', 'source', self.gf('django.db.models.fields.CharField')(max_length=4096))

        # Changing field 'ProvisionLog.reason'
        db.alter_column('django_backend_provisionlog', 'reason', self.gf('django.db.models.fields.CharField')(max_length=4096))

        # Changing field 'ProvisionLog.log_time'
        db.alter_column('django_backend_provisionlog', 'log_time', self.gf('django.db.models.fields.CharField')(max_length=4096))

        # Changing field 'ProvisionLog.resource'
        db.alter_column('django_backend_provisionlog', 'resource', self.gf('django.db.models.fields.CharField')(max_length=4096))

        # Changing field 'ProvisionLog.name'
        db.alter_column('django_backend_provisionlog', 'name', self.gf('django.db.models.fields.CharField')(max_length=4096))

        # Changing field 'ProvisionLog.issue_time'
        db.alter_column('django_backend_provisionlog', 'issue_time', self.gf('django.db.models.fields.CharField')(max_length=4096))

        # Changing field 'ProvisionLog.target'
        db.alter_column('django_backend_provisionlog', 'target', self.gf('django.db.models.fields.CharField')(max_length=4096))

        # Changing field 'Policy.policy'
        db.alter_column('django_backend_policy', 'policy', self.gf('django.db.models.fields.CharField')(max_length=4096, primary_key=True))


    def backwards(self, orm):
        
        # Changing field 'Holder.attribute'
        db.alter_column('django_backend_holder', 'attribute', self.gf('django.db.models.fields.CharField')(max_length=72, primary_key=True))

        # Changing field 'Holder.strval'
        db.alter_column('django_backend_holder', 'strval', self.gf('django.db.models.fields.CharField')(max_length=72))

        # Changing field 'Commission.clientkey'
        db.alter_column('django_backend_commission', 'clientkey', self.gf('django.db.models.fields.CharField')(max_length=72))

        # Changing field 'Commission.name'
        db.alter_column('django_backend_commission', 'name', self.gf('django.db.models.fields.CharField')(max_length=72, null=True))

        # Changing field 'Holding.resource'
        db.alter_column('django_backend_holding', 'resource', self.gf('django.db.models.fields.CharField')(max_length=72))

        # Changing field 'Entity.key'
        db.alter_column('django_backend_entity', 'key', self.gf('django.db.models.fields.CharField')(max_length=72))

        # Changing field 'Entity.entity'
        db.alter_column('django_backend_entity', 'entity', self.gf('django.db.models.fields.CharField')(max_length=72, primary_key=True))

        # Changing field 'Provision.resource'
        db.alter_column('django_backend_provision', 'resource', self.gf('django.db.models.fields.CharField')(max_length=72))

        # Changing field 'ProvisionLog.source'
        db.alter_column('django_backend_provisionlog', 'source', self.gf('django.db.models.fields.CharField')(max_length=72))

        # Changing field 'ProvisionLog.reason'
        db.alter_column('django_backend_provisionlog', 'reason', self.gf('django.db.models.fields.CharField')(max_length=128))

        # Changing field 'ProvisionLog.log_time'
        db.alter_column('django_backend_provisionlog', 'log_time', self.gf('django.db.models.fields.CharField')(max_length=24))

        # Changing field 'ProvisionLog.resource'
        db.alter_column('django_backend_provisionlog', 'resource', self.gf('django.db.models.fields.CharField')(max_length=72))

        # Changing field 'ProvisionLog.name'
        db.alter_column('django_backend_provisionlog', 'name', self.gf('django.db.models.fields.CharField')(max_length=72))

        # Changing field 'ProvisionLog.issue_time'
        db.alter_column('django_backend_provisionlog', 'issue_time', self.gf('django.db.models.fields.CharField')(max_length=24))

        # Changing field 'ProvisionLog.target'
        db.alter_column('django_backend_provisionlog', 'target', self.gf('django.db.models.fields.CharField')(max_length=72))

        # Changing field 'Policy.policy'
        db.alter_column('django_backend_policy', 'policy', self.gf('django.db.models.fields.CharField')(max_length=72, primary_key=True))


    models = {
        'django_backend.commission': {
            'Meta': {'object_name': 'Commission'},
            'clientkey': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_backend.Entity']"}),
            'issue_time': ('django.db.models.fields.CharField', [], {'default': "'2012-11-09T14:43:11.4905'", 'max_length': '24'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'null': 'True'}),
            'serial': ('django.db.models.fields.BigIntegerField', [], {'default': '5', 'primary_key': 'True'})
        },
        'django_backend.entity': {
            'Meta': {'object_name': 'Entity'},
            'entity': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entities'", 'to': "orm['django_backend.Entity']"})
        },
        'django_backend.holder': {
            'Meta': {'object_name': 'Holder'},
            'attribute': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'primary_key': 'True'}),
            'intval': ('django.db.models.fields.BigIntegerField', [], {}),
            'strval': ('django.db.models.fields.CharField', [], {'max_length': '4096'})
        },
        'django_backend.holding': {
            'Meta': {'unique_together': "(('entity', 'resource'),)", 'object_name': 'Holding'},
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_backend.Entity']"}),
            'exported': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'exporting': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'flags': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imported': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'importing': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'policy': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_backend.Policy']"}),
            'released': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'releasing': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'resource': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'returned': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'returning': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
        'django_backend.policy': {
            'Meta': {'object_name': 'Policy'},
            'capacity': ('django.db.models.fields.BigIntegerField', [], {'default': 'None', 'null': 'True'}),
            'export_limit': ('django.db.models.fields.BigIntegerField', [], {'default': 'None', 'null': 'True'}),
            'import_limit': ('django.db.models.fields.BigIntegerField', [], {'default': 'None', 'null': 'True'}),
            'policy': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.BigIntegerField', [], {'default': 'None', 'null': 'True'})
        },
        'django_backend.provision': {
            'Meta': {'object_name': 'Provision'},
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_backend.Entity']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.BigIntegerField', [], {}),
            'resource': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'serial': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provisions'", 'to': "orm['django_backend.Commission']"})
        },
        'django_backend.provisionlog': {
            'Meta': {'object_name': 'ProvisionLog'},
            'delta_quantity': ('django.db.models.fields.BigIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issue_time': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'log_time': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'resource': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'serial': ('django.db.models.fields.BigIntegerField', [], {}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'source_capacity': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'source_export_limit': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'source_exported': ('django.db.models.fields.BigIntegerField', [], {}),
            'source_import_limit': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'source_imported': ('django.db.models.fields.BigIntegerField', [], {}),
            'source_quantity': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'source_released': ('django.db.models.fields.BigIntegerField', [], {}),
            'source_returned': ('django.db.models.fields.BigIntegerField', [], {}),
            'target': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'target_capacity': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'target_export_limit': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'target_exported': ('django.db.models.fields.BigIntegerField', [], {}),
            'target_import_limit': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'target_imported': ('django.db.models.fields.BigIntegerField', [], {}),
            'target_quantity': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'target_released': ('django.db.models.fields.BigIntegerField', [], {}),
            'target_returned': ('django.db.models.fields.BigIntegerField', [], {})
        }
    }

    complete_apps = ['django_backend']
