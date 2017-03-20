# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import wagtail.wagtaildocs.models


class Migration(migrations.Migration):

    dependencies = [
        ('wagtaildocs', '0007_merge'),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentFolder',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('title', models.CharField(max_length=255, verbose_name='title')),
                ('created_at', models.DateTimeField(verbose_name='created at', db_index=True, auto_now_add=True)),
                ('path', models.TextField(blank=True)),
                ('folder', models.ForeignKey(to='wagtaildocs.DocumentFolder', null=True)),
            ],
        ),
        migrations.AlterField(
            model_name='document',
            name='file',
            field=models.FileField(upload_to=wagtail.wagtaildocs.models.get_upload_to, verbose_name='file'),
        ),
        migrations.AddField(
            model_name='document',
            name='folder',
            field=models.ForeignKey(to='wagtaildocs.DocumentFolder', null=True, blank=True),
        ),
    ]
