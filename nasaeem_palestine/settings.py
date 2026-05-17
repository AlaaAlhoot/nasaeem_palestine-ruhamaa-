import os
import logging
from pathlib import Path
from django.utils.translation import gettext_lazy as _
from django.contrib.messages import constants as messages
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent


def read_env():
    env_path = os.path.join(BASE_DIR, '.env')
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value.strip("'\"")
    return env_vars


ENV = read_env()

# ==================== الأمان ====================
SECRET_KEY     = ENV.get('SECRET_KEY', 'change-me-in-production')
DEBUG          = ENV.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS  = ENV.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

CSRF_TRUSTED_ORIGINS = [
    'https://nasaeem-palestine.com',
    'https://www.nasaeem-palestine.com',
    'http://nasaeem-palestine.com',
    'http://www.nasaeem-palestine.com',
    'http://147.79.117.135',
]

# ==================== التطبيقات ====================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'django.contrib.humanize',

    # مكتبات خارجية
    'crispy_forms',
    'crispy_bootstrap5',
    'django_ckeditor_5',
    'phonenumber_field',
    'django_extensions',
    'rest_framework',
    'django_celery_beat',
    'channels',

    # تطبيقات نسائم
    'main.apps.MainConfig',
    'projects.apps.ProjectsConfig',
    'contact.apps.ContactConfig',
    'dashboard.apps.DashboardConfig',

    # تطبيقات رحماء
    'core.apps.CoreConfig',
    'admin_panel.apps.AdminPanelConfig',
    'sponsor.apps.SponsorConfig',
    'beneficiary.apps.BeneficiaryConfig',
]

# ==================== Middleware ====================
# الترتيب مهم — GZip يجب أن يكون أول شيء
MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware',            # ← أولاً دائماً
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # middleware نسائم
    'dashboard.middleware.MaintenanceModeMiddleware',
    'projects.middleware.ProjectNotFoundMiddleware',

    # middleware رحماء
    'core.middleware.OnlineTrackerMiddleware',
    'core.middleware.AutoLogoutMiddleware',
    'core.middleware.SecurityHeadersMiddleware',
    'core.middleware.MaintenanceMiddleware',
]

ROOT_URLCONF      = 'nasaeem_palestine.urls'
ASGI_APPLICATION  = 'nasaeem_palestine.asgi.application'
WSGI_APPLICATION  = 'nasaeem_palestine.wsgi.application'

# ==================== Templates ====================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        # APP_DIRS=True مع loaders متعارضان — نستخدم loaders يدوياً مع cache
        'APP_DIRS': False,
        'OPTIONS': {
            'loaders': [
                # Cache loader يخزن القوالب المُجمّعة في الذاكرة
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ] if not DEBUG else [
                # في التطوير بدون cache عشان تشوف التغييرات فوراً
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',

                # نسائم — موحّدة (كل processor يغني عن 3-6 قديمة)
                'main.context_processors.site_settings',        # يشمل navigation_data + statistics_data
                'main.context_processors.user_preferences',
                'main.context_processors.breadcrumbs',
                'main.context_processors.seo_data',
                'main.context_processors.social_sharing',
                'main.context_processors.navigation_data',      # alias فارغ
                'main.context_processors.statistics_data',      # alias فارغ

                'projects.context_processors.project_context',  # يشمل navigation + meta + search
                'projects.context_processors.project_breadcrumbs',
                'projects.context_processors.project_navigation',     # alias فارغ
                'projects.context_processors.project_meta',           # alias فارغ
                'projects.context_processors.project_search_suggestions', # alias فارغ

                'contact.context_processors.contact_context',   # يشمل footer + social + seo + security
                'contact.context_processors.contact_notifications_context',
                'contact.context_processors.contact_analytics_context',
                'contact.context_processors.contact_forms_context',   # alias فارغ
                'contact.context_processors.contact_seo_context',     # alias فارغ
                'contact.context_processors.contact_security_context',# alias فارغ
                'contact.context_processors.footer_context',          # alias فارغ
                'contact.context_processors.social_links_processor',  # alias فارغ

                'dashboard.context_processors.dashboard_context', # يشمل stats + notif + actions + system
                'dashboard.context_processors.dashboard_breadcrumbs',
                'dashboard.context_processors.dashboard_statistics',  # alias فارغ
                'dashboard.context_processors.dashboard_notifications',# alias فارغ
                'dashboard.context_processors.dashboard_quick_actions',# alias فارغ
                'dashboard.context_processors.dashboard_system_info',  # alias فارغ

                # رحماء
                'core.context_processors.global_context',
            ],
        },
    },
]

# ==================== قاعدة البيانات ====================
DATABASES = {
    'default': {
        'ENGINE':   ENV.get('DB_ENGINE',   'django.db.backends.mysql'),
        'NAME':     ENV.get('DB_NAME',     'nasaeem_palestine_db'),
        'USER':     ENV.get('DB_USER',     'nasaeem_admin'),
        'PASSWORD': ENV.get('DB_PASSWORD', 'nasaeem@2025@admin'),
        'HOST':     ENV.get('DB_HOST',     'localhost'),
        'PORT':     ENV.get('DB_PORT',     '3306'),
        'OPTIONS': {
            'charset':      'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        # اتصال دائم — يمنع فتح اتصال جديد في كل طلب
        'CONN_MAX_AGE': 60,
    }
}

# ==================== المستخدم المخصص ====================
AUTH_USER_MODEL = 'core.CustomUser'

# ==================== كلمة المرور ====================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ==================== Cache ====================
CACHES = {
    'default': {
        'BACKEND':  'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'nasaeem-cache',
        'TIMEOUT':  300,
        'OPTIONS': {
            'MAX_ENTRIES':  2000,   # زيادة من 1000 → 2000
            'CULL_FREQUENCY': 4,    # احذف ربع الـ cache عند الامتلاء
        },
    }
}

# ==================== WebSocket (Django Channels) ====================
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

# ==================== الجلسات ====================
#SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # أسرع من db وحدها
SESSION_COOKIE_AGE          = 1800
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST  = False   # ← False أسرع (كانت True = write في كل طلب)
SESSION_COOKIE_HTTPONLY     = True
SESSION_COOKIE_SAMESITE     = 'Lax'
SESSION_COOKIE_SECURE       = not DEBUG

# ==================== Authentication ====================
LOGIN_URL            = '/accounts/login/'
LOGIN_REDIRECT_URL   = '/dashboard/'
LOGOUT_REDIRECT_URL  = '/'

# ==================== اللغة والتوقيت ====================
LANGUAGE_CODE = 'ar'
TIME_ZONE     = 'Asia/Gaza'
USE_I18N      = True
USE_L10N      = True
USE_TZ        = True
LANGUAGES     = [('ar', _('العربية')), ('en', _('English'))]
LOCALE_PATHS  = [BASE_DIR / 'locale']

# ==================== الملفات الثابتة والوسائط ====================
STATIC_URL      = ENV.get('STATIC_URL',  '/static/')
STATIC_ROOT     = ENV.get('STATIC_ROOT', str(BASE_DIR / 'staticfiles'))
STATICFILES_DIRS = [BASE_DIR / 'static']

# WhiteNoise — يخدم static files مباشرة بدون Nginx في التطوير
STATICFILES_STORAGE = (
    'django.contrib.staticfiles.storage.StaticFilesStorage' if DEBUG
    else 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
)

MEDIA_URL   = ENV.get('MEDIA_URL',   '/media/')
MEDIA_ROOT  = ENV.get('MEDIA_ROOT',  str(BASE_DIR / 'media'))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==================== إعدادات الموقع ====================
SITE_ID                  = 1
SITE_NAME                = 'جمعية نسائم فلسطين الخيرية'
SITE_URL = ENV.get('SITE_URL', 'http://127.0.0.1:8000' if DEBUG else 'https://nasaeem-palestine.com')
ORGANIZATION_NAME        = 'جمعية نسائم فلسطين الخيرية'
ORGANIZATION_DESCRIPTION = 'جمعية خيرية تنموية إنسانية تعمل على خدمة المجتمع الفلسطيني منذ 2013'

# ==================== Crispy Forms ====================
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK          = "bootstrap5"

# ==================== CKEditor ====================
CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': {
            'items': [
                'heading', '|', 'bold', 'italic', 'underline', '|',
                'link', 'bulletedList', 'numberedList', '|',
                'imageUpload', 'insertTable', '|', 'undo', 'redo',
            ],
            'shouldNotGroupWhenFull': True,
        },
        'language': 'ar',
    }
}
CKEDITOR_5_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
CKEDITOR_5_UPLOAD_PATH  = "uploads/ckeditor/"

# ==================== REST Framework ====================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES':     ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_PAGINATION_CLASS':       'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
}

# ==================== البريد الإلكتروني ====================
EMAIL_BACKEND       = config('EMAIL_BACKEND',     default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST          = config('EMAIL_HOST',         default='smtp-relay.brevo.com')
EMAIL_PORT          = config('EMAIL_PORT',         default=587, cast=int)
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL  = config('DEFAULT_FROM_EMAIL')

# ==================== الأمان ====================
SECURE_BROWSER_XSS_FILTER   = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS              = 'SAMEORIGIN'
CSRF_COOKIE_SECURE           = not DEBUG
CSRF_COOKIE_HTTPONLY         = False
CSRF_COOKIE_SAMESITE         = 'Lax'

# ==================== رفع الملفات ====================
FILE_UPLOAD_MAX_MEMORY_SIZE = 4 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 4 * 1024 * 1024
MAX_ATTACHMENT_SIZE         = 5 * 1024 * 1024

# ==================== إعدادات مخصصة ====================
PROJECTS_PER_PAGE    = 12
PAGINATE_BY          = 30
CONTACT_ENABLE_PHONE = True

# ==================== Celery ====================
CELERY_BROKER_URL      = ENV.get('CELERY_BROKER_URL',    'redis://localhost:6379/0')
CELERY_RESULT_BACKEND  = ENV.get('CELERY_RESULT_BACKEND','redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT  = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE        = TIME_ZONE

# ==================== Logging ====================
LOGS_DIR = BASE_DIR / 'logs'
os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {module}: {message}',
            'style':  '{',
        },
        'simple': {
            'format': '{levelname}: {message}',
            'style':  '{',
        },
    },
    'handlers': {
        'console': {
            'class':     'logging.StreamHandler',
            'formatter': 'simple' if not DEBUG else 'verbose',
            'level':     'DEBUG' if DEBUG else 'ERROR',
        },
        'file': {
            'class':     'logging.handlers.RotatingFileHandler',  # ← أفضل من FileHandler العادي
            'filename':  str(LOGS_DIR / 'nasaeem.log'),
            'formatter': 'verbose',
            'encoding':  'utf-8',
            'level':     'INFO',
            'maxBytes':  10 * 1024 * 1024,   # 10 MB حد أقصى للملف
            'backupCount': 5,                  # احتفظ بـ 5 نسخ قديمة
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level':    'INFO',
    },
    'loggers': {
        'django': {
            'handlers':  ['console', 'file'],
            'level':     'INFO',
            'propagate': False,
        },
        # إسكات المكتبات الثرثارة
        'weasyprint':         {'handlers': ['file'], 'level': 'ERROR', 'propagate': False},
        'fontTools':          {'handlers': ['file'], 'level': 'ERROR', 'propagate': False},
        'fontTools.ttLib':    {'handlers': ['file'], 'level': 'ERROR', 'propagate': False},
        'fontTools.subset':   {'handlers': ['file'], 'level': 'ERROR', 'propagate': False},
        'PIL':                {'handlers': ['file'], 'level': 'ERROR', 'propagate': False},
        'django.db.backends': {
            'handlers':  ['file'],
            'level':     'DEBUG' if DEBUG else 'ERROR',  # اعرض SQL فقط في التطوير
            'propagate': False,
        },
    },
}

# ==================== Message Tags ====================
MESSAGE_TAGS = {
    messages.DEBUG:   'debug',
    messages.INFO:    'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR:   'danger',
}

# ==================== إنشاء المجلدات المطلوبة ====================
_dirs = [
    'logs', 'media', 'media/projects/main', 'media/projects/images',
    'media/projects/videos/thumbnails', 'media/projects/documents',
    'media/categories', 'media/uploads/ckeditor',
    'media/sponsors/photos', 'media/sponsors/receipts',
    'media/orphans', 'media/specials', 'media/families',
    'media/profiles', 'staticfiles',
]
for d in _dirs:
    (BASE_DIR / d).mkdir(parents=True, exist_ok=True)

# ==================== إعدادات الإنتاج ====================

# Cache — Redis على السيرفر، LocMem محلياً تلقائياً
if ENV.get('REDIS_CACHE_URL'):
    CACHES = {
        'default': {
            'BACKEND':    'django.core.cache.backends.redis.RedisCache',
            'LOCATION':   ENV.get('REDIS_CACHE_URL'),
            'TIMEOUT':    300,
            'KEY_PREFIX': 'nasaeem',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND':  'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'nasaeem-cache',
            'TIMEOUT':  300,
            'OPTIONS':  {'MAX_ENTRIES': 2000, 'CULL_FREQUENCY': 4},
        }
    }

if not DEBUG:
    # قاعدة البيانات — اتصال دائم في الإنتاج
    DATABASES['default']['CONN_MAX_AGE'] = 600

    # HTTPS
    SECURE_SSL_REDIRECT            = True
    SECURE_HSTS_SECONDS            = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD            = True
# ==================== CSRF Failure View ====================
CSRF_FAILURE_VIEW = 'main.views.custom_csrf_failure'