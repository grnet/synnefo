# encoding: utf-8

from south.v2 import DataMigration

from astakos.im.settings import SERVICES

import logging

logger = logging.getLogger(__name__)

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."

        try:
            default = orm.AstakosGroup.objects.get(name='default')
        except orm.AstakosGroup.DoesNotExist:
            return

        def create_policies(args):
            sn, dict = args
            url = dict.get('url')
            resources = dict.get('resources') or ()
            s, created = orm.Service.objects.get_or_create(name=sn,
                                                           defaults={'url': url})
            if not created and not s.url:
                s.url = url
            s.save()

            for r in resources:
                try:
                    rn = r.pop('name', '')
                    uplimit = r.pop('uplimit', None)
                    r, created = orm.Resource.objects.get_or_create(
                        service=s,
                        name=rn,
                        defaults=r)
                except Exception, e:
                    print "Cannot create resource ", rn
                    continue

                q, created = orm.AstakosGroupQuota.objects.get_or_create(
                    group=default,
                    resource=r,
                    uplimit=uplimit,
                    limit=0)
        map(create_policies, SERVICES.iteritems())

    def backwards(self, orm):
        try:
            default = orm.AstakosGroup.objects.get(name='default')
        except orm.AstakosGroup.DoesNotExist:
            return

        def destroy_policies(args):
            sn, dict = args
            url = dict.get('url')
            resources = dict.get('resources') or ()
            for r in resources:
                rn = r.get('name', '')
                try:
                    q = orm.AstakosGroupQuota.objects.get(
                        group=default,
                        resource__name=rn)
                    q.delete()
                    q = orm.Resource.objects.get(service__name=sn, name=rn)
                    q.delete()
                except Exception, e:
                    print "Cannot create resource ", rn
                    continue

        map(destroy_policies, SERVICES.iteritems())

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'im.additionalmail': {
            'Meta': {'object_name': 'AdditionalMail'},
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosUser']"})
        },
        'im.approvalterms': {
            'Meta': {'object_name': 'ApprovalTerms'},
            'date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 11, 5, 12, 47, 39, 465319)', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'im.astakosgroup': {
            'Meta': {'object_name': 'AstakosGroup', '_ormbases': ['auth.Group']},
            'approval_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 11, 5, 12, 47, 39, 456067)'}),
            'desc': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'estimated_participants': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'expiration_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'group_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.Group']", 'unique': 'True', 'primary_key': 'True'}),
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'issue_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'kind': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.GroupKind']"}),
            'max_participants': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'moderation_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'policy': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['im.Resource']", 'null': 'True', 'through': "orm['im.AstakosGroupQuota']", 'blank': 'True'})
        },
        'im.astakosgroupquota': {
            'Meta': {'unique_together': "(('resource', 'group'),)", 'object_name': 'AstakosGroupQuota'},
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosGroup']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'limit': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Resource']"}),
            'uplimit': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'})
        },
        'im.astakosuser': {
            'Meta': {'unique_together': "(('provider', 'third_party_identifier'),)", 'object_name': 'AstakosUser', '_ormbases': ['auth.User']},
            'activation_sent': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'affiliation': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'astakos_groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['im.AstakosGroup']", 'symmetrical': 'False', 'through': "orm['im.Membership']", 'blank': 'True'}),
            'auth_token': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'auth_token_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'auth_token_expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'date_signed_terms': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'disturbed_quota': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'email_verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_credits': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_signed_terms': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'invitations': ('django.db.models.fields.IntegerField', [], {'default': '100'}),
            'is_verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'level': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'owner': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'owner'", 'null': 'True', 'to': "orm['im.AstakosGroup']"}),
            'policy': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['im.Resource']", 'null': 'True', 'through': "orm['im.AstakosUserQuota']", 'symmetrical': 'False'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'third_party_identifier': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {}),
            'user_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        },
        'im.astakosuserquota': {
            'Meta': {'unique_together': "(('resource', 'user'),)", 'object_name': 'AstakosUserQuota'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'limit': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Resource']"}),
            'uplimit': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosUser']"})
        },
        'im.emailchange': {
            'Meta': {'object_name': 'EmailChange'},
            'activation_key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'new_email_address': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'requested_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 11, 5, 12, 47, 39, 466946)'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'emailchange_user'", 'unique': 'True', 'to': "orm['im.AstakosUser']"})
        },
        'im.groupkind': {
            'Meta': {'object_name': 'GroupKind'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'})
        },
        'im.invitation': {
            'Meta': {'object_name': 'Invitation'},
            'code': ('django.db.models.fields.BigIntegerField', [], {'db_index': 'True'}),
            'consumed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inviter': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'invitations_sent'", 'null': 'True', 'to': "orm['im.AstakosUser']"}),
            'is_consumed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'realname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'im.membership': {
            'Meta': {'unique_together': "(('person', 'group'),)", 'object_name': 'Membership'},
            'date_joined': ('django.db.models.fields.DateField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'date_requested': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime(2012, 11, 5, 12, 47, 39, 462857)', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosGroup']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosUser']"})
        },
        'im.resource': {
            'Meta': {'object_name': 'Resource'},
            'desc': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'group': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meta': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['im.ResourceMetadata']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Service']"}),
            'unit': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'})
        },
        'im.resourcemetadata': {
            'Meta': {'object_name': 'ResourceMetadata'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'im.service': {
            'Meta': {'object_name': 'Service'},
            'auth_token': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'auth_token_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'auth_token_expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'icon': ('django.db.models.fields.FilePathField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'url': ('django.db.models.fields.FilePathField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['im']
