from .base import *  # noqa

ALLOWED_HOSTS = ['mdh.kdl.kcl.ac.uk']

INTERNAL_IPS = INTERNAL_IPS + ['']

DATABASES = {
    'default': {
        'ENGINE': db_engine,
        'NAME': 'app_mdh_liv',
        'USER': 'app_mdh',
        'PASSWORD': '',
        'HOST': ''
    },
}

SECRET_KEY = ''
