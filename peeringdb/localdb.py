
import django
import os
from django.conf import settings
from django.core.management import call_command
from django.db import connection
import warnings

# lazy init for translations
_ = lambda s: s


def django_configure(cfg):
    if settings.configured:
        return

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

    if 'peeringdb' in cfg:
        extra = {
            'PEERINGDB_SYNC_URL': cfg['peeringdb'].get('url', ''),
            'PEERINGDB_SYNC_USERNAME': cfg['peeringdb'].get('user', ''),
            'PEERINGDB_SYNC_PASSWORD': cfg['peeringdb'].get('password', ''),
            'PEERINGDB_SYNC_ONLY': cfg['peeringdb'].get('sync_only', []),
            'PEERINGDB_SYNC_STRIP_TZ': True,
        }
    else:
        extra = {
            'PEERINGDB_SYNC_STRIP_TZ': True,
        }

    # open file reletive to config dir
    if '__config_dir__' in cfg:
        os.chdir(cfg['__config_dir__'])

    db['ENGINE'] = 'django.db.backends.' + db['ENGINE']

    settings.configure(
        INSTALLED_APPS=[
            'django_peeringdb',
        ],
        DATABASES={
            'default': db
        },
        DEBUG=False,
        TEMPLATE_DEBUG=True,
        LOGGING={
            'version': 1,
            'disable_existing_loggers': False,
            'filters': {
                'dev_warnings': {
                    }
                },
            'handlers': {
                'stderr': {
                    'level': 'DEBUG',
                    'class': 'logging.StreamHandler',
                    'filters': ['dev_warnings'],
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
        # add user defined iso code for Kosovo
        COUNTRIES_OVERRIDE={
            'XK': _('Kosovo'),
        },
        **extra
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

        # get rid of django deprecation warnings
        # TODO fix log filters
        warnings.filterwarnings("ignore")

    def create(self):
        call_command('migrate', interactive=False)

    def drop_tables(self):
        """ drop tables this added """
        print("This command has been removed temporarily")

    def sync(self):
        self.create()
        call_command('pdb_sync', interactive=False)
