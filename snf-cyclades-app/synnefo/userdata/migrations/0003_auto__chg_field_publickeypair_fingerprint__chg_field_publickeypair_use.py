# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    needed_by = (
        ("db", "0027_auto__del_legacy_fields"),
    )

    def forwards(self, orm):

        # Changing field 'PublicKeyPair.fingerprint'
        db.alter_column('userdata_publickeypair', 'fingerprint', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True))

        try:
            db.drop_foreign_key('userdata_publickeypair', 'user_id')
        except:
            pass
        # Renaming column for 'PublicKeyPair.user' to match new field type.
        db.rename_column('userdata_publickeypair', 'user_id', 'user')
        # Changing field 'PublicKeyPair.user'
        db.alter_column('userdata_publickeypair', 'user', self.gf('django.db.models.fields.CharField')(max_length=100))

        try:
            # Removing index on 'PublicKeyPair', fields ['user']
            db.delete_index('userdata_publickeypair', ['user_id'])
        except:
            pass


    def backwards(self, orm):

        # Changing field 'PublicKeyPair.fingerprint'
        db.alter_column('userdata_publickeypair', 'fingerprint', self.gf('django.db.models.fields.CharField')(max_length=100))

        # Renaming column for 'PublicKeyPair.user' to match new field type.
        db.rename_column('userdata_publickeypair', 'user', 'user_id')
        # Changing field 'PublicKeyPair.user'
        db.alter_column('userdata_publickeypair', 'user_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['db.SynnefoUser']))

        # Adding index on 'PublicKeyPair', fields ['user']
        db.create_index('userdata_publickeypair', ['user_id'])


    models = {
        'userdata.publickeypair': {
            'Meta': {'object_name': 'PublicKeyPair'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'fingerprint': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['userdata']
