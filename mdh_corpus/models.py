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


TERM_MAX_LEN = 30


class Term(models.Model):
    # Note: postgres will add an index just for like queries
    # e.g. "X_00ec206e_like" btree (label varchar_pattern_ops)
    # You may want to remove it to save space.
    # Not interested in strings beyond 30 chars, likely to be garbage
    label = models.CharField(max_length=TERM_MAX_LEN, unique=True)


class Article3Term(models.Model):
    '''
    This table can be huge, with hundreds of millions of record.
    Every byte has to count.
    Ideally we'd like to avoid Django .pk / .id field
    because there's no use for it.
    Natural PK = (article, term1, term2, term3)
    but not really essential to enforce it.
    Unfortunately, Django doesn't allow models with composite PK.
    See https://code.djangoproject.com/ticket/373 (open since 2005!)
    '''
    # Total: 20 bytes / records + indices => 40 B
    #
    # 4 bytes
    # id
    # 2 Bytes
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    # 4 Bytes
    term1 = models.ForeignKey(Term, on_delete=models.CASCADE,
                              related_name='art_term1')
    # 4 Bytes
    term2 = models.ForeignKey(Term, on_delete=models.CASCADE,
                              related_name='art_term2')
    # 4 Bytes
    term3 = models.ForeignKey(Term, on_delete=models.CASCADE,
                              related_name='art_term3')
    # 2 Bytes
    freq = models.PositiveSmallIntegerField(default=0)

    class Meta:
        managed = True

#
# class Ngram1(models.Model):
#     label = models.CharField(max_length=30, unique=True)
#
#
# class Ngram1Article(models.Model):
#     ngram1 = models.ForeignKey(Ngram1, on_delete=models.CASCADE)
#     article = models.ForeignKey(Article, on_delete=models.CASCADE)
#     freq = models.PositiveSmallIntegerField(default=0)
#
#
# class Ngram2(models.Model):
#     label = models.CharField(max_length=50, unique=True)
#
#
# class Ngram2Article(models.Model):
#     ngram2 = models.ForeignKey(Ngram2, on_delete=models.CASCADE)
#     article = models.ForeignKey(Article, on_delete=models.CASCADE)
#     freq = models.PositiveSmallIntegerField(default=0)
#
#
# class Ngram3(models.Model):
#     label = models.CharField(max_length=60, unique=True)
#
#
# class Ngram3Article(models.Model):
#     ngram3 = models.ForeignKey(Ngram3, on_delete=models.CASCADE)
#     article = models.ForeignKey(Article, on_delete=models.CASCADE)
#     freq = models.PositiveSmallIntegerField(default=0)
