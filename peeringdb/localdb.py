
import django
import os
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.db.models import get_app, get_models
import warnings

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

    extra = {
        'PEERINGDB_SYNC_URL': cfg['peeringdb'].get('url', ''),
        'PEERINGDB_SYNC_USERNAME': cfg['peeringdb'].get('user', ''),
        'PEERINGDB_SYNC_PASSWORD': cfg['peeringdb'].get('password', ''),
        'PEERINGDB_SYNC_ONLY': cfg['peeringdb'].get('sync_only', []),
        'PEERINGDB_SYNC_STRIP_TZ': True,
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

    def list_tables(self):
        models = get_models(get_app('django_peeringdb'), include_auto_created=True)
        return tuple(m._meta.db_table for m in models)

    def fix_tables(self):
        """ fix mysql table character set
        shouldn't be used on tables with existing data
        """
        self.create()
        dbcfg = self.cfg['database']

        if dbcfg.get('engine', '') == 'mysql':
            cursor = connection.cursor()

            for each in self.list_tables():
                cursor.execute('ALTER TABLE %s DEFAULT CHARACTER SET utf8;' % each)

    def drop_tables(self):
        """ drop tables this added """
        cursor = connection.cursor()
        cursor.execute('set foreign_key_checks = 0;')
        cursor.execute('DROP TABLE IF EXISTS %s;' % ','.join(self.list_tables()))
        cursor.execute('set foreign_key_checks = 1;')

    def sync(self):
        self.create()
        call_command('pdb_sync', interactive=False)
