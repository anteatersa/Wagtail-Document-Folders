# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wagtaildocs', '0007_merge'),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentFolder',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('title', models.CharField(verbose_name='title', max_length=255)),
                ('created_at', models.DateTimeField(verbose_name='created at', db_index=True, auto_now_add=True)),
                ('folder', models.ForeignKey(to='wagtaildocs.DocumentFolder', null=True)),
            ],
        ),
        migrations.AddField(
            model_name='document',
            name='folder',
            field=models.ForeignKey(to='wagtaildocs.DocumentFolder', null=True, blank=True),
        ),
    ]
