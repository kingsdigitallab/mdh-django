'''
Created on 15 Feb 2018

@author: Geoffroy Noel
'''

from mdh_corpus.models import (
    Language, Discipline,
    Article, Journal,
    # Ngram, NgramArticle
)
import logging
from ._kdlcommand import KDLCommand
import os
import re
from django.conf import settings
from datetime import date
from tqdm import tqdm

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
            'discipline': {},
            'language': {},
            'journal': {},
        }

    def add_arguments(self, parser):
        ret = super(Command, self).add_arguments(parser)
        parser.add_argument(
            '-f', '--filter', action='store', dest='filter',
            help="Filter article by substring.",
        )

        return ret

    def get_files(self):
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
            if 'metadata' in p:
                for file in f:
                    path = os.path.join(p, file)
                    if re.search(filter_re, path):
                        yield path

    def log(self, msg):
        # logger.debug(msg)
        pass

    def action_clear(self):
        [r.delete() for r in Journal.objects.all()]

    def action_locate(self):
        c = 0
        for path in self.get_files():
            c += 1
            print(path)

        print('Found %s files.' % c)

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

    def read_and_upload_meta(self, path, update=False):

        data = {}
        data['article.fileid'] = re.sub(r'^.*/(.*?).xml$', r'\1', path)

        article = Article.objects.filter(
            fileid=data['article.fileid']
        ).first()

        if update or article is None:
            try:
                self.read_meta_file(path, data)
                self.upload_meta(data, article)
            except Exception:
                print(data)
                raise

    def get_or_create(self, Amodel, label):
        # get or create a record in Amodel table
        # with label = label
        # Use caching.
        amodel = Amodel.__name__.lower()
        cache = self.cache[amodel]
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
            Language, data['language.label'])

        # discipline
        discipline, created = self.get_or_create(
            Discipline, data['discipline.label'])

        # article
        article.journal = journal
        article.language = language
        article.label = data['article.label']
        article.discipline = discipline
        article.pub_date = date(
            int(data['article.pub_date.year']),
            int(data['article.pub_date.month']),
            1
        )
        article.save()

        # update the article

    def read_meta_file(self, path, data):
        import xml.etree.ElementTree as ET
        tree = ET.parse(path)
        root = tree.getroot()

        data['discipline.label'] = 'unknown'
        for match in re.findall(r'([^/]+?)\s+Corpus', path):
            data['discipline.label'] = match.strip().lower()

        # <issn pub-type="epub">1539297X</issn>
        xpaths = {
            'journal.label': './/journal-title',
            'journal.ppub': './/journal-meta/issn[@pub-type="ppub"]',
            'journal.epub': './/journal-meta/issn[@pub-type="epub"]',
            'article.label': './/article-meta/title-group/article-title',
            'article.pub_date.month': './/article-meta/pub-date/month',
            'article.pub_date.year': './/article-meta/pub-date/year',
        }
        required = ['journal.label', 'article.pub_date_year']

        for f, p in xpaths.items():
            v = None
            v = root.find(p, ns_meta)
            if v is not None:
                v = (''.join(v.itertext()) or '').strip()[:300]
            if not v and f in required:
                raise Exception('Empty value ' + p)
            data[f] = v

        # language
        data['language.label'] = 'unspecified'
        for meta in root.findall('.//article-meta//custom-meta'):
            name = meta.find('meta-name')
            if name is not None and name.text == 'lang':
                data['language.label'] = meta.find('meta-value').text
                break

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

        return data
