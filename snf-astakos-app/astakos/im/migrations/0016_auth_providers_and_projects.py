# encoding: utf-8
import datetime
import uuid

from south.db import db
from south.v2 import DataMigration
from django.db import models
from django.core.validators import email_re

from django.conf import settings

class Migration(DataMigration):

    def forwards(self, orm):
        # valid activation_sent/email_verified
        for user in orm.AstakosUser.objects.all():
            if user.is_active:
                if not user.activation_sent:
                    user.activation_sent = datetime.datetime.now()
                    user.email_verified = True
                    user.save()

            while not user.uuid:
                uuid_val =  str(uuid.uuid4())
                try:
                    orm.AstakosUser.objects.get(uuid=uuid_val)
                except orm.AstakosUser.DoesNotExist, e:
                    user.uuid = uuid_val
                    user.save()

        # migrate to auth providers
        for user in orm.AstakosUser.objects.all():
            if user.provider and user.provider != 'local':
                orm.AstakosUserAuthProvider.objects.create(user=user,
                                                           module=user.provider,
                                                           identifier=user.third_party_identifier)
            else:
                orm.AstakosUserAuthProvider.objects.create(user=user,
                                                           module='local',
                                                           auth_backend='astakos')

            user.save()

        # migrate duplicate emails
        to_remove = getattr(settings,
                            'ASTAKOS_MIGRATION_0045_DELETE_DUPLICATE_USER_IDS',
                            [])
        for pk in to_remove:
            try:
                u = orm.AstakosUser.objects.get(pk=int(pk))
                print "Removing user: %s (%d)" % (u.email, u.pk)
            except Exception:
                msg = "You requested user with id %s to be removed but such user doesn't exist in database" % str(pk)
                raise Exception(msg)

            if orm.AstakosUser.objects.filter(email__iexact=u.email).count() == 1:
                msg = ("You requested user with duplicate email %s and id (%d) to"
                " be removed, but it seems that only one user exists with this"
                " email in the database.") % (u.email , pk)
                raise Exception(msg)
            else:
                orm.AstakosUser.objects.filter(pk=int(pk)).delete()

        for u in orm.AstakosUser.objects.all():
            if orm.AstakosUser.objects.filter(email__iexact=u.email).count() > 1:
                existing = orm.AstakosUser.objects.filter(
                                email__iexact=u.email)
                print "Duplicate email found in database"
                for e in existing:
                    print "%d: %s (is_active: %s)" % (e.pk, e.email, e.is_active)
                keep = input("Select which user id you want to BE PRESERVED in the database: ")
                if keep:
                    for e in existing.exclude(pk=int(keep)):
                        e.delete()
                else:
                    raise Exception("Email %s is not unique %r. Please resolve conflicts and run migrate again." % (u.email,
                                                                 existing))
            u = orm.AstakosUser.objects.get(email__iexact=u.email)
            save = False
            if not email_re.match(u.username):
                u.username = u.email.lower()
                save = True
            if save:
                u.save()


    def backwards(self, orm):
        # set third_party_identifier
        for user in orm.AstakosUser.objects.all():
            for auth_provider in user.auth_providers.all():
                user.provider = auth_provider.module
                user.third_party_identifier = auth_provider.identifier

            user.save()

        # reset usernames
        for u in orm.AstakosUser.objects.all():
            u.uuid = None
            u.auth_providers.all().delete()
            if email_re.match(u.username):
                username = None
                while not username:
                    username_val = uuid.uuid4().hex[:30]
                    try:
                        orm.AstakosUser.objects.get(username = username_val)
                    except orm.AstakosUser.DoesNotExist, e:
                        username = username_val
                u.username = username
            u.save()


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
            'date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 1, 11, 14, 22, 49, 523700)', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'im.astakosuser': {
            'Meta': {'object_name': 'AstakosUser', '_ormbases': ['auth.User']},
            'activation_sent': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'affiliation': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'auth_token': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'auth_token_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'auth_token_expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'date_signed_terms': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'disturbed_quota': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'email_verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_credits': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_signed_terms': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'invitations': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'is_verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'level': ('django.db.models.fields.IntegerField', [], {'default': '4'}),
            'policy': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['im.Resource']", 'null': 'True', 'through': "orm['im.AstakosUserQuota']", 'symmetrical': 'False'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'third_party_identifier': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {}),
            'user_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True', 'primary_key': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '255', 'unique': 'True', 'null': 'True'})
        },
        'im.astakosuserauthprovider': {
            'Meta': {'ordering': "('module', 'created')", 'unique_together': "(('identifier', 'module', 'user'),)", 'object_name': 'AstakosUserAuthProvider'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'affiliation': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'auth_backend': ('django.db.models.fields.CharField', [], {'default': "'astakos'", 'max_length': '255'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'info_data': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'module': ('django.db.models.fields.CharField', [], {'default': "'local'", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'auth_providers'", 'to': "orm['im.AstakosUser']"})
        },
        'im.astakosuserquota': {
            'Meta': {'unique_together': "(('resource', 'user'),)", 'object_name': 'AstakosUserQuota'},
            'capacity': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'export_limit': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_limit': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'quantity': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Resource']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosUser']"})
        },
        'im.chain': {
            'Meta': {'object_name': 'Chain'},
            'chain': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'im.emailchange': {
            'Meta': {'object_name': 'EmailChange'},
            'activation_key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'new_email_address': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'requested_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 1, 11, 14, 22, 49, 524502)'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'emailchanges'", 'unique': 'True', 'to': "orm['im.AstakosUser']"})
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
        'im.pendingthirdpartyuser': {
            'Meta': {'unique_together': "(('provider', 'third_party_identifier'),)", 'object_name': 'PendingThirdPartyUser'},
            'affiliation': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'third_party_identifier': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'im.project': {
            'Meta': {'object_name': 'Project'},
            'application': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'project'", 'unique': 'True', 'to': "orm['im.ProjectApplication']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {}),
            'deactivation_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'deactivation_reason': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'is_modified': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'last_approval_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['im.AstakosUser']", 'through': "orm['im.ProjectMembership']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80', 'db_index': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1', 'db_index': 'True'})
        },
        'im.projectapplication': {
            'Meta': {'unique_together': "(('chain', 'id'),)", 'object_name': 'ProjectApplication'},
            'applicant': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects_applied'", 'to': "orm['im.AstakosUser']"}),
            'chain': ('django.db.models.fields.IntegerField', [], {}),
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issue_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'limit_on_members_number': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'member_join_policy': ('django.db.models.fields.IntegerField', [], {}),
            'member_leave_policy': ('django.db.models.fields.IntegerField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects_owned'", 'to': "orm['im.AstakosUser']"}),
            'precursor_application': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['im.ProjectApplication']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'resource_grants': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['im.Resource']", 'null': 'True', 'through': "orm['im.ProjectResourceGrant']", 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'im.projectmembership': {
            'Meta': {'unique_together': "(('person', 'project'),)", 'object_name': 'ProjectMembership'},
            'acceptance_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'db_index': 'True'}),
            'application': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'memberships'", 'null': 'True', 'to': "orm['im.ProjectApplication']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'is_pending': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'leave_request_date': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            'pending_application': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'pending_memebrships'", 'null': 'True', 'to': "orm['im.ProjectApplication']"}),
            'pending_serial': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'db_index': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosUser']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Project']"}),
            'request_date': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime(2013, 1, 11, 14, 22, 49, 528323)'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'})
        },
        'im.projectmembershiphistory': {
            'Meta': {'object_name': 'ProjectMembershipHistory'},
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'person': ('django.db.models.fields.BigIntegerField', [], {}),
            'project': ('django.db.models.fields.BigIntegerField', [], {}),
            'reason': ('django.db.models.fields.IntegerField', [], {}),
            'serial': ('django.db.models.fields.BigIntegerField', [], {})
        },
        'im.projectresourcegrant': {
            'Meta': {'unique_together': "(('resource', 'project_application'),)", 'object_name': 'ProjectResourceGrant'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'member_capacity': ('synnefo.lib.db.intdecimalfield.IntDecimalField', [], {'default': '100000000000000000000000000000000L', 'max_digits': '38', 'decimal_places': '0'}),
            'member_export_limit': ('synnefo.lib.db.intdecimalfield.IntDecimalField', [], {'default': '100000000000000000000000000000000L', 'max_digits': '38', 'decimal_places': '0'}),
            'member_import_limit': ('synnefo.lib.db.intdecimalfield.IntDecimalField', [], {'default': '100000000000000000000000000000000L', 'max_digits': '38', 'decimal_places': '0'}),
            'project_application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.ProjectApplication']", 'null': 'True'}),
            'project_capacity': ('synnefo.lib.db.intdecimalfield.IntDecimalField', [], {'default': '100000000000000000000000000000000L', 'max_digits': '38', 'decimal_places': '0'}),
            'project_export_limit': ('synnefo.lib.db.intdecimalfield.IntDecimalField', [], {'default': '100000000000000000000000000000000L', 'max_digits': '38', 'decimal_places': '0'}),
            'project_import_limit': ('synnefo.lib.db.intdecimalfield.IntDecimalField', [], {'default': '100000000000000000000000000000000L', 'max_digits': '38', 'decimal_places': '0'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Resource']"})
        },
        'im.resource': {
            'Meta': {'unique_together': "(('name', 'service'),)", 'object_name': 'Resource'},
            'desc': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'group': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meta': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['im.ResourceMetadata']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Service']"}),
            'unit': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'})
        },
        'im.resourcemetadata': {
            'Meta': {'object_name': 'ResourceMetadata'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'im.serial': {
            'Meta': {'object_name': 'Serial'},
            'serial': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'im.service': {
            'Meta': {'ordering': "('order',)", 'object_name': 'Service'},
            'auth_token': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'auth_token_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'auth_token_expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'icon': ('django.db.models.fields.FilePathField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'url': ('django.db.models.fields.FilePathField', [], {'max_length': '100'})
        },
        'im.sessioncatalog': {
            'Meta': {'object_name': 'SessionCatalog'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'session_key': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sessions'", 'null': 'True', 'to': "orm['im.AstakosUser']"})
        }
    }

    complete_apps = ['im']
