# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-08 16:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('micromanager', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='templatecontent',
            name='is_home_page',
            field=models.BooleanField(default=False),
        ),
    ]
