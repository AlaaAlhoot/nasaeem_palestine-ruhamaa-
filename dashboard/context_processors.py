# dashboard/context_processors.py

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


def _is_dashboard(request):
    """تحقق سريع — يُستخدم في كل processor"""
    return getattr(request, 'user', None) and \
           request.user.is_authenticated and \
           'dashboard' in request.path


# ==========================================
# Processor موحّد — يغني عن 5 processors
# ==========================================

def dashboard_context(request):
    """
    معالج موحّد يجمع: context + statistics + notifications + quick_actions + system_info + menu
    """
    if not _is_dashboard(request):
        return {}

    try:
        from .models import UserProfile, SiteSetting, ActivityLog, SystemHealth, QuickAction
        from contact.models import ContactMessage, Newsletter
        from projects.models import Project

        user = request.user
        cache_key = f'dashboard_ctx_{user.id}'
        cached = cache.get(cache_key)
        if cached:
            # current_path لا يُكش لأنه يتغير
            cached['current_path'] = request.path
            return cached

        # ── الملف الشخصي ──
        try:
            user_profile = user.profile
        except Exception:
            role = 'super_admin' if user.is_superuser else ('admin' if user.is_staff else 'viewer')
            user_profile = UserProfile.objects.create(
                user=user,
                role=role,
                full_name_ar=user.get_full_name() or user.username,
                is_active_staff=user.is_staff,
            )

        dashboard_settings = SiteSetting.objects.filter(pk=1).first()
        is_admin = user_profile.is_admin() or user.is_superuser

        # ── الإحصائيات (queries مجمّعة) ──
        today     = timezone.now().date()
        week_ago  = today - timedelta(days=7)

        new_messages_count   = ContactMessage.objects.filter(status='new').count()
        urgent_messages      = ContactMessage.objects.filter(priority='urgent', status__in=['new','reading']).count()
        active_projects      = Project.objects.filter(status='active', is_active=True).count()
        pending_newsletter   = Newsletter.objects.filter(is_active=True, confirmed_at__isnull=True).count()
        recent_activities    = ActivityLog.objects.filter(
            timestamp__gte=timezone.now() - timedelta(hours=24)
        ).count()
        total_users  = user.__class__.objects.count()
        online_users = user.__class__.objects.filter(
            profile__last_activity__gte=timezone.now() - timedelta(minutes=15)
        ).count()

        # ── الإشعارات (بدون queries إضافية) ──
        notifications = []
        if new_messages_count > 0:
            notifications.append({
                'type': 'info', 'icon': 'fas fa-envelope',
                'message': f'لديك {new_messages_count} رسالة جديدة',
                'url': '/dashboard/messages/', 'count': new_messages_count,
            })
        pending_projects = Project.objects.filter(status='planning', is_active=True).count()
        if pending_projects > 0:
            notifications.append({
                'type': 'warning', 'icon': 'fas fa-clock',
                'message': f'{pending_projects} مشروع في انتظار التفعيل',
                'url': '/dashboard/projects/', 'count': pending_projects,
            })
        last_health = SystemHealth.objects.order_by('-checked_at').first()
        if last_health and last_health.status != 'healthy':
            notifications.append({
                'type': 'danger', 'icon': 'fas fa-exclamation-triangle',
                'message': f'تحذير: حالة النظام {last_health.get_status_display()}',
                'url': '/dashboard/system-health/', 'count': 1,
            })
        if is_admin:
            new_users = user.__class__.objects.filter(date_joined__gte=week_ago).count()
            if new_users > 0:
                notifications.append({
                    'type': 'success', 'icon': 'fas fa-user-plus',
                    'message': f'{new_users} مستخدم جديد هذا الأسبوع',
                    'url': '/dashboard/users/', 'count': new_users,
                })

        # ── الإجراءات السريعة ──
        user_role = getattr(user_profile, 'role', 'viewer')
        if user.is_superuser or user_role == 'super_admin':
            quick_actions = list(QuickAction.objects.filter(is_active=True).order_by('order')[:8])
        else:
            quick_actions = list(QuickAction.objects.filter(
                is_active=True
            ).filter(
                Q(required_role='') | Q(required_role=user_role) | Q(required_role__isnull=True)
            ).order_by('order')[:8])

        # ── نشاط المستخدم ──
        user_activities = list(ActivityLog.objects.filter(user=user).order_by('-timestamp')[:5])
        total_activities = ActivityLog.objects.filter(user=user).count()

        # ── معلومات النظام ──
        system_info = {
            'debug_mode':        settings.DEBUG,
            'site_name':         getattr(settings, 'SITE_NAME', 'Dashboard'),
            'current_time':      timezone.now(),
            'maintenance_mode': dashboard_settings.maintenance_mode if dashboard_settings else False,
            'system_status':     last_health.status if last_health else 'unknown',
            'last_health_check': last_health.checked_at if last_health else None,
        }

        # ── القائمة الجانبية ──
        can_edit = user_profile.can_edit_content() or user.is_superuser
        menu_items = [
            {'title': 'الرئيسية',   'url': '/dashboard/',           'icon': 'fas fa-tachometer-alt'},
            {'title': 'التحليلات',  'url': '/dashboard/analytics/', 'icon': 'fas fa-chart-line'},
        ]
        if can_edit:
            menu_items += [
                {'title': 'المحتوى',  'url': '/dashboard/content/',  'icon': 'fas fa-edit'},
                {'title': 'التقارير', 'url': '/dashboard/reports/',  'icon': 'fas fa-file-alt'},
            ]
        if is_admin:
            menu_items += [
                {'title': 'المستخدمين', 'url': '/dashboard/users/',    'icon': 'fas fa-users'},
                {'title': 'الإعدادات',  'url': '/dashboard/settings/', 'icon': 'fas fa-cogs'},
            ]
        menu_items += [
            {'title': 'الموقع الرئيسي', 'url': '/',        'icon': 'fas fa-home',         'external': True},
            {'title': 'تسجيل خروج',     'url': '/logout/', 'icon': 'fas fa-sign-out-alt'},
        ]

        context_data = {
            # الملف الشخصي
            'user_profile':      user_profile,
            'dashboard_settings': dashboard_settings,
            'user_role':         user_role,
            'dashboard_theme':   user_profile.dashboard_theme,
            'user_permissions': {
                'is_admin':         is_admin,
                'can_edit_content': can_edit,
                'is_active_staff':  user_profile.is_active_staff,
                'is_superuser':     user.is_superuser,
            },

            # الإحصائيات
            'dashboard_stats': {
                'new_messages_count':      new_messages_count,
                'urgent_messages_count':   urgent_messages,
                'active_projects_count':   active_projects,
                'pending_newsletter_count': pending_newsletter,
                'recent_activities_count': recent_activities,
                'total_users':             total_users,
                'online_users':            online_users,
            },

            # الإشعارات
            'dashboard_notifications': notifications,

            # الإجراءات السريعة
            'dashboard_quick_actions': quick_actions,

            # نشاط المستخدم
            'dashboard_user_activity': {
                'recent_activities': user_activities,
                'total_activities':  total_activities,
                'login_count':       getattr(user_profile, 'login_count', 0),
                'last_activity':     getattr(user_profile, 'last_activity', None),
                'is_online':         True,
            },

            # معلومات النظام
            'dashboard_system_info': system_info,

            # القائمة
            'dashboard_menu_items': menu_items,
        }

        # cache لمدة 5 دقائق
        cache.set(cache_key, context_data, 60 * 5)
        context_data['current_path'] = request.path
        return context_data

    except Exception as e:
        logger.error(f'dashboard_context error: {e}', exc_info=True)
        return {
            'user_permissions': {
                'is_admin':         request.user.is_superuser,
                'can_edit_content': request.user.is_staff,
                'is_active_staff':  request.user.is_staff,
                'is_superuser':     request.user.is_superuser,
            }
        }


# ==========================================
# Breadcrumbs (لا يحتاج cache — سريع جداً)
# ==========================================

def dashboard_breadcrumbs(request):
    if not _is_dashboard(request):
        return {}

    section_map = {
        'analytics':     {'title': 'التحليلات',       'icon': 'fas fa-chart-line'},
        'users':         {'title': 'المستخدمين',       'icon': 'fas fa-users'},
        'content':       {'title': 'المحتوى',          'icon': 'fas fa-edit'},
        'settings':      {'title': 'الإعدادات',        'icon': 'fas fa-cogs'},
        'reports':       {'title': 'التقارير',         'icon': 'fas fa-file-alt'},
        'messages':      {'title': 'الرسائل',          'icon': 'fas fa-envelope'},
        'projects':      {'title': 'المشاريع',         'icon': 'fas fa-project-diagram'},
        'profile':       {'title': 'الملف الشخصي',    'icon': 'fas fa-user'},
        'activity-log':  {'title': 'سجل الأنشطة',     'icon': 'fas fa-list'},
        'system-health': {'title': 'صحة النظام',       'icon': 'fas fa-heartbeat'},
    }

    crumbs = [{'title': 'لوحة التحكم', 'url': '/dashboard/', 'icon': 'fas fa-tachometer-alt'}]
    current = '/dashboard/'

    for part in request.path.strip('/').split('/')[1:]:
        if part in section_map:
            current += f'{part}/'
            crumbs.append({**section_map[part], 'url': current})

    return {'dashboard_breadcrumbs': crumbs}


# ==========================================
# Aliases للتوافق مع settings.py
# ==========================================

def dashboard_statistics(request):
    return {}   # مدمج في dashboard_context

def dashboard_notifications(request):
    return {}   # مدمج في dashboard_context

def dashboard_quick_actions(request):
    return {}   # مدمج في dashboard_context

def dashboard_system_info(request):
    return {}   # مدمج في dashboard_context


__all__ = [
    'dashboard_context',
    'dashboard_breadcrumbs',
    'dashboard_statistics',
    'dashboard_notifications',
    'dashboard_quick_actions',
    'dashboard_system_info',
]
