# Generated by Django 2.0 on 2018-08-07 20:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mdh_corpus', '0008_auto_20180807_2110'),
    ]

    operations = [
        migrations.AddField(
            model_name='journal',
            name='epub',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='journal',
            name='label',
            field=models.CharField(max_length=200, unique=True),
        ),
        migrations.AlterField(
            model_name='journal',
            name='ppub',
            field=models.CharField(max_length=50, null=True),
        ),
    ]