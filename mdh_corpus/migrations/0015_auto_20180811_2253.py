# Generated by Django 2.0 on 2018-08-11 21:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mdh_corpus', '0014_auto_20180810_0223'),
    ]

    operations = [
        migrations.CreateModel(
            name='Article3Term',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('freq', models.PositiveSmallIntegerField(default=0)),
                ('article', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mdh_corpus.Article')),
            ],
            options={
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='Term',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=30, unique=True)),
            ],
        ),
        migrations.AlterField(
            model_name='ngram1',
            name='label',
            field=models.CharField(max_length=30, unique=True),
        ),
        migrations.AlterField(
            model_name='ngram2',
            name='label',
            field=models.CharField(max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name='ngram3',
            name='label',
            field=models.CharField(max_length=60, unique=True),
        ),
        migrations.AddField(
            model_name='article3term',
            name='term1',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='art_term1', to='mdh_corpus.Term'),
        ),
        migrations.AddField(
            model_name='article3term',
            name='term2',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='art_term2', to='mdh_corpus.Term'),
        ),
        migrations.AddField(
            model_name='article3term',
            name='term3',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='art_term3', to='mdh_corpus.Term'),
        ),
    ]
