# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

def _partition_by(f, l):
    d = {}
    for x in l:
        group = f(x)
        group_l = d.get(group, [])
        group_l.append(x)
        d[group] = group_l
    return d

NORMAL = 1
SUSPENDED = 10
TERMINATED = 100
INITIALIZED_STATES = [NORMAL, SUSPENDED, TERMINATED]
ACTUALLY_ACCEPTED = [1, 5]


class Migration(DataMigration):

    depends_on = (
        ("im", "0080_initialized_memberships"),
    )

    def project_holder(self, project):
        return "project:" + project.uuid

    def user_holder(self, user):
        return "user:" + user.uuid

    def find_resource(self, holdings, resource):
        if holdings is None:
            return None
        hs = [h for h in holdings if h.resource == resource]
        assert len(hs) < 2
        if not hs:
            return None
        h = hs[0]
        return (h.usage_min, h.usage_max)

    def forwards(self, orm):
        AstakosUser = orm["im.astakosuser"]
        users = AstakosUser.objects.filter(moderated=True, is_rejected=False)
        base_projects = {}
        for user in users:
            base_projects[user.base_project_id] = user

        holdings = orm.Holding.objects.all()
        holdings = _partition_by(lambda h: h.holder, holdings)

        Project = orm["im.project"]
        projects = Project.objects.filter(state__in=INITIALIZED_STATES)

        ProjectResourceQuota = orm["im.projectresourcequota"]
        objs = ProjectResourceQuota.objects.select_related("resource")
        grants_l = objs.all()
        grants_d = _partition_by(lambda g: g.project_id, grants_l)

        # Memberships
        ProjectMembership = orm["im.projectmembership"]
        objs = ProjectMembership.objects.select_related("person", "project")
        memberships_l = objs.filter(initialized=True)
        memberships = _partition_by(lambda m: m.project_id, memberships_l)

        new_holdings = []
        for project in projects:
            base_user = base_projects.get(project.id)
            base_holdings = (holdings[base_user.uuid]
                             if base_user is not None else None)

            grants = grants_d[project.id]
            for grant in grants:
                resource = grant.resource.name
                values = self.find_resource(base_holdings, resource)
                (u_min, u_max) = values if values else (0, 0)
                plimit = (grant.project_capacity
                          if project.state == NORMAL else 0)
                h = orm.Holding(
                    holder=self.project_holder(project),
                    source=None,
                    resource=resource,
                    limit=plimit,
                    usage_min=u_min,
                    usage_max=u_max)
                new_holdings.append(h)

                for membership in memberships.get(project.id, []):
                    user = membership.person
                    mlimit = (grant.member_capacity
                              if project.state == NORMAL and
                              membership.state in ACTUALLY_ACCEPTED else 0)
                    (u_min, u_max) = ((u_min, u_max)
                                      if user == base_user else (0, 0))
                    h = orm.Holding(
                        holder=self.user_holder(user),
                        source=self.project_holder(project),
                        resource=resource,
                        limit=mlimit,
                        usage_min=u_min,
                        usage_max=u_max)
                    new_holdings.append(h)

        orm.Holding.objects.bulk_create(new_holdings)
        orm.Holding.objects.filter(source="system").delete()

    def backwards(self, orm):
        "Write your backwards methods here."

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
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'im.astakosuser': {
            'Meta': {'object_name': 'AstakosUser', '_ormbases': ['auth.User']},
            'accepted_email': ('django.db.models.fields.EmailField', [], {'default': 'None', 'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'accepted_policy': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'activation_sent': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'affiliation': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'auth_token': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'auth_token_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'auth_token_expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'base_project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'base_user'", 'to': "orm['im.Project']"}),
            'date_signed_terms': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'deactivated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'deactivated_reason': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True'}),
            'disturbed_quota': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'email_verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_credits': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_signed_terms': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'invitations': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'is_rejected': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'level': ('django.db.models.fields.IntegerField', [], {'default': '4'}),
            'moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'moderated_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'moderated_data': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'policy': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['im.Resource']", 'null': 'True', 'through': "orm['im.AstakosUserQuota']", 'symmetrical': 'False'}),
            'rejected_reason': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {}),
            'user_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True', 'primary_key': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'verification_code': ('django.db.models.fields.CharField', [], {'max_length': '255', 'unique': 'True', 'null': 'True'}),
            'verified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
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
            'capacity': ('django.db.models.fields.BigIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Resource']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosUser']"})
        },
        'im.authproviderpolicyprofile': {
            'Meta': {'ordering': "['priority']", 'object_name': 'AuthProviderPolicyProfile'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'authpolicy_profiles'", 'symmetrical': 'False', 'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_exclusive': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'policy_add': ('django.db.models.fields.NullBooleanField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'policy_automoderate': ('django.db.models.fields.NullBooleanField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'policy_create': ('django.db.models.fields.NullBooleanField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'policy_limit': ('django.db.models.fields.IntegerField', [], {'default': 'None', 'null': 'True'}),
            'policy_login': ('django.db.models.fields.NullBooleanField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'policy_remove': ('django.db.models.fields.NullBooleanField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'policy_required': ('django.db.models.fields.NullBooleanField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'policy_switch': ('django.db.models.fields.NullBooleanField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'priority': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'authpolicy_profiles'", 'symmetrical': 'False', 'to': "orm['im.AstakosUser']"})
        },
        'im.chain': {
            'Meta': {'object_name': 'Chain'},
            'chain': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'im.component': {
            'Meta': {'object_name': 'Component'},
            'auth_token': ('django.db.models.fields.CharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'auth_token_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'auth_token_expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'base_url': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True'})
        },
        'im.emailchange': {
            'Meta': {'object_name': 'EmailChange'},
            'activation_key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'new_email_address': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'requested_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'emailchanges'", 'unique': 'True', 'to': "orm['im.AstakosUser']"})
        },
        'im.endpoint': {
            'Meta': {'object_name': 'Endpoint'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'endpoints'", 'to': "orm['im.Service']"})
        },
        'im.endpointdata': {
            'Meta': {'unique_together': "(('endpoint', 'key'),)", 'object_name': 'EndpointData'},
            'endpoint': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'data'", 'to': "orm['im.Endpoint']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '1024'})
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
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.BigIntegerField', [], {'primary_key': 'True', 'db_column': "'id'"}),
            'is_base': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_application': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'last_of_project'", 'null': 'True', 'to': "orm['im.ProjectApplication']"}),
            'limit_on_members_number': ('django.db.models.fields.BigIntegerField', [], {}),
            'member_join_policy': ('django.db.models.fields.IntegerField', [], {}),
            'member_leave_policy': ('django.db.models.fields.IntegerField', [], {}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['im.AstakosUser']", 'through': "orm['im.ProjectMembership']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'unique': 'True', 'null': 'True', 'db_index': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projs_owned'", 'null': 'True', 'to': "orm['im.AstakosUser']"}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'realname': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'resource_grants': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['im.Resource']", 'null': 'True', 'through': "orm['im.ProjectResourceQuota']", 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'im.projectapplication': {
            'Meta': {'unique_together': "(('chain', 'id'),)", 'object_name': 'ProjectApplication'},
            'applicant': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects_applied'", 'to': "orm['im.AstakosUser']"}),
            'chain': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'chained_apps'", 'db_column': "'chain'", 'to': "orm['im.Project']"}),
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issue_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'limit_on_members_number': ('django.db.models.fields.BigIntegerField', [], {'null': 'True'}),
            'member_join_policy': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'member_leave_policy': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects_owned'", 'null': 'True', 'to': "orm['im.AstakosUser']"}),
            'private': ('django.db.models.fields.NullBooleanField', [], {'default': 'False', 'null': 'True', 'blank': 'True'}),
            'resource_grants': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['im.Resource']", 'null': 'True', 'through': "orm['im.ProjectResourceGrant']", 'blank': 'True'}),
            'response': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'response_actor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'responded_apps'", 'null': 'True', 'to': "orm['im.AstakosUser']"}),
            'response_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'waive_actor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'waived_apps'", 'null': 'True', 'to': "orm['im.AstakosUser']"}),
            'waive_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'waive_reason': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'im.projectlock': {
            'Meta': {'object_name': 'ProjectLock'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'im.projectlog': {
            'Meta': {'object_name': 'ProjectLog'},
            'actor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosUser']", 'null': 'True'}),
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'from_state': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'log'", 'to': "orm['im.Project']"}),
            'reason': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'to_state': ('django.db.models.fields.IntegerField', [], {})
        },
        'im.projectmembership': {
            'Meta': {'unique_together': "(('person', 'project'),)", 'object_name': 'ProjectMembership'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initialized': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosUser']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Project']"}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'})
        },
        'im.projectmembershiplog': {
            'Meta': {'object_name': 'ProjectMembershipLog'},
            'actor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosUser']", 'null': 'True'}),
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'from_state': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'membership': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'log'", 'to': "orm['im.ProjectMembership']"}),
            'reason': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'to_state': ('django.db.models.fields.IntegerField', [], {})
        },
        'im.projectresourcegrant': {
            'Meta': {'unique_together': "(('resource', 'project_application'),)", 'object_name': 'ProjectResourceGrant'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'member_capacity': ('django.db.models.fields.BigIntegerField', [], {}),
            'project_application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.ProjectApplication']"}),
            'project_capacity': ('django.db.models.fields.BigIntegerField', [], {}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Resource']"})
        },
        'im.projectresourcequota': {
            'Meta': {'unique_together': "(('resource', 'project'),)", 'object_name': 'ProjectResourceQuota'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'member_capacity': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Project']"}),
            'project_capacity': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Resource']"})
        },
        'im.resource': {
            'Meta': {'object_name': 'Resource'},
            'api_visible': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'desc': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'project_default': ('django.db.models.fields.BigIntegerField', [], {}),
            'service_origin': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'service_type': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'ui_visible': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'unit': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'uplimit': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
        'im.service': {
            'Meta': {'object_name': 'Service'},
            'component': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.Component']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'im.sessioncatalog': {
            'Meta': {'object_name': 'SessionCatalog'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'session_key': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sessions'", 'null': 'True', 'to': "orm['im.AstakosUser']"})
        },
        'im.usersetting': {
            'Meta': {'unique_together': "(('user', 'setting'),)", 'object_name': 'UserSetting'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'setting': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['im.AstakosUser']"}),
            'value': ('django.db.models.fields.IntegerField', [], {})
        },
        'quotaholder_app.commission': {
            'Meta': {'object_name': 'Commission'},
            'clientkey': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'issue_datetime': ('django.db.models.fields.DateTimeField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '4096'}),
            'serial': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'quotaholder_app.holding': {
            'Meta': {'unique_together': "(('holder', 'source', 'resource'),)", 'object_name': 'Holding'},
            'holder': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'limit': ('django.db.models.fields.BigIntegerField', [], {}),
            'resource': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'null': 'True'}),
            'usage_max': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'usage_min': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
        'quotaholder_app.provision': {
            'Meta': {'object_name': 'Provision'},
            'holder': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.BigIntegerField', [], {}),
            'resource': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'serial': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provisions'", 'to': "orm['quotaholder_app.Commission']"}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'null': 'True'})
        },
        'quotaholder_app.provisionlog': {
            'Meta': {'object_name': 'ProvisionLog'},
            'delta_quantity': ('django.db.models.fields.BigIntegerField', [], {}),
            'holder': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issue_time': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'limit': ('django.db.models.fields.BigIntegerField', [], {}),
            'log_time': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'resource': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'serial': ('django.db.models.fields.BigIntegerField', [], {}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'null': 'True'}),
            'usage_max': ('django.db.models.fields.BigIntegerField', [], {}),
            'usage_min': ('django.db.models.fields.BigIntegerField', [], {})
        }
    }

    complete_apps = ['im', 'quotaholder_app']
    symmetrical = True
