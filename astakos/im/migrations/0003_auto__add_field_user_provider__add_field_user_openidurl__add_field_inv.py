# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'User.provider'
        db.add_column('im_user', 'provider', self.gf('django.db.models.fields.CharField')(default='', max_length=255), keep_default=False)

        # Adding field 'User.openidurl'
        db.add_column('im_user', 'openidurl', self.gf('django.db.models.fields.CharField')(default='', max_length=255), keep_default=False)

        # Adding field 'Invitation.is_consumed'
        db.add_column('im_invitation', 'is_consumed', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)

        # Adding field 'Invitation.consumed'
        db.add_column('im_invitation', 'consumed', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'User.provider'
        db.delete_column('im_user', 'provider')

        # Deleting field 'User.openidurl'
        db.delete_column('im_user', 'openidurl')

        # Deleting field 'Invitation.is_consumed'
        db.delete_column('im_invitation', 'is_consumed')

        # Deleting field 'Invitation.consumed'
        db.delete_column('im_invitation', 'consumed')


    models = {
        'im.invitation': {
            'Meta': {'object_name': 'Invitation'},
            'accepted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'code': ('django.db.models.fields.BigIntegerField', [], {'db_index': 'True'}),
            'consumed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inviter': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'invitations_sent'", 'null': 'True', 'to': "orm['im.User']"}),
            'is_accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_consumed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'realname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uniq': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'im.user': {
            'Meta': {'object_name': 'User'},
            'affiliation': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'auth_token': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'auth_token_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'auth_token_expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {}),
            'email': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invitations': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'is_admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'level': ('django.db.models.fields.IntegerField', [], {'default': '4'}),
            'openidurl': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'provider': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'realname': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '16'}),
            'uniq': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {})
        }
    }

    complete_apps = ['im']
