# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2016-12-19 15:25
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='OpenHumansMember',
            fields=[
                ('oh_id', models.CharField(max_length=16, primary_key=True, serialize=False, unique=True)),
                ('access_token', models.CharField(max_length=256)),
                ('refresh_token', models.CharField(max_length=256)),
                ('token_expires', models.DateTimeField()),
                ('seeq_id', models.IntegerField(null=True)),
            ],
        ),
    ]
