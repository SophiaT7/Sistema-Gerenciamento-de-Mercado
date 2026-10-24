"""
Django settings for config project.
Supermarket Management System with BCE Architecture
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-=b*+rb4#*(bu$!fkel%zivrr!#=5n+8$^4@rh72i$=6u4ike@l'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    # Jazzmin deve vir antes do admin
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # App do sistema de mercado
    'mercado',
]

AUTH_USER_MODEL = 'mercado.Usuario'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'mercado.context_processors.alertas_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# Default: SQLite (perfeito para dev local e fácil de trocar para PostgreSQL em produção gratuita)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 4},
    },
]

# Internationalization - Brasil
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# ==========================================
# CONFIGURAÇÕES AVANÇADAS DO JAZZMIN (ADMIN)
# ==========================================
JAZZMIN_SETTINGS = {
    # Título da janela do navegador
    "site_title": "Mercado Gestão",
    # Cabeçalho no painel admin
    "site_header": "Mercado Central",
    # Marca do painel
    "site_brand": "Mercado Gestão",
    # Logo do site (ícone de boas-vindas)
    "welcome_sign": "Bem-vindo ao Sistema de Gestão do Mercado",
    # Copyright
    "copyright": "Mercado Gestão & Engenharia de Software",
    # Modelo de busca rápida no topo
    "search_model": ["mercado.Produto", "mercado.Venda"],
    
    # Links rápidos no topo
    "topmenu_links": [
        {"name": "Início / Dashboard", "url": "dashboard", "permissions": ["auth.view_user"]},
        {"name": "Ponto de Venda (PDV)", "url": "pdv", "permissions": ["mercado.add_venda"]},
        {"name": "Frente de Caixa", "url": "caixa_status", "permissions": ["mercado.add_caixa"]},
        {"name": "Entrada de Mercadoria", "url": "entrada_mercadoria", "permissions": ["mercado.add_entradamercadoria"]},
    ],

    # Organização do menu lateral (User Interface)
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],

    # Ícones dos Modelos (FontAwesome)
    "icons": {
        "auth": "fas fa-users-cog",
        "mercado.Usuario": "fas fa-user-tie",
        "mercado.Produto": "fas fa-box-open",
        "mercado.Lote": "fas fa-boxes",
        "mercado.EntradaMercadoria": "fas fa-truck-loading",
        "mercado.Caixa": "fas fa-cash-register",
        "mercado.Venda": "fas fa-shopping-cart",
        "mercado.ItemVenda": "fas fa-receipt",
        "mercado.Perda": "fas fa-trash-alt",
        "mercado.MovimentacaoEstoque": "fas fa-exchange-alt",
        "mercado.Alerta": "fas fa-bell",
    },
    
    # Ordem dos apps/modelos
    "order_with_respect_to": [
        "mercado.Produto",
        "mercado.Lote",
        "mercado.EntradaMercadoria",
        "mercado.Caixa",
        "mercado.Venda",
        "mercado.Perda",
        "mercado.Alerta",
        "mercado.MovimentacaoEstoque",
        "mercado.Usuario",
    ],
    
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    
    # Tema escuro/claro
    "show_ui_builder": False,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-primary",
    "navbar": "navbar-dark navbar-navy",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-navy",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "flatly",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}
