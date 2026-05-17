# main/signals.py
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.core.mail import send_mail
from django.conf import settings
import logging
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import (
    SiteSettings, Goal, BoardMember, HomeSlider,
    Statistic, AboutPage, VisionPage
)
from django.db.models import Sum
logger = logging.getLogger('main')


# إشارات تحديث الكاش
@receiver([post_save, post_delete], sender=SiteSettings)
def clear_site_settings_cache(sender, **kwargs):
    """مسح كاش إعدادات الموقع عند التحديث"""
    cache.delete('site_settings')
    cache.delete('navigation_data')
    cache.delete('footer_statistics')
    logger.info("تم مسح كاش إعدادات الموقع")


@receiver([post_save, post_delete], sender=Goal)
def clear_goals_cache(sender, **kwargs):
    """مسح كاش الأهداف عند التحديث"""
    cache.delete('featured_goals')
    cache.delete('navigation_data')
    logger.info("تم مسح كاش الأهداف")


@receiver([post_save, post_delete], sender=BoardMember)
def clear_board_cache(sender, **kwargs):
    """مسح كاش أعضاء مجلس الإدارة"""
    cache.delete('board_members')
    cache.delete('navigation_data')
    logger.info("تم مسح كاش مجلس الإدارة")


@receiver([post_save, post_delete], sender=HomeSlider)
def clear_slider_cache(sender, **kwargs):
    """مسح كاش السلايدر"""
    cache.delete('home_slider')
    logger.info("تم مسح كاش السلايدر")


@receiver([post_save, post_delete], sender=Statistic)
def clear_statistics_cache(sender, **kwargs):
    """مسح كاش الإحصائيات"""
    cache.delete('footer_statistics')
    cache.delete('main_statistics')
    logger.info("تم مسح كاش الإحصائيات")




# إشارات تحديث الإحصائيات التلقائية
@receiver(post_save, sender=Goal)
def update_goals_statistics(sender, instance, created, **kwargs):
    """تحديث إحصائية عدد الأهداف"""
    if created and instance.is_active:
        try:
            goals_stat = Statistic.objects.filter(auto_update_from='goals').first()
            if goals_stat:
                goals_stat.number = Goal.objects.filter(is_active=True).count()
                goals_stat.save()
                logger.info("تم تحديث إحصائية الأهداف تلقائياً")
        except Exception as e:
            logger.error(f"خطأ في تحديث إحصائية الأهداف: {e}")


@receiver(post_save, sender=BoardMember)
def update_board_statistics(sender, instance, created, **kwargs):
    """تحديث إحصائية أعضاء مجلس الإدارة"""
    if created and instance.is_active:
        try:
            board_stat = Statistic.objects.filter(auto_update_from='board_members').first()
            if board_stat:
                board_stat.number = BoardMember.objects.filter(is_active=True).count()
                board_stat.save()
                logger.info("تم تحديث إحصائية أعضاء مجلس الإدارة")
        except Exception as e:
            logger.error(f"خطأ في تحديث إحصائية مجلس الإدارة: {e}")


# إشارات التدقيق والسجلات
@receiver(post_save, sender=SiteSettings)
def log_settings_change(sender, instance, created, **kwargs):
    """تسجيل تغييرات إعدادات الموقع"""
    action = "تم إنشاء" if created else "تم تحديث"
    logger.info(f"{action} إعدادات الموقع - {instance.site_name_ar}")


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """تسجيل دخول المستخدمين"""
    ip_address = get_client_ip(request)
    logger.info(f"تم تسجيل دخول المستخدم {user.username} من IP: {ip_address}")


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """تسجيل خروج المستخدمين"""
    if user:
        logger.info(f"تم تسجيل خروج المستخدم {user.username}")




# إشارات التحقق من البيانات
@receiver(pre_save, sender=SiteSettings)
def validate_site_settings(sender, instance, **kwargs):
    """التحقق من صحة إعدادات الموقع قبل الحفظ"""
    # التحقق من صحة أرقام الهاتف
    if instance.phone and not instance.phone.replace('+', '').replace('-', '').replace(' ', '').isdigit():
        logger.warning(f"رقم هاتف غير صحيح: {instance.phone}")

    # التحقق من صحة الإحداثيات الجغرافية
    if instance.latitude and (instance.latitude < -90 or instance.latitude > 90):
        logger.warning(f"خط عرض غير صحيح: {instance.latitude}")
        instance.latitude = None

    if instance.longitude and (instance.longitude < -180 or instance.longitude > 180):
        logger.warning(f"خط طول غير صحيح: {instance.longitude}")
        instance.longitude = None


@receiver(pre_save, sender=Statistic)
def validate_statistic(sender, instance, **kwargs):
    """التحقق من صحة الإحصائيات قبل الحفظ"""
    if instance.number < 0:
        logger.warning(f"رقم إحصائية سالب: {instance.title_ar}")
        instance.number = 0


# إشارات تحديث خريطة الموقع
@receiver([post_save, post_delete], sender=AboutPage)
@receiver([post_save, post_delete], sender=VisionPage)
@receiver([post_save, post_delete], sender=Goal)
@receiver([post_save, post_delete], sender=BoardMember)
def update_sitemap_cache(sender, **kwargs):
    """تحديث كاش خريطة الموقع"""
    cache.delete('sitemap_urls')
    cache.delete('sitemap_lastmod')
    logger.info("تم تحديث كاش خريطة الموقع")


# دوال مساعدة
def get_client_ip(request):
    """الحصول على عنوان IP الخاص بالمستخدم"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def send_admin_notification(subject, message):
    """إرسال إشعار للمدير"""
    if not settings.DEBUG and hasattr(settings, 'ADMIN_EMAIL'):
        try:
            send_mail(
                subject=f'[جمعية نسائم فلسطين] {subject}',
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"فشل في إرسال إشعار المدير: {e}")


# إشارة مخصصة للمراقبة
class CustomSignals:
    """إشارات مخصصة للتطبيق"""

    @staticmethod
    def content_updated(sender, instance, **kwargs):
        """إشارة عامة عند تحديث المحتوى"""
        cache_keys_to_clear = [
            'site_settings',
            'navigation_data',
            'footer_statistics',
            'main_statistics'
        ]

        for key in cache_keys_to_clear:
            cache.delete(key)

        logger.info(f"تم تحديث المحتوى: {sender.__name__}")

    @staticmethod
    def user_activity(user, action, details=None):
        """تسجيل نشاط المستخدمين"""
        log_message = f"المستخدم {user.username} قام بـ {action}"
        if details:
            log_message += f" - {details}"
        logger.info(log_message)


# ربط الإشارات المخصصة
post_save.connect(CustomSignals.content_updated, sender=SiteSettings)
post_save.connect(CustomSignals.content_updated, sender=Goal)
post_save.connect(CustomSignals.content_updated, sender=BoardMember)
post_save.connect(CustomSignals.content_updated, sender=HomeSlider)
post_save.connect(CustomSignals.content_updated, sender=Statistic)