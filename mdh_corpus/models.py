from django.db import models

# Create your models here.

# TODO: optimise data types (e.g. PositiveSmallIntegerField for freq)
# TODO: don't use postgresql autoincrement ID for m2m
# https://docs.djangoproject.com/en/2.1/ref/models/fields/
# #positivesmallintegerfield
# https://www.postgresql.org/docs/current/static/datatype-numeric.html


class Journal(models.Model):
    label = models.CharField(max_length=200, unique=True)
    ppub = models.CharField(max_length=50, null=True)
    epub = models.CharField(max_length=50, null=True)


class Language(models.Model):
    label = models.CharField(max_length=15, unique=True)


class Domain(models.Model):
    label = models.CharField(max_length=30, unique=True)


class Article(models.Model):
    fileid = models.CharField(max_length=100, unique=True)
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE)
    label = models.CharField(max_length=300, null=True)
    lang = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True)
    pub_date = models.DateField()
    domains = models.ManyToManyField(Domain)


class Ngram1(models.Model):
    label = models.CharField(max_length=50, unique=True)


class Ngram1Article(models.Model):
    ngram1 = models.ForeignKey(Ngram1, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    freq = models.PositiveSmallIntegerField(default=0)


class Ngram2(models.Model):
    label = models.CharField(max_length=100, unique=True)


class Ngram2Article(models.Model):
    ngram2 = models.ForeignKey(Ngram2, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    freq = models.PositiveSmallIntegerField(default=0)


class Ngram3(models.Model):
    label = models.CharField(max_length=150, unique=True)


class Ngram3Article(models.Model):
    ngram3 = models.ForeignKey(Ngram3, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    freq = models.PositiveSmallIntegerField(default=0)
