from pathlib import Path
BASE_DIR=Path(__file__).resolve().parent.parent
SECRET_KEY='change-this-for-production'
DEBUG=True
ALLOWED_HOSTS=['127.0.0.1','localhost','*']
INSTALLED_APPS=['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','tracker']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF='presence_core.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION='presence_core.wsgi.application'
DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'db.sqlite3'}}
AUTH_PASSWORD_VALIDATORS=[]
LANGUAGE_CODE='en-us'; TIME_ZONE='Asia/Kolkata'; USE_I18N=True; USE_TZ=True
STATIC_URL='/static/'; STATIC_ROOT=BASE_DIR/'staticfiles'; MEDIA_URL='/media/'; MEDIA_ROOT=BASE_DIR/'media'
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
LOGIN_URL='/admin-login/'; LOGIN_REDIRECT_URL='/admin-panel/'; LOGOUT_REDIRECT_URL='/'

# Honor the original request scheme when running behind a trusted HTTPS development proxy.
# Configure the proxy to overwrite this header; do not trust arbitrary client-supplied values.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# Permit the two standard local development origins. Codespaces/remote HTTPS
# origins should be added via the CSRF_TRUSTED_ORIGINS environment variable.
_local_csrf_origins = ['http://localhost:8000', 'http://127.0.0.1:8000'] if DEBUG else []
_env_csrf_origins = [
    origin.strip()
    for origin in __import__('os').environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]
CSRF_TRUSTED_ORIGINS = _local_csrf_origins + _env_csrf_origins
