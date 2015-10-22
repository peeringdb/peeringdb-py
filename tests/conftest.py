
from django.conf import settings
import os


def pytest_configure():
    # lazy init for translations
    _ = lambda s: s


    settings.configure(
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.admin',
            'django.contrib.sessions',
            'django_peeringdb',
        ],
#        MIDDLEWARE_CLASSES=(
#            'django.contrib.sessions.middleware.SessionMiddleware',
#            'django.contrib.auth.middleware.AuthenticationMiddleware',
#            'django.contrib.messages.middleware.MessageMiddleware',
#        ),
        DATABASE_ENGINE='django.db.backends.sqlite3',
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
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

