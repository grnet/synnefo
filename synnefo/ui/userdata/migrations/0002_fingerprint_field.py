# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'PublicKeyPair.fingerprint'
        db.add_column('userdata_publickeypair', 'fingerprint', self.gf('django.db.models.fields.CharField')(default='', max_length=100), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'PublicKeyPair.fingerprint'
        db.delete_column('userdata_publickeypair', 'fingerprint')


    models = {
        'db.synnefouser': {
            'Meta': {'object_name': 'SynnefoUser'},
            'auth_token': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'auth_token_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'auth_token_expires': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'credit': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_invitations': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'realname': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'ACTIVE'", 'max_length': '30'}),
            'tmp_auth_token': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'tmp_auth_token_expires': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'uniq': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'userdata.publickeypair': {
            'Meta': {'object_name': 'PublicKeyPair'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'fingerprint': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.SynnefoUser']"})
        }
    }

    complete_apps = ['userdata']
