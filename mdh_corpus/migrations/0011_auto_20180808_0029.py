# Generated by Django 2.0 on 2018-08-07 23:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mdh_corpus', '0010_auto_20180807_2250'),
    ]

    operations = [
        migrations.AlterField(
            model_name='language',
            name='label',
            field=models.CharField(max_length=15, unique=True),
        ),
    ]
