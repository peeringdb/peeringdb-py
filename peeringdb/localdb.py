
import django
import os
from django.conf import settings
from django.core.management import call_command

# lazy init for translations
_ = lambda s: s


def django_configure(cfg):
    db_fields = (
        'ENGINE',
        'HOST',
        'NAME',
        'PASSWORD',
        'PORT',
        'USER',
    )
    db = {}
    if 'database' in cfg:
        for k,v in cfg['database'].items():
            k = k.upper()
            if k in db_fields:
                db[k] = v

    else:
        db = {
            'ENGINE': 'sqlite3',
            'NAME': ':memory:',
        }

    # open file reletive to config dir
    if '__config_dir__' in cfg:
        os.chdir(cfg['__config_dir__'])

    db['ENGINE'] = 'django.db.backends.' + db['ENGINE']

    settings.configure(
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.admin',
            'django.contrib.sessions',
            'django_peeringdb',
        ],
        DATABASE_ENGINE='django.db.backends.sqlite3',
        DATABASES={
            'default': db
        },
        DEBUG=False,
        TEMPLATE_DEBUG=True,
        LOGGING = {
            'version': 1,
            'disable_existing_loggers': False,
            'handlers': {
                'stderr': {
                    'level': 'DEBUG',
                    'class': 'logging.StreamHandler',
                    },
            },
            'loggers': {
                '': {
                    'handlers': ['stderr'],
                    'level': 'DEBUG',
                    'propagate': False
                },
            },
        },

        USE_TZ=False,
        PEERINGDB_SYNC_STRIP_TZ=True,
        # add user defined iso code for Kosovo
        COUNTRIES_OVERRIDE = {
            'XK': _('Kosovo'),
        }
    )

class LocalDB(object):
    """
    Abstraction for a local database

    currently this is just django, to extend that, would just need to
    extend this interface
    """

    def __init__(self, cfg):
        self.cfg = cfg
        django_configure(cfg)
        django.setup()

    def create(self):
        call_command('migrate', interactive=False)

    def sync(self):
        self.create()
        call_command('pdb_sync', interactive=False)

