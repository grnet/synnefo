# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdditionalMail',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.EmailField(max_length=75)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ApprovalTerms',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(auto_now_add=True, verbose_name='Issue date', db_index=True)),
                ('location', models.CharField(max_length=255, verbose_name='Terms location')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AstakosUser',
            fields=[
                ('user_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('affiliation', models.CharField(max_length=255, null=True, verbose_name='Affiliation', blank=True)),
                ('level', models.IntegerField(default=4, verbose_name='Inviter level')),
                ('invitations', models.IntegerField(default=0, verbose_name='Invitations left')),
                ('auth_token', models.CharField(null=True, max_length=64, blank=True, help_text='Renew your authentication token. Make sure to set the new token in any client you may be using, to preserve its functionality.', unique=True, verbose_name='Authentication Token')),
                ('auth_token_created', models.DateTimeField(null=True, verbose_name='Token creation date')),
                ('auth_token_expires', models.DateTimeField(null=True, verbose_name='Token expiration date')),
                ('updated', models.DateTimeField(verbose_name='Last update date')),
                ('deactivated_reason', models.TextField(default=None, null=True, verbose_name='Reason for user deactivation')),
                ('deactivated_at', models.DateTimeField(null=True, verbose_name='User deactivation date', blank=True)),
                ('has_credits', models.BooleanField(default=False, verbose_name='User has credits')),
                ('is_verified', models.BooleanField(default=False, verbose_name='User is verified')),
                ('email_verified', models.BooleanField(default=False, verbose_name='User email is verified')),
                ('verification_code', models.CharField(max_length=255, unique=True, null=True, verbose_name='String used for email verification')),
                ('verified_at', models.DateTimeField(null=True, verbose_name='User verification date', blank=True)),
                ('activation_sent', models.DateTimeField(null=True, verbose_name='Activation sent date', blank=True)),
                ('is_rejected', models.BooleanField(default=False, verbose_name='Account is rejected')),
                ('rejected_reason', models.TextField(null=True, verbose_name='Reason for user rejection', blank=True)),
                ('moderated', models.BooleanField(default=False, verbose_name='Account is moderated')),
                ('moderated_at', models.DateTimeField(default=None, null=True, verbose_name='Date moderated', blank=True)),
                ('moderated_data', models.TextField(default=None, null=True, blank=True)),
                ('accepted_policy', models.CharField(default=None, max_length=255, null=True, verbose_name='Accepted policy', blank=True)),
                ('accepted_email', models.EmailField(default=None, max_length=75, null=True, blank=True)),
                ('has_signed_terms', models.BooleanField(default=False, verbose_name='False if needs to sign terms')),
                ('date_signed_terms', models.DateTimeField(null=True, verbose_name='Date of terms signing', blank=True)),
                ('uuid', models.CharField(unique=True, max_length=255, verbose_name='Unique user identifier')),
                ('disturbed_quota', models.BooleanField(default=False, db_index=True, verbose_name='Needs quotaholder syncing')),
            ],
            options={
                'abstract': False,
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
            },
            bases=('auth.user',),
        ),
        migrations.CreateModel(
            name='AstakosUserAuthProvider',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('affiliation', models.CharField(default=None, max_length=255, null=True, verbose_name='Affiliation', blank=True)),
                ('module', models.CharField(default=b'local', max_length=255, verbose_name='Provider')),
                ('identifier', models.CharField(max_length=255, null=True, verbose_name='Third-party identifier', blank=True)),
                ('active', models.BooleanField(default=True)),
                ('auth_backend', models.CharField(default=b'astakos', max_length=255, verbose_name='Backend')),
                ('info_data', models.TextField(default=b'', null=True, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name=b'Creation date')),
                ('last_login_at', models.DateTimeField(default=None, null=True, verbose_name=b'Last login date')),
                ('user', models.ForeignKey(related_name='auth_providers', to='im.AstakosUser')),
            ],
            options={
                'ordering': ('module', 'created'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AstakosUserQuota',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('capacity', models.BigIntegerField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AuthProviderPolicyProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='Name', db_index=True)),
                ('provider', models.CharField(max_length=255, verbose_name='Provider')),
                ('is_exclusive', models.BooleanField(default=False)),
                ('policy_add', models.NullBooleanField(default=None)),
                ('policy_remove', models.NullBooleanField(default=None)),
                ('policy_create', models.NullBooleanField(default=None)),
                ('policy_login', models.NullBooleanField(default=None)),
                ('policy_limit', models.IntegerField(default=None, null=True)),
                ('policy_required', models.NullBooleanField(default=None)),
                ('policy_automoderate', models.NullBooleanField(default=None)),
                ('policy_switch', models.NullBooleanField(default=None)),
                ('priority', models.IntegerField(default=1)),
                ('active', models.BooleanField(default=True)),
                ('groups', models.ManyToManyField(related_name='authpolicy_profiles', to='auth.Group')),
                ('users', models.ManyToManyField(related_name='authpolicy_profiles', to='im.AstakosUser')),
            ],
            options={
                'ordering': ['priority'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Chain',
            fields=[
                ('chain', models.AutoField(serialize=False, primary_key=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Component',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255, verbose_name='Name', db_index=True)),
                ('url', models.CharField(help_text='URL the component is accessible from', max_length=1024, null=True, verbose_name='Component url')),
                ('base_url', models.CharField(max_length=1024, null=True)),
                ('auth_token', models.CharField(max_length=64, unique=True, null=True, verbose_name='Authentication Token', blank=True)),
                ('auth_token_created', models.DateTimeField(null=True, verbose_name='Token creation date')),
                ('auth_token_expires', models.DateTimeField(null=True, verbose_name='Token expiration date')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EmailChange',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('new_email_address', models.EmailField(help_text='Provide a new email address. Until you verify the new address by following the activation link that will be sent to it, your old email address will remain active.', max_length=75, verbose_name='new e-mail address')),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('activation_key', models.CharField(unique=True, max_length=40, db_index=True)),
                ('user', models.ForeignKey(related_name='emailchanges', to='im.AstakosUser', unique=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Endpoint',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EndpointData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.CharField(max_length=255)),
                ('value', models.CharField(max_length=1024)),
                ('endpoint', models.ForeignKey(related_name='data', to='im.Endpoint')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Invitation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('realname', models.CharField(max_length=255, verbose_name='Real name')),
                ('username', models.CharField(unique=True, max_length=255, verbose_name='Unique ID')),
                ('code', models.BigIntegerField(verbose_name='Invitation code', db_index=True)),
                ('is_consumed', models.BooleanField(default=False, verbose_name='Consumed?')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Creation date')),
                ('consumed', models.DateTimeField(null=True, verbose_name='Consumption date', blank=True)),
                ('inviter', models.ForeignKey(related_name='invitations_sent', to='im.AstakosUser', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PendingThirdPartyUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('third_party_identifier', models.CharField(max_length=255, null=True, verbose_name='Third-party identifier', blank=True)),
                ('provider', models.CharField(max_length=255, verbose_name='Provider', blank=True)),
                ('email', models.EmailField(max_length=75, null=True, verbose_name='e-mail address', blank=True)),
                ('first_name', models.CharField(max_length=30, null=True, verbose_name='first name', blank=True)),
                ('last_name', models.CharField(max_length=30, null=True, verbose_name='last name', blank=True)),
                ('affiliation', models.CharField(max_length=255, null=True, verbose_name=b'Affiliation', blank=True)),
                ('username', models.CharField(help_text='Required. 30 characters or fewer. Letters, numbers and @/./+/-/_ characters', unique=True, max_length=30, verbose_name='username')),
                ('token', models.CharField(max_length=255, null=True, verbose_name='Token', blank=True)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('info', models.TextField(default=b'', null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigIntegerField(serialize=False, primary_key=True, db_column=b'id')),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(max_length=80, unique=True, null=True, db_index=True)),
                ('state', models.IntegerField(default=0, db_index=True)),
                ('uuid', models.CharField(unique=True, max_length=255)),
                ('realname', models.CharField(max_length=80)),
                ('homepage', models.URLField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('end_date', models.DateTimeField()),
                ('member_join_policy', models.IntegerField()),
                ('member_leave_policy', models.IntegerField()),
                ('limit_on_members_number', models.BigIntegerField()),
                ('private', models.BooleanField(default=False)),
                ('is_base', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectApplication',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('state', models.IntegerField(default=0, db_index=True)),
                ('name', models.CharField(max_length=80, null=True)),
                ('homepage', models.URLField(max_length=255, null=True)),
                ('description', models.TextField(null=True, blank=True)),
                ('start_date', models.DateTimeField(null=True, blank=True)),
                ('end_date', models.DateTimeField(null=True)),
                ('member_join_policy', models.IntegerField(null=True)),
                ('member_leave_policy', models.IntegerField(null=True)),
                ('limit_on_members_number', models.BigIntegerField(null=True)),
                ('comments', models.TextField(null=True, blank=True)),
                ('issue_date', models.DateTimeField(auto_now_add=True)),
                ('response_date', models.DateTimeField(null=True, blank=True)),
                ('response', models.TextField(null=True, blank=True)),
                ('waive_date', models.DateTimeField(null=True, blank=True)),
                ('waive_reason', models.TextField(null=True, blank=True)),
                ('private', models.NullBooleanField(default=False)),
                ('applicant', models.ForeignKey(related_name='projects_applied', to='im.AstakosUser')),
                ('chain', models.ForeignKey(related_name='chained_apps', db_column=b'chain', to='im.Project')),
                ('owner', models.ForeignKey(related_name='projects_owned', to='im.AstakosUser', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectLock',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('from_state', models.IntegerField(null=True)),
                ('to_state', models.IntegerField()),
                ('date', models.DateTimeField()),
                ('reason', models.TextField(null=True)),
                ('comments', models.TextField(null=True)),
                ('actor', models.ForeignKey(to='im.AstakosUser', null=True)),
                ('project', models.ForeignKey(related_name='log', to='im.Project')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectMembership',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('state', models.IntegerField(default=0, db_index=True)),
                ('overquota_state', models.CharField(default=b'OK', max_length=255)),
                ('overquota_state_date', models.DateTimeField(auto_now_add=True)),
                ('overquota_date', models.DateTimeField(default=None, null=True)),
                ('initialized', models.BooleanField(default=False)),
                ('person', models.ForeignKey(to='im.AstakosUser')),
                ('project', models.ForeignKey(to='im.Project')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectMembershipLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('from_state', models.IntegerField(null=True)),
                ('to_state', models.IntegerField()),
                ('date', models.DateTimeField()),
                ('reason', models.TextField(null=True)),
                ('comments', models.TextField(null=True)),
                ('actor', models.ForeignKey(to='im.AstakosUser', null=True)),
                ('membership', models.ForeignKey(related_name='log', to='im.ProjectMembership')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectResourceGrant',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('project_capacity', models.BigIntegerField()),
                ('member_capacity', models.BigIntegerField()),
                ('project_application', models.ForeignKey(to='im.ProjectApplication')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectResourceQuota',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('project_capacity', models.BigIntegerField(default=0)),
                ('member_capacity', models.BigIntegerField(default=0)),
                ('project', models.ForeignKey(to='im.Project')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255, verbose_name='Name')),
                ('desc', models.TextField(null=True, verbose_name='Description')),
                ('service_type', models.CharField(max_length=255, verbose_name='Type')),
                ('service_origin', models.CharField(max_length=255, db_index=True)),
                ('unit', models.CharField(max_length=255, null=True, verbose_name='Unit')),
                ('uplimit', models.BigIntegerField(default=0)),
                ('project_default', models.BigIntegerField()),
                ('ui_visible', models.BooleanField(default=True)),
                ('api_visible', models.BooleanField(default=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255)),
                ('type', models.CharField(max_length=255)),
                ('component', models.ForeignKey(to='im.Component')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SessionCatalog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('session_key', models.CharField(max_length=40, verbose_name='session key')),
                ('user', models.ForeignKey(related_name='sessions', to='im.AstakosUser', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserSetting',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('setting', models.CharField(max_length=255)),
                ('value', models.IntegerField()),
                ('user', models.ForeignKey(to='im.AstakosUser')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='usersetting',
            unique_together=set([('user', 'setting')]),
        ),
        migrations.AddField(
            model_name='projectresourcequota',
            name='resource',
            field=models.ForeignKey(to='im.Resource'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='projectresourcequota',
            unique_together=set([('resource', 'project')]),
        ),
        migrations.AddField(
            model_name='projectresourcegrant',
            name='resource',
            field=models.ForeignKey(to='im.Resource'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='projectresourcegrant',
            unique_together=set([('resource', 'project_application')]),
        ),
        migrations.AlterUniqueTogether(
            name='projectmembership',
            unique_together=set([('person', 'project')]),
        ),
        migrations.AddField(
            model_name='projectapplication',
            name='resource_grants',
            field=models.ManyToManyField(to='im.Resource', null=True, through='im.ProjectResourceGrant', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='projectapplication',
            name='response_actor',
            field=models.ForeignKey(related_name='responded_apps', to='im.AstakosUser', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='projectapplication',
            name='waive_actor',
            field=models.ForeignKey(related_name='waived_apps', to='im.AstakosUser', null=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='projectapplication',
            unique_together=set([('chain', 'id')]),
        ),
        migrations.AddField(
            model_name='project',
            name='last_application',
            field=models.ForeignKey(related_name='last_of_project', to='im.ProjectApplication', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='project',
            name='members',
            field=models.ManyToManyField(to='im.AstakosUser', through='im.ProjectMembership'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='project',
            name='owner',
            field=models.ForeignKey(related_name='projs_owned', to='im.AstakosUser', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='project',
            name='resource_grants',
            field=models.ManyToManyField(to='im.Resource', null=True, through='im.ProjectResourceQuota', blank=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='pendingthirdpartyuser',
            unique_together=set([('provider', 'third_party_identifier')]),
        ),
        migrations.AlterUniqueTogether(
            name='endpointdata',
            unique_together=set([('endpoint', 'key')]),
        ),
        migrations.AddField(
            model_name='endpoint',
            name='service',
            field=models.ForeignKey(related_name='endpoints', to='im.Service'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='astakosuserquota',
            name='resource',
            field=models.ForeignKey(to='im.Resource'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='astakosuserquota',
            name='user',
            field=models.ForeignKey(to='im.AstakosUser'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='astakosuserquota',
            unique_together=set([('resource', 'user')]),
        ),
        migrations.AlterUniqueTogether(
            name='astakosuserauthprovider',
            unique_together=set([('identifier', 'module', 'user')]),
        ),
        migrations.AddField(
            model_name='astakosuser',
            name='base_project',
            field=models.ForeignKey(related_name='base_user', to='im.Project', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='astakosuser',
            name='policy',
            field=models.ManyToManyField(to='im.Resource', null=True, through='im.AstakosUserQuota'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='additionalmail',
            name='owner',
            field=models.ForeignKey(to='im.AstakosUser'),
            preserve_default=True,
        ),
    ]
