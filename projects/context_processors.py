# projects/context_processors.py

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext as _
from django.db.models import Count, Q
import logging

logger = logging.getLogger(__name__)


def _get_lang(request):
    return getattr(request, 'LANGUAGE_CODE', settings.LANGUAGE_CODE)


# ==========================================
# Processor موحّد — يغني عن 4 processors
# ==========================================

def project_context(request):
    """
    معالج موحّد: إحصائيات + فئات + مشاريع مميزة + تنقل + meta + اقتراحات بحث
    يغني عن: project_context, project_navigation, project_meta, project_search_suggestions
    """
    try:
        if 'projects' not in settings.INSTALLED_APPS:
            return {}

        from .models import Project, ProjectCategory

        lang      = _get_lang(request)
        cache_key = f'project_ctx_{lang}'
        cached    = cache.get(cache_key)
        if cached:
            return cached

        # ── الفئات (query واحدة تخدم كل الحاجات) ──
        all_categories = list(
            ProjectCategory.objects.filter(is_active=True).annotate(
                projects_count=Count('projects', filter=Q(projects__is_active=True))
            ).order_by('order', 'name_ar')
        )
        active_categories = [c for c in all_categories if c.projects_count > 0]

        # ── إحصائيات المشاريع (query واحدة) ──
        from django.db.models import Sum
        stats_qs = Project.objects.filter(is_active=True).aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
            active=Count('id', filter=Q(status='active')),
            featured=Count('id', filter=Q(is_featured=True)),
        )

        # ── قوائم المشاريع (queries مجمّعة) ──
        featured_projects = list(
            Project.objects.filter(is_active=True, is_featured=True)
            .select_related('category').order_by('-created_at')[:5]
        )
        recent_projects = list(
            Project.objects.filter(is_active=True)
            .select_related('category').order_by('-created_at')[:6]
        )
        popular_projects = list(
            Project.objects.filter(is_active=True)
            .select_related('category').order_by('-views_count')[:5]
        )

        # ── الكلمات المفتاحية (بدون query إضافية) ──
        popular_keywords = [
            _('مشاريع تعليمية'), _('مساعدات طبية'), _('كفالة أيتام'),
            _('مساعدات غذائية'), _('مشاريع إسكان'), _('مساعدات شتوية'),
        ]

        # ── قائمة التنقل (من الفئات المحمّلة بالفعل) ──
        project_nav_items = [
            {'title': _('جميع المشاريع'), 'url': 'projects:all_projects',    'icon': 'fas fa-th-large'},
            {'title': _('البحث'),          'url': 'projects:search_projects', 'icon': 'fas fa-search'},
        ]
        for cat in active_categories[:8]:
            project_nav_items.append({
                'title':         cat.name_ar,
                'url':           'projects:category_projects',
                'url_kwargs':    {'slug': cat.slug},
                'icon':          cat.icon or 'fas fa-folder',
                'projects_count': cat.projects_count,
            })

        context_data = {
            # إحصائيات
            'projects_stats': {
                'total_projects':       stats_qs['total'],
                'completed_projects':   stats_qs['completed'],
                'active_projects':      stats_qs['active'],
                'featured_projects_count': stats_qs['featured'],
            },

            # قوائم المشاريع
            'featured_projects_sidebar': featured_projects,
            'recent_projects_sidebar':   recent_projects,
            'popular_projects_sidebar':  popular_projects,

            # الفئات
            'active_categories_sidebar': active_categories[:10],
            'project_categories_nav':    active_categories[:8],

            # التنقل
            'project_nav_items': project_nav_items,

            # البحث
            'popular_project_keywords': popular_keywords,

            # Meta & SEO
            'project_meta': {
                'default_project_image': getattr(settings, 'DEFAULT_PROJECT_IMAGE', '/static/images/default-project.jpg'),
                'project_author':        getattr(settings, 'SITE_AUTHOR', _('جمعية نسائم فلسطين الخيرية')),
                'project_og_type':       'website',
                'project_twitter_card':  'summary_large_image',
            },

            # إعدادات
            'project_settings': {
                'show_featured_badge': True,
                'show_status_badge':   True,
                'enable_like_system':  True,
                'enable_share_system': True,
                'items_per_page':      getattr(settings, 'PROJECTS_PER_PAGE', 12),
            },

            # روابط سريعة
            'quick_links': {
                'all_projects':   'projects:all_projects',
                'project_search': 'projects:search_projects',
            },

            # اقتراحات البحث
            'project_search_suggestions': popular_keywords,
        }

        cache.set(cache_key, context_data, 60 * 15)
        return context_data

    except Exception as e:
        logger.error(f'project_context error: {e}', exc_info=True)
        return {'projects_stats': {'total_projects':0,'completed_projects':0,'active_projects':0,'featured_projects_count':0}}


# ==========================================
# Breadcrumbs (سريع — DB فقط عند الحاجة)
# ==========================================

def project_breadcrumbs(request):
    try:
        crumbs = [{'title': _('الرئيسية'), 'url': '/', 'icon': 'fas fa-home'}]
        path   = request.path

        if '/projects/' not in path:
            return {'project_breadcrumbs': crumbs}

        crumbs.append({'title': _('المشاريع'), 'url': '/projects/', 'icon': 'fas fa-project-diagram'})

        if '/project/' in path:
            try:
                from .models import Project
                slug    = path.split('/')[-2]
                project = Project.objects.only('title_ar').get(slug=slug, is_active=True)
                crumbs.append({'title': project.title_ar, 'url': path, 'icon': 'fas fa-file-alt', 'current': True})
            except Exception:
                pass

        elif '/category/' in path:
            try:
                from .models import ProjectCategory
                slug     = path.split('/')[-2]
                category = ProjectCategory.objects.only('name_ar').get(slug=slug, is_active=True)
                crumbs.append({'title': category.name_ar, 'url': path, 'icon': 'fas fa-folder', 'current': True})
            except Exception:
                pass

        elif '/search/' in path:
            crumbs.append({'title': _('نتائج البحث'), 'url': path, 'icon': 'fas fa-search', 'current': True})

        return {'project_breadcrumbs': crumbs}

    except Exception as e:
        logger.error(f'project_breadcrumbs error: {e}')
        return {'project_breadcrumbs': []}


# ==========================================
# Aliases للتوافق مع settings.py القديم
# ==========================================

def project_navigation(request):
    return {}   # مدمج في project_context

def project_meta(request):
    return {}   # مدمج في project_context

def project_search_suggestions(request):
    return {}   # مدمج في project_context


# ==========================================
# Cache Management
# ==========================================

def clear_project_context_cache():
    try:
        for lang in [l[0] for l in settings.LANGUAGES]:
            cache.delete(f'project_ctx_{lang}')
        return True
    except Exception as e:
        logger.error(f'clear_project_context_cache error: {e}')
        return False


__all__ = [
    'project_context',
    'project_breadcrumbs',
    'project_navigation',
    'project_meta',
    'project_search_suggestions',
    'clear_project_context_cache',
]
