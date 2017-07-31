# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0012_add_flavor_specs'),
    ]

    operations = [
        migrations.CreateModel(
            name='RescueImage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False,
                                        auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('location', models.TextField()),
                ('location_type', models.CharField(max_length=32,
                                                   default=b'file')),
                ('os', models.CharField(max_length=256, null=True)),
                ('os_family', models.CharField(max_length=256, null=True)),
                ('target_os', models.CharField(max_length=256, null=True)),
                ('target_os_family', models.CharField(max_length=256,
                                                      null=True)),
                ('deleted', models.BooleanField(default=False)),
                ('is_default', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RescueProperties',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False,
                                        auto_created=True, primary_key=True)),
                ('os', models.CharField(max_length=256, null=True)),
                ('os_family', models.CharField(max_length=256, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='virtualmachine',
            name='rescue',
            field=models.BooleanField(default=False, db_index=True,
                                      verbose_name=b'Rescue'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='virtualmachine',
            name='rescue_image',
            field=models.ForeignKey(to='db.RescueImage', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='virtualmachine',
            name='rescue_properties',
            field=models.ForeignKey(to='db.RescueProperties', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='virtualmachine',
            name='action',
            field=models.CharField(default=None, max_length=30, null=True,
                                   choices=[(b'CREATE', b'Create VM'),
                                            (b'START', b'Start VM'),
                                            (b'STOP', b'Shutdown VM'),
                                            (b'SUSPEND', b'Admin Suspend VM'),
                                            (b'REBOOT', b'Reboot VM'),
                                            (b'DESTROY', b'Destroy VM'),
                                            (b'RESIZE', b'Resize a VM'),
                                            (b'ADDFLOATINGIP',
                                             b'Add floating IP to VM'),
                                            (b'REMOVEFLOATINGIP',
                                             b'Add floating IP to VM'),
                                            (b'RESCUE', b'Rescue VM'),
                                            (b'UNRESCUE', b'Unrescue VM')]),
            preserve_default=True,
        ),
    ]
