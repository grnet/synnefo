# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Holder'
        db.create_table('django_backend_holder', (
            ('attribute', self.gf('django.db.models.fields.CharField')(max_length=72, primary_key=True)),
            ('intval', self.gf('django.db.models.fields.BigIntegerField')()),
            ('strval', self.gf('django.db.models.fields.CharField')(max_length=72)),
        ))
        db.send_create_signal('django_backend', ['Holder'])

        # Adding model 'Entity'
        db.create_table('django_backend_entity', (
            ('entity', self.gf('django.db.models.fields.CharField')(max_length=72, primary_key=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(related_name='entities', to=orm['django_backend.Entity'])),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=72)),
        ))
        db.send_create_signal('django_backend', ['Entity'])

        # Adding model 'Policy'
        db.create_table('django_backend_policy', (
            ('policy', self.gf('django.db.models.fields.CharField')(max_length=72, primary_key=True)),
            ('quantity', self.gf('django.db.models.fields.BigIntegerField')(default=None, null=True)),
            ('capacity', self.gf('django.db.models.fields.BigIntegerField')(default=None, null=True)),
            ('import_limit', self.gf('django.db.models.fields.BigIntegerField')(default=None, null=True)),
            ('export_limit', self.gf('django.db.models.fields.BigIntegerField')(default=None, null=True)),
        ))
        db.send_create_signal('django_backend', ['Policy'])

        # Adding model 'Holding'
        db.create_table('django_backend_holding', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('entity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['django_backend.Entity'])),
            ('resource', self.gf('django.db.models.fields.CharField')(max_length=72)),
            ('policy', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['django_backend.Policy'])),
            ('flags', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('imported', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('importing', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('exported', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('exporting', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('returned', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('returning', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('released', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('releasing', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
        ))
        db.send_create_signal('django_backend', ['Holding'])

        # Adding unique constraint on 'Holding', fields ['entity', 'resource']
        db.create_unique('django_backend_holding', ['entity_id', 'resource'])

        # Adding model 'Commission'
        db.create_table('django_backend_commission', (
            ('serial', self.gf('django.db.models.fields.BigIntegerField')(default=1, primary_key=True)),
            ('entity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['django_backend.Entity'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=72, null=True)),
            ('clientkey', self.gf('django.db.models.fields.CharField')(max_length=72)),
            ('issue_time', self.gf('django.db.models.fields.CharField')(default='2012-11-09T14:38:00.6122', max_length=24)),
        ))
        db.send_create_signal('django_backend', ['Commission'])

        # Adding model 'Provision'
        db.create_table('django_backend_provision', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('serial', self.gf('django.db.models.fields.related.ForeignKey')(related_name='provisions', to=orm['django_backend.Commission'])),
            ('entity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['django_backend.Entity'])),
            ('resource', self.gf('django.db.models.fields.CharField')(max_length=72)),
            ('quantity', self.gf('django.db.models.fields.BigIntegerField')()),
        ))
        db.send_create_signal('django_backend', ['Provision'])

        # Adding model 'ProvisionLog'
        db.create_table('django_backend_provisionlog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('serial', self.gf('django.db.models.fields.BigIntegerField')()),
            ('source', self.gf('django.db.models.fields.CharField')(max_length=72)),
            ('target', self.gf('django.db.models.fields.CharField')(max_length=72)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=72)),
            ('issue_time', self.gf('django.db.models.fields.CharField')(max_length=24)),
            ('log_time', self.gf('django.db.models.fields.CharField')(max_length=24)),
            ('resource', self.gf('django.db.models.fields.CharField')(max_length=72)),
            ('source_quantity', self.gf('django.db.models.fields.BigIntegerField')(null=True)),
            ('source_capacity', self.gf('django.db.models.fields.BigIntegerField')(null=True)),
            ('source_import_limit', self.gf('django.db.models.fields.BigIntegerField')(null=True)),
            ('source_export_limit', self.gf('django.db.models.fields.BigIntegerField')(null=True)),
            ('source_imported', self.gf('django.db.models.fields.BigIntegerField')()),
            ('source_exported', self.gf('django.db.models.fields.BigIntegerField')()),
            ('source_returned', self.gf('django.db.models.fields.BigIntegerField')()),
            ('source_released', self.gf('django.db.models.fields.BigIntegerField')()),
            ('target_quantity', self.gf('django.db.models.fields.BigIntegerField')(null=True)),
            ('target_capacity', self.gf('django.db.models.fields.BigIntegerField')(null=True)),
            ('target_import_limit', self.gf('django.db.models.fields.BigIntegerField')(null=True)),
            ('target_export_limit', self.gf('django.db.models.fields.BigIntegerField')(null=True)),
            ('target_imported', self.gf('django.db.models.fields.BigIntegerField')()),
            ('target_exported', self.gf('django.db.models.fields.BigIntegerField')()),
            ('target_returned', self.gf('django.db.models.fields.BigIntegerField')()),
            ('target_released', self.gf('django.db.models.fields.BigIntegerField')()),
            ('delta_quantity', self.gf('django.db.models.fields.BigIntegerField')()),
            ('reason', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal('django_backend', ['ProvisionLog'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Holding', fields ['entity', 'resource']
        db.delete_unique('django_backend_holding', ['entity_id', 'resource'])

        # Deleting model 'Holder'
        db.delete_table('django_backend_holder')

        # Deleting model 'Entity'
        db.delete_table('django_backend_entity')

        # Deleting model 'Policy'
        db.delete_table('django_backend_policy')

        # Deleting model 'Holding'
        db.delete_table('django_backend_holding')

        # Deleting model 'Commission'
        db.delete_table('django_backend_commission')

        # Deleting model 'Provision'
        db.delete_table('django_backend_provision')

        # Deleting model 'ProvisionLog'
        db.delete_table('django_backend_provisionlog')


    models = {
        'django_backend.commission': {
            'Meta': {'object_name': 'Commission'},
            'clientkey': ('django.db.models.fields.CharField', [], {'max_length': '72'}),
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_backend.Entity']"}),
            'issue_time': ('django.db.models.fields.CharField', [], {'default': "'2012-11-09T14:38:00.6266'", 'max_length': '24'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '72', 'null': 'True'}),
            'serial': ('django.db.models.fields.BigIntegerField', [], {'default': '2', 'primary_key': 'True'})
        },
        'django_backend.entity': {
            'Meta': {'object_name': 'Entity'},
            'entity': ('django.db.models.fields.CharField', [], {'max_length': '72', 'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '72'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entities'", 'to': "orm['django_backend.Entity']"})
        },
        'django_backend.holder': {
            'Meta': {'object_name': 'Holder'},
            'attribute': ('django.db.models.fields.CharField', [], {'max_length': '72', 'primary_key': 'True'}),
            'intval': ('django.db.models.fields.BigIntegerField', [], {}),
            'strval': ('django.db.models.fields.CharField', [], {'max_length': '72'})
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
            'resource': ('django.db.models.fields.CharField', [], {'max_length': '72'}),
            'returned': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'returning': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
        'django_backend.policy': {
            'Meta': {'object_name': 'Policy'},
            'capacity': ('django.db.models.fields.BigIntegerField', [], {'default': 'None', 'null': 'True'}),
            'export_limit': ('django.db.models.fields.BigIntegerField', [], {'default': 'None', 'null': 'True'}),
            'import_limit': ('django.db.models.fields.BigIntegerField', [], {'default': 'None', 'null': 'True'}),
            'policy': ('django.db.models.fields.CharField', [], {'max_length': '72', 'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.BigIntegerField', [], {'default': 'None', 'null': 'True'})
        },
        'django_backend.provision': {
            'Meta': {'object_name': 'Provision'},
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_backend.Entity']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.BigIntegerField', [], {}),
            'resource': ('django.db.models.fields.CharField', [], {'max_length': '72'}),
            'serial': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provisions'", 'to': "orm['django_backend.Commission']"})
        },
        'django_backend.provisionlog': {
            'Meta': {'object_name': 'ProvisionLog'},
            'delta_quantity': ('django.db.models.fields.BigIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issue_time': ('django.db.models.fields.CharField', [], {'max_length': '24'}),
            'log_time': ('django.db.models.fields.CharField', [], {'max_length': '24'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '72'}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'resource': ('django.db.models.fields.CharField', [], {'max_length': '72'}),
            'serial': ('django.db.models.fields.BigIntegerField', [], {}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '72'}),
            'source_capacity': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'source_export_limit': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'source_exported': ('django.db.models.fields.BigIntegerField', [], {}),
            'source_import_limit': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'source_imported': ('django.db.models.fields.BigIntegerField', [], {}),
            'source_quantity': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'source_released': ('django.db.models.fields.BigIntegerField', [], {}),
            'source_returned': ('django.db.models.fields.BigIntegerField', [], {}),
            'target': ('django.db.models.fields.CharField', [], {'max_length': '72'}),
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
