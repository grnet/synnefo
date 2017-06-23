# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Holder'
        db.create_table('quotaholder_app_holder', (
            ('attribute', self.gf('django.db.models.fields.CharField')(max_length=4096, primary_key=True)),
            ('intval', self.gf('django.db.models.fields.BigIntegerField')()),
            ('strval', self.gf('django.db.models.fields.CharField')(max_length=4096)),
        ))
        db.send_create_signal('quotaholder_app', ['Holder'])

        # Adding model 'Entity'
        db.create_table('quotaholder_app_entity', (
            ('entity', self.gf('django.db.models.fields.CharField')(max_length=4096, primary_key=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(related_name='entities', to=orm['quotaholder_app.Entity'])),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=4096)),
        ))
        db.send_create_signal('quotaholder_app', ['Entity'])

        # Adding model 'Policy'
        db.create_table('quotaholder_app_policy', (
            ('policy', self.gf('django.db.models.fields.CharField')(max_length=4096, primary_key=True)),
            ('quantity', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('capacity', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('import_limit', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('export_limit', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
        ))
        db.send_create_signal('quotaholder_app', ['Policy'])

        # Adding model 'Holding'
        db.create_table('quotaholder_app_holding', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('entity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['quotaholder_app.Entity'])),
            ('resource', self.gf('django.db.models.fields.CharField')(max_length=4096)),
            ('policy', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['quotaholder_app.Policy'])),
            ('flags', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('imported', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0)),
            ('importing', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0)),
            ('exported', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0)),
            ('exporting', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0)),
            ('returned', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0)),
            ('returning', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0)),
            ('released', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0)),
            ('releasing', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0)),
        ))
        db.send_create_signal('quotaholder_app', ['Holding'])

        # Adding unique constraint on 'Holding', fields ['entity', 'resource']
        db.create_unique('quotaholder_app_holding', ['entity_id', 'resource'])

        # Adding model 'Commission'
        db.create_table('quotaholder_app_commission', (
            ('serial', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('entity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['quotaholder_app.Entity'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=4096, null=True)),
            ('clientkey', self.gf('django.db.models.fields.CharField')(max_length=4096)),
            ('issue_time', self.gf('django.db.models.fields.CharField')(default='2013-04-26T11:03:12.0078', max_length=24)),
        ))
        db.send_create_signal('quotaholder_app', ['Commission'])

        # Adding model 'Provision'
        db.create_table('quotaholder_app_provision', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('serial', self.gf('django.db.models.fields.related.ForeignKey')(related_name='provisions', to=orm['quotaholder_app.Commission'])),
            ('entity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['quotaholder_app.Entity'])),
            ('resource', self.gf('django.db.models.fields.CharField')(max_length=4096)),
            ('quantity', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
        ))
        db.send_create_signal('quotaholder_app', ['Provision'])

        # Adding model 'ProvisionLog'
        db.create_table('quotaholder_app_provisionlog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('serial', self.gf('django.db.models.fields.BigIntegerField')()),
            ('source', self.gf('django.db.models.fields.CharField')(max_length=4096)),
            ('target', self.gf('django.db.models.fields.CharField')(max_length=4096)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=4096)),
            ('issue_time', self.gf('django.db.models.fields.CharField')(max_length=4096)),
            ('log_time', self.gf('django.db.models.fields.CharField')(max_length=4096)),
            ('resource', self.gf('django.db.models.fields.CharField')(max_length=4096)),
            ('source_quantity', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('source_capacity', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('source_import_limit', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('source_export_limit', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('source_imported', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('source_exported', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('source_returned', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('source_released', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('target_quantity', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('target_capacity', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('target_import_limit', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('target_export_limit', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('target_imported', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('target_exported', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('target_returned', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('target_released', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('delta_quantity', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('reason', self.gf('django.db.models.fields.CharField')(max_length=4096)),
        ))
        db.send_create_signal('quotaholder_app', ['ProvisionLog'])

        # Adding model 'CallSerial'
        db.create_table('quotaholder_app_callserial', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('serial', self.gf('django.db.models.fields.BigIntegerField')()),
            ('clientkey', self.gf('django.db.models.fields.CharField')(max_length=4096)),
        ))
        db.send_create_signal('quotaholder_app', ['CallSerial'])

        # Adding unique constraint on 'CallSerial', fields ['serial', 'clientkey']
        db.create_unique('quotaholder_app_callserial', ['serial', 'clientkey'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'CallSerial', fields ['serial', 'clientkey']
        db.delete_unique('quotaholder_app_callserial', ['serial', 'clientkey'])

        # Removing unique constraint on 'Holding', fields ['entity', 'resource']
        db.delete_unique('quotaholder_app_holding', ['entity_id', 'resource'])

        # Deleting model 'Holder'
        db.delete_table('quotaholder_app_holder')

        # Deleting model 'Entity'
        db.delete_table('quotaholder_app_entity')

        # Deleting model 'Policy'
        db.delete_table('quotaholder_app_policy')

        # Deleting model 'Holding'
        db.delete_table('quotaholder_app_holding')

        # Deleting model 'Commission'
        db.delete_table('quotaholder_app_commission')

        # Deleting model 'Provision'
        db.delete_table('quotaholder_app_provision')

        # Deleting model 'ProvisionLog'
        db.delete_table('quotaholder_app_provisionlog')

        # Deleting model 'CallSerial'
        db.delete_table('quotaholder_app_callserial')


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
            'issue_time': ('django.db.models.fields.CharField', [], {'default': "'2013-04-26T11:03:12.0120'", 'max_length': '24'}),
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
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imported': ('snf_django.lib.db.fields.IntDecimalField', [], {'default': '0', 'max_digits': '38', 'decimal_places': '0'}),
            'importing': ('snf_django.lib.db.fields.IntDecimalField', [], {'default': '0', 'max_digits': '38', 'decimal_places': '0'}),
            'policy': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['quotaholder_app.Policy']"}),
            'released': ('snf_django.lib.db.fields.IntDecimalField', [], {'default': '0', 'max_digits': '38', 'decimal_places': '0'}),
            'releasing': ('snf_django.lib.db.fields.IntDecimalField', [], {'default': '0', 'max_digits': '38', 'decimal_places': '0'}),
            'resource': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'returned': ('snf_django.lib.db.fields.IntDecimalField', [], {'default': '0', 'max_digits': '38', 'decimal_places': '0'}),
            'returning': ('snf_django.lib.db.fields.IntDecimalField', [], {'default': '0', 'max_digits': '38', 'decimal_places': '0'})
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
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'resource': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'serial': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provisions'", 'to': "orm['quotaholder_app.Commission']"})
        },
        'quotaholder_app.provisionlog': {
            'Meta': {'object_name': 'ProvisionLog'},
            'delta_quantity': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issue_time': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
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
            'target_returned': ('snf_django.lib.db.fields.IntDecimalField', [], {'max_digits': '38', 'decimal_places': '0'})
        }
    }

    complete_apps = ['quotaholder_app']
