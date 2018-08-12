'''
Created on 15 Feb 2018

@author: Geoffroy Noel
'''

from mdh_corpus.models import (
    Language,
    Article, Journal,
    Term, Article3Term,
    Domain, TERM_MAX_LEN
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
from django.db.utils import IntegrityError, OperationalError

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
            'terms': None,
            'language': {},
        }

    def add_arguments(self, parser):
        ret = super(Command, self).add_arguments(parser)
        parser.add_argument(
            '-f', '--filter', action='store', dest='filter',
            help="Filter article by substring.",
        )
        parser.add_argument(
            '--reverse', action='store_true', dest='reverse',
            help="reverse processing.",
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
        Article3Term.objects.all().delete()
        Term.objects.all().delete()

    def action_locate(self):
        c = 0
        for path in self.get_files():
            c += 1
            print(path)

        print('Found %s files.' % c)

    def action_update_ngram3(self):
        return self.action_add_ngramn('3', update=True)

    def action_add_ngram3(self):
        return self.action_add_ngramn('3')

    def action_add_ngramn(self, n, update=False):
        c = 0
        nf = 0

        assert(n == '3')

        self._init_garbage_regs()

#         Ngramn = globals()['Ngram%s' % n]
#         NgramnArticle = globals()['Ngram%sArticle' % n]
        Ngramn = Term
        NgramnArticle = Article3Term

        # self.preload_ngrams(Ngramn)

        csv_pattern = re.compile(r'^.*/(.*?)-ngram' + n + r'\.txt$')

        print('locate ngram files')
        paths = list(self.get_files('ngram%s' % n, '.txt'))
        if self.options['reverse']:
            paths = paths[::-1]
        for path in tqdm(paths):
            c += 1
            fileid = csv_pattern.sub(r'\1', path)

            article_ids = Article.objects.filter(
                fileid=fileid,
                lang__label__in=['en', 'EN', 'eng', 'ENG']
            ).values_list('id', flat=True)

            if not article_ids:
                nf += 1
            else:
                while True:
                    try:
                        self.add_ngramn(
                            article_ids[0], path,
                            Ngramn, NgramnArticle, n, update=update
                        )
                        break
                    except IntegrityError as e:
                        print(
                            'Race condition (duplicate key), retry... (%s)'
                            % str(e))
                    except OperationalError as e:
                        print(
                            'Race condition (operational error), retry... (%s)'
                            % str(e))

        print('Found %s files. %s missing from DB.' % (c, nf))

    def preload_ngrams(self, Ngramn):
        print('preload ngrams')
        self.cache['ngrams'] = {
            ngram[0]: ngram[1]
            for ngram
            in Ngramn.objects.all().values_list(
                'label', 'id'
            ).order_by().iterator()
        }

    def _init_garbage_regs(self):
        self.reg_alphanum = re.compile(r'\d\D|\D\d')
        self.reg_repetition = re.compile(r'(.)\1\1\1')

    def get_garbage_label(self, string):
        ret = string

        if ret.startswith('0'):
            ret = 'JUNK_ZERO'
        # digits and non-digits (! 4th, 1990s should be kept)
        elif len(ret) > 6 and self.reg_alphanum.search(ret):
            ret = 'JUNK_ALPHANUM'
        # number >= 3000 ! MUST BE AFTER JUNK_ALPHANUM
        elif len(ret) > 3 and ret[0] in ['3', '4', '5', '6', '7', '8', '9']:
            ret = 'NUMBER'
        # repetition same char 4 times is suspicious
        elif self.reg_repetition.search(ret):
            ret = 'JUNK_REPETITION'

        return ret

    def _has_ngram_article(self, NgramnArticle, article_id):
        # skip if we already have ngrams for this article
        return NgramnArticle.objects.filter(
            article_id=article_id
        ).exists()

    def _read_ngram_csv(self, path, lines, tokens):
        max_len = TERM_MAX_LEN

        with open(path, newline='') as f:
            reader = csv.reader(f, delimiter='\t')
            for row in reader:
                string = row[0].strip()
                substrings = string.split(' ')
                if len(substrings) != 3:
                    continue

                tuple = []
                for token in substrings:
                    token = self.get_garbage_label(token[:max_len])

                    tuple.append(token)
                    tokens[token] = 1

                # TODO: pre-process the tokens
                lines[string] = {
                    'freq': row[1].strip(),
                    'tokens': tuple
                }

    def _get_or_create_terms(self, tokens):
        # retrieve all existing ngrams
        # From DB.
        # More scalable and allow concurrent executions
        # But less fast.
        terms = {
            term[0]: term[1]
            for term
            in Term.objects.filter(
                label__in=tokens
            ).values_list('label', 'id').order_by()
        }

        # prepare missing terms records
        terms_missing = []
        for token in tokens:
            if token not in terms:
                terms_missing.append(
                    Term(label=token)
                )

        # bulk create the missing terms records
        if terms_missing:
            Term.objects.bulk_create(terms_missing)
            # add that to <terms>
            for term in terms_missing:
                terms[term.label] = term.id

        return terms, len(terms_missing)

    def _add_article_terms(self, lines, terms, NgramnArticle, article_id):
        # Raw queries here are more than 3 times faster than using ORM

        from django.db import connection
        with connection.cursor() as c:
            statement = '''INSERT INTO mdh_corpus_article3term
            (article_id, term1_id, term2_id, term3_id, freq)
            VALUES
            ''' + ','.join([
                '''(%s, %s, %s, %s, %s)''' % (
                    article_id,
                    terms[line_info['tokens'][0]],
                    terms[line_info['tokens'][1]],
                    terms[line_info['tokens'][2]],
                    line_info['freq']
                )
                for line_info in lines.values()
            ])

            c.execute(statement)

        return len(lines)

    def _add_article_terms_orm(self, lines, terms, NgramnArticle, article_id):
        assert(0)
        article_nterms = [
            NgramnArticle(**{
                'article_id': article_id,
                'term1_id': terms[line_info['tokens'][0]],
                'term2_id': terms[line_info['tokens'][1]],
                'term3_id': terms[line_info['tokens'][2]],
                'freq': line_info['freq']
            })
            for line_info in lines.values()
        ]

        # bulk create the ngram_article records
        if article_nterms:
            NgramnArticle.objects.bulk_create(article_nterms)

        return len(article_nterms)

    @transaction.atomic
    def add_ngramn(self, article_id, path,
                   Ngramn, NgramnArticle, n, update=False):

        # TODO: check all ngrams are normalised in CSV (e.g. lowercase)
        if not update and self._has_ngram_article(NgramnArticle, article_id):
            return

        # read all pairs from CSV (ngram, freq)
        lines = {}
        tokens = {}

        self._read_ngram_csv(path, lines, tokens)

        terms, new_terms_count = self._get_or_create_terms(tokens)

        # prepare all article_nterms
        article_terms_count = self._add_article_terms(
            lines, terms, NgramnArticle, article_id
        )

        print(
            'CSV ngrams: %s; found: %s; missing: %s; ngram_articles: %s [%s]'
            % (
                len(lines),
                len(terms),
                new_terms_count,
                article_terms_count,
                path
            )
        )

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
        article.lang = language
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
