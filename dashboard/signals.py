# dashboard/signals.py

from django.db.models.signals import post_save, pre_delete, post_delete
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.auth import get_user_model
from django.dispatch import receiver, Signal
from django.utils import timezone
from django.core.cache import cache
import logging

from .models import UserProfile, ActivityLog
from .utils import get_client_ip, get_user_agent
from main.models import SiteSettings
from projects.models import Project
from contact.models import ContactMessage


def get_user_model_lazy():
    return get_user_model()


@receiver(post_save)
def create_user_profile(sender, instance, created, **kwargs):
    """إنشاء ملف شخصي تلقائياً للمستخدمين الجدد"""
    User = get_user_model()
    if sender != User:
        return
    if created:
        if instance.is_superuser:
            role = 'super_admin'
        elif instance.is_staff:
            role = 'admin'
        else:
            role = 'viewer'

        UserProfile.objects.get_or_create(
            user=instance,
            defaults={
                'role': role,
                'full_name_ar': instance.get_full_name() or instance.username,
                'is_active_staff': instance.is_staff
            }
        )


@receiver(user_logged_in)
def user_login_handler(sender, request, user, **kwargs):
    """معالج تسجيل الدخول"""
    try:
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'role': 'super_admin' if user.is_superuser else ('admin' if user.is_staff else 'viewer'),
                'full_name_ar': user.get_full_name() or user.username,
                'is_active_staff': user.is_staff
            }
        )

        profile.login_count += 1
        profile.last_login_ip = get_client_ip(request)
        profile.last_activity = timezone.now()
        profile.save(update_fields=['login_count', 'last_login_ip', 'last_activity'])

    except Exception as e:
        logging.getLogger(__name__).warning(f"فشل في تحديث الملف الشخصي لـ {user.username}: {e}")

    try:
        ActivityLog.log_activity(
            user=user,
            action='login',
            title='تسجيل دخول',
            description=f'دخل المستخدم من IP: {get_client_ip(request)}',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            session_key=request.session.session_key if hasattr(request, 'session') else ''
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"فشل في تسجيل نشاط الدخول لـ {user.username}: {e}")


@receiver(user_logged_out)
def user_logout_handler(sender, request, user, **kwargs):
    """معالج تسجيل الخروج"""
    if user and user.is_authenticated:
        try:
            ActivityLog.log_activity(
                user=user,
                action='logout',
                title='تسجيل خروج',
                description='خرج المستخدم من النظام',
                ip_address=get_client_ip(request) if request else '',
                user_agent=get_user_agent(request) if request else '',
                session_key=request.session.session_key if hasattr(request, 'session') else ''
            )
        except Exception as e:
            logging.getLogger(__name__).error(f"فشل في تسجيل نشاط الخروج لـ {user.username}: {e}")


@receiver(post_save, sender=Project)
def project_saved_handler(sender, instance, created, **kwargs):
    """معالج حفظ المشاريع"""
    try:
        action = 'create' if created else 'update'
        title = f"{'إنشاء' if created else 'تحديث'} مشروع: {instance.title_ar}"

        cache.delete_many(['dashboard_stats', 'featured_projects', 'recent_projects', 'projects_stats'])

        ActivityLog.objects.create(
            user=None,
            username='System',
            action=action,
            title=title,
            description=f'تم {title}',
            content_object=instance,
            level='success' if created else 'info',
            timestamp=timezone.now(),
            user_agent='',
            ip_address='',
            session_key='',
            extra_data={}
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"خطأ في معالج المشاريع: {e}")


@receiver(post_save, sender=ContactMessage)
def contact_message_handler(sender, instance, created, **kwargs):
    """معالج رسائل التواصل الجديدة"""
    if created:
        try:
            cache.delete('dashboard_stats')

            ActivityLog.objects.create(
                user=None,
                username='System',
                action='create',
                title='رسالة تواصل جديدة',
                description=f'رسالة جديدة من: {instance.name} - {instance.subject}',
                content_object=instance,
                level='info',
                timestamp=timezone.now(),
                user_agent='',
                ip_address='',
                session_key='',
                extra_data={
                    'sender_email': instance.email,
                    'message_priority': getattr(instance, 'priority', 'normal')
                }
            )
        except Exception as e:
            logging.getLogger(__name__).error(f"خطأ في معالج رسائل التواصل: {e}")


@receiver(pre_delete)
def user_deletion_handler(sender, instance, **kwargs):
    """معالج حذف المستخدمين"""
    User = get_user_model()
    if sender != User:
        return
    try:
        ActivityLog.objects.create(
            user=None,
            username='System',
            action='delete',
            title=f'حذف المستخدم: {instance.username}',
            description=f'تم حذف المستخدم {instance.username} ({instance.email})',
            level='warning',
            timestamp=timezone.now(),
            user_agent='',
            ip_address='',
            session_key='',
            extra_data={
                'deleted_user_id': str(instance.id),
                'deleted_user_email': instance.email,
                'was_staff': instance.is_staff,
                'was_superuser': instance.is_superuser
            }
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"خطأ في معالج حذف المستخدمين: {e}")


@receiver(post_save, sender=SiteSettings)
def site_settings_updated(sender, instance, **kwargs):
    """معالج تحديث إعدادات الموقع"""
    try:
        cache.delete_many(['site_settings', 'navigation_menu', 'footer_data', 'dashboard_stats'])

        ActivityLog.objects.create(
            user=None,
            username='System',
            action='update',
            title='تحديث إعدادات الموقع',
            description='تم تحديث إعدادات الموقع العامة',
            content_object=instance,
            level='info',
            timestamp=timezone.now(),
            user_agent='',
            ip_address='',
            session_key='',
            extra_data={}
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"خطأ في معالج إعدادات الموقع: {e}")


@receiver(post_delete)
def generic_deletion_handler(sender, instance, **kwargs):
    """معالج عام للحذف"""
    try:
        ignored_models = ['ActivityLog', 'SystemHealth', 'LogEntry']
        if sender.__name__ in ignored_models:
            return

        if hasattr(sender, '_meta') and sender._meta.app_label in ['sessions', 'admin', 'auth', 'contenttypes']:
            return

        ActivityLog.objects.create(
            user=None,
            username='System',
            action='delete',
            title=f'حذف {sender._meta.verbose_name}',
            description=f'تم حذف عنصر من نموذج {sender._meta.verbose_name}',
            level='warning',
            timestamp=timezone.now(),
            user_agent='',
            ip_address='',
            session_key='',
            extra_data={
                'model_name': sender.__name__,
                'app_label': sender._meta.app_label
            }
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"خطأ في المعالج العام للحذف: {e}")


# ==================== إشارات مخصصة ====================

dashboard_access_denied = Signal()
system_health_critical = Signal()
backup_completed = Signal()


@receiver(dashboard_access_denied)
def handle_access_denied(sender, user, request, **kwargs):
    try:
        ActivityLog.log_activity(
            user=user,
            action='view',
            title='محاولة وصول مرفوضة',
            description=f'محاولة وصول غير مصرح بها للوحة التحكم من {user.username if user else "مجهول"}',
            level='warning',
            ip_address=get_client_ip(request) if request else '',
            user_agent=get_user_agent(request) if request else '',
            session_key=request.session.session_key if hasattr(request, 'session') else ''
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"خطأ في معالج رفض الوصول: {e}")


@receiver(system_health_critical)
def handle_system_health_critical(sender, health_data, **kwargs):
    try:
        ActivityLog.objects.create(
            user=None,
            username='System',
            action='warning',
            title='تحذير: حالة النظام حرجة',
            description=f'النظام في حالة حرجة: {health_data.get("status", "unknown")}',
            level='error',
            timestamp=timezone.now(),
            user_agent='',
            ip_address='',
            session_key='',
            extra_data=health_data
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"خطأ في معالج الحالة الحرجة: {e}")


@receiver(backup_completed)
def handle_backup_completed(sender, backup_info, **kwargs):
    try:
        status = 'success' if backup_info.get('success') else 'error'

        ActivityLog.objects.create(
            user=None,
            username='System',
            action='backup',
            title='نسخ احتياطي تلقائي',
            description=f'تم {"إنجاز" if backup_info.get("success") else "فشل"} النسخ الاحتياطي',
            level=status,
            timestamp=timezone.now(),
            user_agent='',
            ip_address='',
            session_key='',
            extra_data=backup_info
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"خطأ في معالج النسخ الاحتياطي: {e}")


@receiver([post_save, post_delete])
def cache_invalidation_handler(sender, instance, **kwargs):
    try:
        cache_sensitive_models = [
            'Project', 'ContactMessage', 'Newsletter',
            'SiteSettings', 'Statistic', 'FAQ'
        ]
        if sender.__name__ in cache_sensitive_models:
            cache.delete_many([
                'dashboard_stats',
                f'{sender.__name__.lower()}_list',
                f'{sender.__name__.lower()}_stats',
                'homepage_data'
            ])
    except Exception as e:
        logging.getLogger(__name__).error(f"خطأ في تنظيف الكاش: {e}")


@receiver(user_logged_in)
def reset_failed_login_attempts(sender, request, user, **kwargs):
    try:
        cache_key = f'failed_login_attempts_{get_client_ip(request)}'
        cache.delete(cache_key)
    except Exception as e:
        logging.getLogger(__name__).error(f"خطأ في إعادة تعيين محاولات الدخول الفاشلة: {e}")


def log_suspicious_activity(user, activity_type, description, request=None):
    try:
        ActivityLog.log_activity(
            user=user,
            action='security',
            title=f'نشاط مشبوه: {activity_type}',
            description=description,
            level='warning',
            ip_address=get_client_ip(request) if request else '',
            user_agent=get_user_agent(request) if request else '',
            session_key=request.session.session_key if hasattr(request, 'session') else '',
            extra_data={
                'activity_type': activity_type,
                'timestamp': timezone.now().isoformat()
            }
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"خطأ في تسجيل النشاط المشبوه: {e}")


# ==================== إشارات المشاريع والإحصائيات ====================

from main.models import Statistic


@receiver(post_save, sender=Project)
def update_statistics_on_project_save(sender, instance, **kwargs):
    """تحديث الإحصائيات تلقائياً عند حفظ مشروع"""
    for stat in Statistic.objects.filter(is_active=True).exclude(auto_update_from__isnull=True):
        stat.update_number()