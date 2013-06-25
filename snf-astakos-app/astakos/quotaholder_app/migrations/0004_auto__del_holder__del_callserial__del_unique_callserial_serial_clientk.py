# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Removing unique constraint on 'Holding', fields ['resource', 'entity']
        db.delete_unique('quotaholder_app_holding', ['resource', 'entity_id'])

        # Removing unique constraint on 'CallSerial', fields ['serial', 'clientkey']
        db.delete_unique('quotaholder_app_callserial', ['serial', 'clientkey'])

        # Deleting model 'Holder'
        db.delete_table('quotaholder_app_holder')

        # Deleting model 'CallSerial'
        db.delete_table('quotaholder_app_callserial')

        # Deleting model 'Entity'
        db.delete_table('quotaholder_app_entity')

        # Deleting model 'Policy'
        db.delete_table('quotaholder_app_policy')

        # Deleting field 'ProvisionLog.target_released'
        db.delete_column('quotaholder_app_provisionlog', 'target_released')

        # Deleting field 'ProvisionLog.target_returned'
        db.delete_column('quotaholder_app_provisionlog', 'target_returned')

        # Deleting field 'ProvisionLog.source_quantity'
        db.delete_column('quotaholder_app_provisionlog', 'source_quantity')

        # Deleting field 'ProvisionLog.target_quantity'
        db.delete_column('quotaholder_app_provisionlog', 'target_quantity')

        # Deleting field 'ProvisionLog.target_exported'
        db.delete_column('quotaholder_app_provisionlog', 'target_exported')

        # Deleting field 'ProvisionLog.target_import_limit'
        db.delete_column('quotaholder_app_provisionlog', 'target_import_limit')

        # Deleting field 'ProvisionLog.target_capacity'
        db.delete_column('quotaholder_app_provisionlog', 'target_capacity')

        # Deleting field 'ProvisionLog.source_capacity'
        db.delete_column('quotaholder_app_provisionlog', 'source_capacity')

        # Deleting field 'ProvisionLog.source_returned'
        db.delete_column('quotaholder_app_provisionlog', 'source_returned')

        # Deleting field 'ProvisionLog.target_export_limit'
        db.delete_column('quotaholder_app_provisionlog', 'target_export_limit')

        # Deleting field 'ProvisionLog.source_released'
        db.delete_column('quotaholder_app_provisionlog', 'source_released')

        # Deleting field 'ProvisionLog.target'
        db.delete_column('quotaholder_app_provisionlog', 'target')

        # Deleting field 'ProvisionLog.source_export_limit'
        db.delete_column('quotaholder_app_provisionlog', 'source_export_limit')

        # Deleting field 'ProvisionLog.source_exported'
        db.delete_column('quotaholder_app_provisionlog', 'source_exported')

        # Deleting field 'ProvisionLog.source_import_limit'
        db.delete_column('quotaholder_app_provisionlog', 'source_import_limit')

        # Deleting field 'ProvisionLog.target_imported'
        db.delete_column('quotaholder_app_provisionlog', 'target_imported')

        # Deleting field 'ProvisionLog.source_imported'
        db.delete_column('quotaholder_app_provisionlog', 'source_imported')

        # Changing field 'ProvisionLog.source'
        db.alter_column('quotaholder_app_provisionlog', 'source', self.gf('django.db.models.fields.CharField')(max_length=4096, null=True))

        # Deleting field 'Commission.entity'
        db.delete_column('quotaholder_app_commission', 'entity_id')

        # Changing field 'Commission.name'
        db.alter_column('quotaholder_app_commission', 'name', self.gf('django.db.models.fields.CharField')(max_length=4096))

        # Deleting field 'Holding.imported'
        db.delete_column('quotaholder_app_holding', 'imported')

        # Deleting field 'Holding.returned'
        db.delete_column('quotaholder_app_holding', 'returned')

        # Deleting field 'Holding.released'
        db.delete_column('quotaholder_app_holding', 'released')

        # Deleting field 'Holding.releasing'
        db.delete_column('quotaholder_app_holding', 'releasing')

        # Deleting field 'Holding.entity'
        db.delete_column('quotaholder_app_holding', 'entity_id')

        # Deleting field 'Holding.policy'
        db.delete_column('quotaholder_app_holding', 'policy_id')

        # Deleting field 'Holding.flags'
        db.delete_column('quotaholder_app_holding', 'flags')

        # Deleting field 'Holding.exported'
        db.delete_column('quotaholder_app_holding', 'exported')

        # Deleting field 'Holding.exporting'
        db.delete_column('quotaholder_app_holding', 'exporting')

        # Deleting field 'Holding.importing'
        db.delete_column('quotaholder_app_holding', 'importing')

        # Deleting field 'Holding.returning'
        db.delete_column('quotaholder_app_holding', 'returning')

        # Adding unique constraint on 'Holding', fields ['resource', 'source', 'holder']
        db.create_unique('quotaholder_app_holding', ['resource', 'source', 'holder'])

        # Deleting field 'Provision.entity'
        db.delete_column('quotaholder_app_provision', 'entity_id')


    def backwards(self, orm):
        
        # Removing unique constraint on 'Holding', fields ['resource', 'source', 'holder']
        db.delete_unique('quotaholder_app_holding', ['resource', 'source', 'holder'])

        # Adding model 'Holder'
        db.create_table('quotaholder_app_holder', (
            ('attribute', self.gf('django.db.models.fields.CharField')(max_length=4096, primary_key=True)),
            ('strval', self.gf('django.db.models.fields.CharField')(max_length=4096)),
            ('intval', self.gf('django.db.models.fields.BigIntegerField')()),
        ))
        db.send_create_signal('quotaholder_app', ['Holder'])

        # Adding model 'CallSerial'
        db.create_table('quotaholder_app_callserial', (
            ('serial', self.gf('django.db.models.fields.BigIntegerField')()),
            ('clientkey', self.gf('django.db.models.fields.CharField')(max_length=4096)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('quotaholder_app', ['CallSerial'])

        # Adding unique constraint on 'CallSerial', fields ['serial', 'clientkey']
        db.create_unique('quotaholder_app_callserial', ['serial', 'clientkey'])

        # Adding model 'Entity'
        db.create_table('quotaholder_app_entity', (
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(related_name='entities', to=orm['quotaholder_app.Entity'])),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=4096)),
            ('entity', self.gf('django.db.models.fields.CharField')(max_length=4096, primary_key=True)),
        ))
        db.send_create_signal('quotaholder_app', ['Entity'])

        # Adding model 'Policy'
        db.create_table('quotaholder_app_policy', (
            ('capacity', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('import_limit', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('export_limit', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
            ('policy', self.gf('django.db.models.fields.CharField')(max_length=4096, primary_key=True)),
            ('quantity', self.gf('snf_django.lib.db.fields.IntDecimalField')(max_digits=38, decimal_places=0)),
        ))
        db.send_create_signal('quotaholder_app', ['Policy'])

        # User chose to not deal with backwards NULL issues for 'ProvisionLog.target_released'
        raise RuntimeError("Cannot reverse this migration. 'ProvisionLog.target_released' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'ProvisionLog.target_returned'
        raise RuntimeError("Cannot reverse this migration. 'ProvisionLog.target_returned' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'ProvisionLog.source_quantity'
        raise RuntimeError("Cannot reverse this migration. 'ProvisionLog.source_quantity' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'ProvisionLog.target_quantity'
        raise RuntimeError("Cannot reverse this migration. 'ProvisionLog.target_quantity' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'ProvisionLog.target_exported'
        raise RuntimeError("Cannot reverse this migration. 'ProvisionLog.target_exported' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'ProvisionLog.target_import_limit'
        raise RuntimeError("Cannot reverse this migration. 'ProvisionLog.target_import_limit' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'ProvisionLog.target_capacity'
        raise RuntimeError("Cannot reverse this migration. 'ProvisionLog.target_capacity' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'ProvisionLog.source_capacity'
        raise RuntimeError("Cannot reverse this migration. 'ProvisionLog.source_capacity' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'ProvisionLog.source_returned'
        raise RuntimeError("Cannot reverse this migration. 'ProvisionLog.source_returned' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'ProvisionLog.target_export_limit'
        raise RuntimeError("Cannot reverse this migration. 'ProvisionLog.target_export_limit' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'ProvisionLog.source_released'
        raise RuntimeError("Cannot reverse this migration. 'ProvisionLog.source_released' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'ProvisionLog.target'
        raise RuntimeError("Cannot reverse this migration. 'ProvisionLog.target' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'ProvisionLog.source_export_limit'
        raise RuntimeError("Cannot reverse this migration. 'ProvisionLog.source_export_limit' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'ProvisionLog.source_exported'
        raise RuntimeError("Cannot reverse this migration. 'ProvisionLog.source_exported' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'ProvisionLog.source_import_limit'
        raise RuntimeError("Cannot reverse this migration. 'ProvisionLog.source_import_limit' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'ProvisionLog.target_imported'
        raise RuntimeError("Cannot reverse this migration. 'ProvisionLog.target_imported' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'ProvisionLog.source_imported'
        raise RuntimeError("Cannot reverse this migration. 'ProvisionLog.source_imported' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'ProvisionLog.source'
        raise RuntimeError("Cannot reverse this migration. 'ProvisionLog.source' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'Commission.entity'
        raise RuntimeError("Cannot reverse this migration. 'Commission.entity' and its values cannot be restored.")

        # Changing field 'Commission.name'
        db.alter_column('quotaholder_app_commission', 'name', self.gf('django.db.models.fields.CharField')(max_length=4096, null=True))

        # Adding field 'Holding.imported'
        db.add_column('quotaholder_app_holding', 'imported', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0), keep_default=False)

        # Adding field 'Holding.returned'
        db.add_column('quotaholder_app_holding', 'returned', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0), keep_default=False)

        # Adding field 'Holding.released'
        db.add_column('quotaholder_app_holding', 'released', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0), keep_default=False)

        # Adding field 'Holding.releasing'
        db.add_column('quotaholder_app_holding', 'releasing', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0), keep_default=False)

        # User chose to not deal with backwards NULL issues for 'Holding.entity'
        raise RuntimeError("Cannot reverse this migration. 'Holding.entity' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'Holding.policy'
        raise RuntimeError("Cannot reverse this migration. 'Holding.policy' and its values cannot be restored.")

        # Adding field 'Holding.flags'
        db.add_column('quotaholder_app_holding', 'flags', self.gf('django.db.models.fields.BigIntegerField')(default=0), keep_default=False)

        # Adding field 'Holding.exported'
        db.add_column('quotaholder_app_holding', 'exported', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0), keep_default=False)

        # Adding field 'Holding.exporting'
        db.add_column('quotaholder_app_holding', 'exporting', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0), keep_default=False)

        # Adding field 'Holding.importing'
        db.add_column('quotaholder_app_holding', 'importing', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0), keep_default=False)

        # Adding field 'Holding.returning'
        db.add_column('quotaholder_app_holding', 'returning', self.gf('snf_django.lib.db.fields.IntDecimalField')(default=0, max_digits=38, decimal_places=0), keep_default=False)

        # Adding unique constraint on 'Holding', fields ['resource', 'entity']
        db.create_unique('quotaholder_app_holding', ['resource', 'entity_id'])

        # User chose to not deal with backwards NULL issues for 'Provision.entity'
        raise RuntimeError("Cannot reverse this migration. 'Provision.entity' and its values cannot be restored.")


    models = {
        'quotaholder_app.commission': {
            'Meta': {'object_name': 'Commission'},
            'clientkey': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'issue_time': ('django.db.models.fields.CharField', [], {'max_length': '24'}),
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
