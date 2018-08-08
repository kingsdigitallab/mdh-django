'''
Created on 15 Feb 2018

@author: Geoffroy Noel
'''

from mdh_corpus.models import (
    Language,
    Article, Journal,
    Ngram1, Ngram1Article,
    Domain
)
from django.db import transaction
import logging
from ._kdlcommand import KDLCommand
import os
import re
from django.conf import settings
from datetime import date
from tqdm import tqdm
import csv

logger = logging.getLogger('mdh')

ns_meta = {
    'xlink': "http://www.w3.org/1999/xlink",
    'mml': "http://www.w3.org/1998/Math/MathML",
    'xsi': "http://www.w3.org/2001/XMLSchema-instance",
}


class Command(KDLCommand):
    help = 'articles'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.cache = {
            'domain': {},
            'journal': {},
        }

    def add_arguments(self, parser):
        ret = super(Command, self).add_arguments(parser)
        parser.add_argument(
            '-f', '--filter', action='store', dest='filter',
            help="Filter article by substring.",
        )

        return ret

    def get_files(self, dirname='metadata', ext='.xml'):
        source_path = settings.MDH_SOURCE_PATH

        filter = self.options['filter']
        if filter:
            filter_re = [re.escape(f) for f in filter.split(' ')]
            filter_re = r'.*'.join(filter_re)

            print('Filter: ' + filter_re)
        else:
            filter_re = '.*'
        filter_re = '(?ui)' + filter_re

        for p, d, f in os.walk(source_path):
            if dirname in p:
                for file in f:
                    path = os.path.join(p, file)
                    if ext in path and re.search(filter_re, path):
                        yield path

    def log(self, msg):
        # logger.debug(msg)
        pass

    def action_clear_journals(self):
        [r.delete() for r in Journal.objects.all()]
        [r.delete() for r in Article.objects.all()]

    def action_clear_ngrams(self):
        Ngram1Article.objects.all().delete()
        Ngram1.objects.all().delete()

    def action_locate(self):
        c = 0
        for path in self.get_files():
            c += 1
            print(path)

        print('Found %s files.' % c)

    def action_add_ngram1(self):
        c = 0
        nf = 0
        for path in tqdm(list(self.get_files('ngram1', '.txt'))):
            c += 1
            fileid = re.sub(r'^.*/(.*?)-ngram1.txt$', r'\1', path)

            article = Article.objects.filter(fileid=fileid).first()
            if not article:
                nf += 1
            else:
                self.add_ngram1(article, path)

        print('Found %s files. %s missing from DB.' % (c, nf))

    @transaction.atomic
    def add_ngram1(self, article, path):
        # find the ngram file
        # TODO: check the quotation marks and escape marks
        # TODO: check encoding!

        angram_article = Ngram1Article.objects.filter(article=article).first()

        if angram_article:
            return

        strings = {}
        ngram_articles = []

        with open(path, newline='') as f:
            reader = csv.reader(f, delimiter='\t')
            for row in reader:
                string = row[0].strip()[0:50]

                if string in strings:
                    continue

                strings[string] = 1

                # add it to the article
                ngram_articles.append(
                    Ngram1Article(
                        article=article,
                        ngram1=self.get_or_create(Ngram1, string)[0],
                        freq=row[1].strip()
                    )
                )

        if ngram_articles:
            Ngram1Article.objects.bulk_create(ngram_articles)

    def action_update_meta(self):
        return self.action_add_meta(update=True)

    def action_add_meta(self, update=False):
        c = 0
        for path in tqdm(list(self.get_files())):
            c += 1
            self.log(path)
            # print(path)
            self.read_and_upload_meta(path, update=update)

        print('Found %s files.' % c)

    @transaction.atomic
    def read_and_upload_meta(self, path, update=False):

        data = {}
        data['article.fileid'] = re.sub(r'^.*/(.*?).xml$', r'\1', path)

        article = Article.objects.filter(
            fileid=data['article.fileid']
        ).first()

        if update or article is None:
            try:
                if self.read_meta_file(path, data):
                    self.upload_meta(data, article)
            except Exception:
                print(data)
                raise

    def get_or_create(self, Amodel, label):
        # get or create a record in Amodel table
        # with label = label
        # Use caching.
        amodel = Amodel.__name__.lower()

        cache = self.cache.get(amodel, None)
        if cache is None:
            cache = self.cache[amodel] = {
                r.label: r
                for r in
                Amodel.objects.all()
            }

        ret = cache.get(label)
        created = False
        if not ret:
            ret, created = Amodel.objects.get_or_create(
                label=label
            )
            cache[label] = ret

        return ret, created

    def upload_meta(self, data, article):

        if article is None:
            self.log('new article')
            article = Article()

        article.fileid = data['article.fileid']

        # update the journal
        journal, created = self.get_or_create(
            Journal, label=data['journal.label'])

        if created:
            self.log('new journal')
            journal.epub = data['journal.epub']
            journal.ppub = data['journal.ppub']
            journal.label = data['journal.label']
            journal.save()

        # update the language
        language, created = self.get_or_create(
            Language, data['language.label'][:15])

        # domain
        domain, created = self.get_or_create(
            Domain, data['domain.label'])

        # article
        article.journal = journal
        article.language = language
        article.label = data['article.label']
        article.pub_date = date(
            int(data['article.pub_date.year']),
            int(data['article.pub_date.month']),
            1
        )
        article.save()
        article.domains.add(domain)

        # update the article

    def read_meta_file(self, path, data):
        import xml.etree.ElementTree as ET
        try:
            tree = ET.parse(path)
        except ET.ParseError:
            return None

        root = tree.getroot()

        data['domain.label'] = 'unknown'
        for match in re.findall(r'([^/]+?)\s+Corpus', path):
            data['domain.label'] = match.strip().lower()

        # <issn pub-type="epub">1539297X</issn>
        xpaths = {
            'journal.label': './/journal-title',
            'journal.ppub': './/journal-meta/issn[@pub-type="ppub"]',
            'journal.epub': './/journal-meta/issn[@pub-type="epub"]',
            'article.label': './/article-meta/title-group/article-title',
            'article.pub_date.month': './/article-meta/pub-date/month',
            'article.pub_date.year': './/article-meta/pub-date/year',
        }
        required = []

        for f, p in xpaths.items():
            v = None
            v = root.find(p, ns_meta)
            if v is not None:
                v = (''.join(v.itertext()) or '').strip()[:300]
            if not v and f in required:
                raise Exception('Empty value ' + p)
            data[f] = v

        # language
        language = None
        for meta in root.findall('.//article-meta//custom-meta'):
            name = meta.find('meta-name')
            if name is not None and name.text == 'lang':
                language = meta.find('meta-value').text
                break
        data['language.label'] = language or 'unspecified'

        # convert month from string to number (january to 1)
        month = (data['article.pub_date.month'] or '').lower()
        if not re.match(r'^\d+$', month):
            months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                      'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
            month_number = 1
            for i, m in enumerate(months):
                if month.startswith(m):
                    month_number = i + 1
                    break

            data['article.pub_date.month'] = month_number

        #
        data['journal.label'] = data['journal.label'] or 'unspecified'

        #
        year = data.get('article.pub_date.year', None)
        if not year:
            # .../Anthro 2010/...
            year = re.findall(r' (\d{4,4})/', path)[0]
            data['article.pub_date.year'] = year

        return data
