# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0009_volume_type_specs'),
    ]

    operations = [
        migrations.CreateModel(
            name='FlavorAccess',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('project', models.CharField(max_length=255)),
                ('flavor', models.ForeignKey(related_name='access', to='db.Flavor')),
            ],
            options={
                'verbose_name': 'Flavor access per project.',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='flavoraccess',
            unique_together=set([('project', 'flavor')]),
        ),
        migrations.AddField(
            model_name='flavor',
            name='public',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
    ]
