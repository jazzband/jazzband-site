from datetime import timedelta
import os
from decouple import config, Csv
from markdown.extensions.toc import TocExtension
from markdown.extensions.wikilinks import WikiLinkExtension

from .renderer import smart_pygmented_markdown

IS_PRODUCTION = 'PRODUCTION' in os.environ

ROOT_DIR = os.path.dirname(__file__)

SECRET_KEY = config('SECRET_KEY', 'dev key')
DEBUG = config('DEBUG', True, cast=bool)
SERVER_NAME = config('SERVER_NAME', 'localhost:5000')

HOSTNAMES = config('HOSTNAMES', 'localhost:5000,0.0.0.0:5000', cast=Csv())
REDIS_URL = config('REDIS_URL', 'redis://redis:6379/0')

CELERY_BROKER_URL = CELERY_RESULT_BACKEND = REDIS_URL
CELERY_IMPORTS = [
    'jazzband.members.tasks',
    'jazzband.projects.tasks',
]
CELERY_BEAT_SCHEDULE = {
    'send-new-upload-notifications': {
        'task': 'jazzband.projects.tasks.send_new_upload_notifications',
        'schedule': timedelta(minutes=1),
        'options': {
            'expires': 45,
        }
    },
}

MAIL_DEFAULT_SENDER = config(
    'MAIL_DEFAULT_SENDER',
    'Jazzband <roadies@jazzband.co>'
)
MAIL_PASSWORD = config('MAIL_PASSWORD')
MAIL_PORT = config('MAIL_PORT', 587, cast=int)
MAIL_SERVER = config('MAIL_SERVER', 'localhost')
MAIL_USERNAME = config('MAIL_USERNAME', '')
MAIL_USE_TLS = config('MAIL_USE_TLS', False, cast=bool)

# how many seconds to set the expires and max_age headers
HTTP_CACHE_TIMEOUT = config('HTTP_CACHE_TIMEOUT', 60 * 60, cast=int)

FLATPAGES_ABOUT_ROOT = '../docs/about'
FLATPAGES_ABOUT_EXTENSION = FLATPAGES_NEWS_EXTENSION = ['.md']
FLATPAGES_NEWS_MARKDOWN_EXTENSIONS = [
    'codehilite',
    'fenced_code',
    'footnotes',
    'admonition',
    'tables',
    'abbr',
    'smarty',
    WikiLinkExtension(base_url='/about/', end_url='', html_class=''),
]
FLATPAGES_ABOUT_MARKDOWN_EXTENSIONS = FLATPAGES_NEWS_MARKDOWN_EXTENSIONS + [
    TocExtension(permalink=True),
]

FLATPAGES_ABOUT_HTML_RENDERER = FLATPAGES_NEWS_HTML_RENDERER = \
    smart_pygmented_markdown

FLATPAGES_NEWS_ROOT = '../docs/news'

# Set these values in the .env file or env vars
GITHUB_CLIENT_ID = config('GITHUB_CLIENT_ID', '')
GITHUB_CLIENT_SECRET = config('GITHUB_CLIENT_SECRET', '')
GITHUB_ORG_ID = config('GITHUB_ORG_ID', 'jazzband')
GITHUB_SCOPE = config('GITHUB_SCOPE', 'read:org,user:email')
GITHUB_MEMBERS_TEAM_ID = config('GITHUB_MEMBERS_TEAM_ID', 0, cast=int)
GITHUB_ROADIES_TEAM_ID = config('GITHUB_ROADIES_TEAM_ID', 0, cast=int)
GITHUB_ADMIN_TOKEN = config('GITHUB_ADMIN_TOKEN', '')
GITHUB_WEBHOOKS_KEY = config('GITHUB_WEBHOOKS_KEY', '')

SESSION_COOKIE_NAME = 'session'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_REFRESH_EACH_REQUEST = False
PERMANENT_SESSION_LIFETIME = timedelta(days=14)
USE_SESSION_FOR_NEXT = True

LIBSASS_STYLE = 'compressed'

SQLALCHEMY_DATABASE_URI = config('DATABASE_URL',
                                 'postgres://postgres@db/postgres')
if IS_PRODUCTION:
    SQLALCHEMY_DATABASE_URI += '?sslmode=require'
    VALIDATE_IP = config('GITHUB_VALIDATE_IP', True, cast=bool)
    VALIDATE_SIGNATURE = config('GITHUB_VALIDATE_SIGNATURE', True, cast=bool)
else:
    VALIDATE_IP = False
    VALIDATE_SIGNATURE = False

SQLALCHEMY_TRACK_MODIFICATIONS = False

CSP_REPORT_URI = config('CSP_REPORT_URI', None)
CSP_REPORT_ONLY = config('CSP_REPORT_ONLY', False, cast=bool)
CSP_RULES = {
    'default-src': "'self'",
    'font-src': "'self' data:",
    'frame-src': "'self' analytics.websushi.org",
    'script-src': "'self' analytics.websushi.org",
    'style-src': "'self' 'unsafe-inline'",
    'img-src': "* data:",
    'object-src': "'none'",
}

SENTRY_USER_ATTRS = ['id', 'login', 'is_banned', 'is_member']
if 'GIT_REV' in os.environ:
    SENTRY_CONFIG = {
        'release': os.environ['GIT_REV'],
    }

UPLOAD_ROOT = '/app/uploads'
UPLOAD_ENABLED = config('UPLOAD_ENABLED', True, cast=bool)
RELEASE_ENABLED = config('RELEASE_ENABLED', True, cast=bool)

MAX_CONTENT_LENGTH = 60 * 1024 * 1024  # 60M
