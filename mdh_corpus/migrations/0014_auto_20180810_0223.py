# Generated by Django 2.0 on 2018-08-10 01:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mdh_corpus', '0013_auto_20180808_0226'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ngram1article',
            name='freq',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='ngram2article',
            name='freq',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='ngram3article',
            name='freq',
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
