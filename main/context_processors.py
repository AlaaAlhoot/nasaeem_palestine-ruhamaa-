# main/context_processors.py

from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Q
import logging

from .models import SiteSettings, Goal, BoardMember, Statistic

logger = logging.getLogger(__name__)


def _get_lang(request):
    return getattr(request, 'LANGUAGE_CODE', settings.LANGUAGE_CODE)


# ==========================================
# Processor موحّد — يغني عن site_settings + navigation_data + statistics_data
# ==========================================

def site_settings(request):
    """
    معالج موحّد: إعدادات الموقع + التنقل + الإحصائيات
    Cache مشترك لا يعتمد على request.path
    """
    lang = _get_lang(request)
    cache_key = f'main_ctx_{lang}'
    cached = cache.get(cache_key)

    if cached:
        # أضف القيم الديناميكية بدون كسر الـ cache
        cached['current_path'] = request.path
        return cached

    try:
        site_settings_obj = SiteSettings.get_settings()

        # ── المشاريع ──
        try:
            from projects.models import ProjectCategory, Project
            project_categories = list(
                ProjectCategory.objects.filter(is_active=True).order_by('order')[:10]
            )
            recent_projects = list(
                Project.objects.filter(is_active=True).order_by('-created_at')[:3]
            )
            total_projects = Project.objects.filter(is_active=True).count()

            # فئات التنقل مع عدد المشاريع
            from django.db.models import Count
            nav_categories = []
            for cat in ProjectCategory.objects.filter(is_active=True).annotate(
                projects_count=Count('projects', filter=Q(projects__is_active=True))
            ).filter(projects_count__gt=0).order_by('order')[:8]:
                nav_categories.append({
                    'name':           cat.name_ar,
                    'name_en':        cat.name_en,
                    'slug':           cat.slug,
                    'icon':           cat.icon,
                    'projects_count': cat.projects_count,
                    'url':            f'/projects/category/{cat.slug}/',
                })
        except Exception:
            project_categories = []
            recent_projects    = []
            total_projects     = 0
            nav_categories     = []

        # ── الإحصائيات ──
        try:
            main_statistics = list(Statistic.objects.filter(is_active=True).order_by('order')[:4])
            stats_dict = {}
            for stat in main_statistics:
                key = stat.title_ar.lower().replace(' ','_').replace('عدد_','').replace('إجمالي_','')
                stats_dict[key] = {
                    'title':     stat.title_ar,
                    'title_en':  stat.title_en,
                    'number':    stat.number,
                    'formatted': stat.get_formatted_number(),
                    'suffix':    stat.suffix_ar or '',
                    'icon':      stat.icon,
                    'color':     stat.color,
                }
        except Exception:
            main_statistics = []
            stats_dict      = {}

        # ── الصفحات النشطة ──
        active_pages = {
            'about':   True,
            'vision':  True,
            'goals':   Goal.objects.filter(is_active=True).exists(),
            'board':   BoardMember.objects.filter(is_active=True).exists(),
            'contact': True,
        }

        now = timezone.now()
        established_year = getattr(site_settings_obj, 'established_year', 2013)

        data = {
            # إعدادات الموقع
            'site_settings':      site_settings_obj,
            'project_categories': project_categories,
            'recent_projects':    recent_projects,
            'quick_stats': {
                'total_goals':              Goal.objects.filter(is_active=True).count(),
                'total_board_members':      BoardMember.objects.filter(is_active=True).count(),
                'current_year':             now.year,
                'years_since_establishment': now.year - established_year,
            },
            'LANGUAGES':   settings.LANGUAGES,
            'DEBUG':       settings.DEBUG,
            'MEDIA_URL':   settings.MEDIA_URL,
            'STATIC_URL':  settings.STATIC_URL,

            # التنقل
            'nav_categories':  nav_categories,
            'total_projects':  total_projects,
            'active_pages':    active_pages,

            # الإحصائيات
            'main_statistics': main_statistics,
            'stats_dict':      stats_dict,
            'additional_stats': {
                'establishment_years': now.year - established_year,
                'current_year':        now.year,
            },
        }

        cache.set(cache_key, data, 60 * 15)
        data['current_path'] = request.path
        data['LANGUAGE_CODE'] = lang
        return data

    except Exception as e:
        logger.error(f'site_settings processor error: {e}', exc_info=True)
        now = timezone.now()
        return {
            'site_settings':    None,
            'project_categories': [],
            'recent_projects':  [],
            'quick_stats': {
                'total_goals': 0, 'total_board_members': 0,
                'current_year': now.year, 'years_since_establishment': now.year - 2013,
            },
            'LANGUAGE_CODE': lang,
            'LANGUAGES':     settings.LANGUAGES,
            'DEBUG':         settings.DEBUG,
            'MEDIA_URL':     settings.MEDIA_URL,
            'STATIC_URL':    settings.STATIC_URL,
            'nav_categories': [],
            'total_projects': 0,
            'active_pages':   {'about':True,'vision':True,'goals':True,'board':True,'contact':True},
            'main_statistics': [],
            'stats_dict':      {},
            'additional_stats': {'establishment_years': now.year-2013, 'current_year': now.year},
            'current_path':   request.path,
        }


# ==========================================
# تفضيلات المستخدم (لا تحتاج cache)
# ==========================================

def user_preferences(request):
    lang = _get_lang(request)
    if not hasattr(request, 'session'):
        return {'user_preferences': {
            'user_language': lang,
            'theme':         'light',
            'is_rtl':        lang in ('ar','he','fa'),
            'font_family':   'Cairo' if lang == 'ar' else 'Inter',
        }}

    user_language = request.session.get('django_language', lang)
    return {'user_preferences': {
        'user_language': user_language,
        'theme':         request.COOKIES.get('theme', 'light'),
        'is_rtl':        user_language in ('ar','he','fa'),
        'font_family':   'Cairo' if user_language == 'ar' else 'Inter',
    }}


# ==========================================
# Breadcrumbs (سريع — بدون DB)
# ==========================================

def breadcrumbs(request):
    page_map = {
        'about':     {'title': 'من نحن',          'title_en': 'About Us'},
        'vision':    {'title': 'رؤيتنا',           'title_en': 'Our Vision'},
        'goals':     {'title': 'الأهداف',          'title_en': 'Goals'},
        'board':     {'title': 'مجلس الإدارة',     'title_en': 'Board of Directors'},
        'contact':   {'title': 'اتصل بنا',         'title_en': 'Contact Us'},
        'projects':  {'title': 'المشاريع',         'title_en': 'Projects'},
        'dashboard': {'title': 'لوحة التحكم',      'title_en': 'Dashboard'},
        'search':    {'title': 'البحث',             'title_en': 'Search'},
    }

    crumbs = [{'title': 'الرئيسية', 'url': '/'}]
    current_url = ''

    for segment in request.path.strip('/').split('/'):
        if segment and segment in page_map:
            current_url += f'/{segment}'
            crumbs.append({
                **page_map[segment],
                'url':       current_url,
                'is_active': False,
            })

    if len(crumbs) > 1:
        crumbs[-1]['is_active'] = True
        crumbs[-1]['url']       = None

    return {'breadcrumbs': crumbs}


# ==========================================
# SEO (بدون build_absolute_uri في الـ cache)
# ==========================================

def seo_data(request):
    lang  = _get_lang(request)
    path  = request.path.strip('/')

    try:
        current_url = request.build_absolute_uri()
    except Exception:
        current_url = '/'

    page_titles = {
        '':         'الصفحة الرئيسية - جمعية نسائم فلسطين الخيرية',
        'about':    'من نحن - جمعية نسائم فلسطين الخيرية',
        'contact':  'اتصل بنا - جمعية نسائم فلسطين الخيرية',
        'projects': 'المشاريع - جمعية نسائم فلسطين الخيرية',
    }

    return {'seo_data': {
        'site_name':           'جمعية نسائم فلسطين الخيرية',
        'site_name_en':        'Nasaeem Palestine Charity',
        'default_description': 'جمعية نسائم فلسطين الخيرية - مؤسسة خيرية تنموية إنسانية تعمل على خدمة المجتمع الفلسطيني منذ 2013',
        'default_keywords':    'جمعية, خيرية, فلسطين, نسائم, تبرعات, مساعدات, أيتام, تنمية, غزة',
        'canonical_url':       current_url,
        'current_language':    lang,
        'page_type':           'website' if not path else 'article',
        'title':               page_titles.get(path.split('/')[0], 'جمعية نسائم فلسطين الخيرية'),
    }}


# ==========================================
# Social Sharing (بدون cache — ديناميكي)
# ==========================================

def social_sharing(request):
    try:
        current_url = request.build_absolute_uri()
    except Exception:
        current_url = '/'

    title = 'جمعية نسائم فلسطين الخيرية'
    return {'social_sharing': {
        'current_url':    current_url,
        'page_title':     title,
        'facebook_share': f'https://www.facebook.com/sharer/sharer.php?u={current_url}',
        'twitter_share':  f'https://twitter.com/intent/tweet?url={current_url}&text={title}',
        'whatsapp_share': f'https://wa.me/?text={title} {current_url}',
        'telegram_share': f'https://t.me/share/url?url={current_url}&text={title}',
    }}


# ==========================================
# Aliases للتوافق مع settings.py القديم
# ==========================================

def navigation_data(request):
    return {}   # مدمج في site_settings

def statistics_data(request):
    return {}   # مدمج في site_settings


__all__ = [
    'site_settings',
    'user_preferences',
    'breadcrumbs',
    'seo_data',
    'social_sharing',
    'navigation_data',
    'statistics_data',
]
