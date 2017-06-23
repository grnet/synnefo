# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from django.db.models import F

class Migration(DataMigration):

    def forwards(self, orm):
        # Delete service holdings
        orm.Holding.objects.filter(
            entity__in=['cyclades', 'pithos+']).delete()

        # Populate new fields
        holdings = orm.Holding.objects.all().select_related()
        holdings.update(source="system")
        holdings.update(usage_min=F('imported')-F('exporting')+
                        F('returned')-F('releasing'))
        holdings.update(usage_max=F('importing')-F('exported')+
                        F('returning')-F('released'))

        for holding in holdings:
            holding.holder = holding.entity.entity
            holding.limit = holding.policy.capacity
            holding.save()

        h_pith = orm.Holding.objects.filter(resource="pithos+.diskspace")
        h_pith.update(resource="pithos.diskspace")

        provisions = orm.Provision.objects.all().select_related()
        provisions.update(source="system")

        for provision in provisions:
            provision.holder = provision.serial.entity.entity
            provision.save()

        p_pith = orm.Provision.objects.filter(resource="pithos+.diskspace")
        p_pith.update(resource="pithos.diskspace")

        plogs = orm.ProvisionLog.objects.all()
        plogs.update(holder=F('target'))
        plogs.update(source="system")
        plogs.update(limit=F('target_capacity'))
        plogs.update(usage_min=F('target_imported')-F('target_exported')+
                    F('target_returned')-F('target_released'))
        plogs.update(usage_max=F('usage_min'))

        pl_pith = orm.ProvisionLog.objects.filter(resource="pithos+.diskspace")
        pl_pith.update(resource="pithos.diskspace")


    def backwards(self, orm):
        "Write your backwards methods here."


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
            'issue_time': ('django.db.models.fields.CharField', [], {'default': "'2013-04-29T09:17:31.6951'", 'max_length': '24'}),
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
