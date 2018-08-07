from django.db import models

# Create your models here.


class Journal(models.Model):
    label = models.CharField(max_length=200, unique=True)
    ppub = models.CharField(max_length=50, null=True)
    epub = models.CharField(max_length=50, null=True)


class Language(models.Model):
    label = models.CharField(max_length=10, unique=True)


class Discipline(models.Model):
    label = models.CharField(max_length=30, unique=True)


class Article(models.Model):
    fileid = models.CharField(max_length=100, unique=True)
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE)
    label = models.CharField(max_length=300, null=True)
    lang = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True)
    pub_date = models.DateField()
    discipline = models.ForeignKey(
        Discipline, on_delete=models.SET_NULL, null=True)


class Ngram(models.Model):
    label = models.CharField(max_length=100, unique=True)


class NgramArticle(models.Model):
    ngram = models.ForeignKey(Ngram, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    freq = models.IntegerField(default=0)
