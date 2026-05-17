from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_migrate
import logging

logger = logging.getLogger(__name__)


class DashboardConfig(AppConfig):
    """تكوين تطبيق لوحة التحكم"""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'
    verbose_name = _('لوحة التحكم')

    def ready(self):
        """تهيئة التطبيق عند بدء التشغيل"""
        try:
            try:
                from . import signals
            except ImportError:
                logger.warning("[!] لم يتم العثور على ملف signals.py")

            try:
                from . import tasks
            except ImportError as e:
                logger.warning(f"[!] Celery غير متاح - تم تخطي المهام المجدولة: {e}")

            post_migrate.connect(self.create_default_data, sender=self)

        except Exception as e:
            logger.error(f"[X] خطأ في تهيئة تطبيق لوحة التحكم: {e}")

    def create_default_data(self, sender, **kwargs):
        """إنشاء البيانات الافتراضية بعد الهجرة"""

        # ✅ الإصلاح 1: استخدام get_user_model بدل User مباشرة
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            try:
                from .models import SiteSetting
                site_setting_exists = True
            except ImportError:
                site_setting_exists = False
                logger.warning("[!] نموذج SiteSetting غير موجود")

            try:
                from .models import UserProfile
                user_profile_exists = True
            except ImportError:
                user_profile_exists = False
                logger.warning("[!] نموذج UserProfile غير موجود")

            # إنشاء إعدادات افتراضية للموقع
            if site_setting_exists:
                try:
                    setting, created = SiteSetting.objects.get_or_create(
                        pk=1,
                        defaults={
                            'site_name_ar': 'جمعية نسائم فلسطين الخيرية',
                            'site_name_en': 'Nasaeem Palestine Charity',
                            'site_email': 'info@nasaeem-palestine.org',
                            'maintenance_mode': False,
                            'enable_two_factor': False,
                            'session_timeout': 30,
                            'max_login_attempts': 5,
                            'admin_email_alerts': True,
                            'daily_report_enabled': True,
                            'weekly_report_enabled': True,
                            'auto_backup_enabled': True,
                            'backup_frequency_days': 1,
                            'keep_backups_count': 30,
                            'cache_timeout': 3600,
                            'enable_compression': True,
                        }
                    )
                    if created:
                        logger.info("[OK] تم إنشاء إعدادات الموقع الافتراضية")
                    else:
                        logger.info("[i] إعدادات الموقع موجودة مسبقاً")
                except Exception as e:
                    logger.error(f"[X] خطأ في إنشاء إعدادات الموقع: {e}")

            # إنشاء ملفات شخصية للمستخدمين
            if user_profile_exists:
                try:
                    users_without_profile = User.objects.filter(profile__isnull=True)
                    created_count = 0

                    for user in users_without_profile:
                        try:
                            if user.is_superuser:
                                role = 'super_admin'
                            elif user.is_staff:
                                role = 'admin'
                            else:
                                role = 'viewer'

                            UserProfile.objects.create(
                                user=user,
                                role=role,
                                is_active_staff=user.is_staff,
                                bio='',
                            )
                            created_count += 1
                            logger.info(f"[OK] تم إنشاء ملف شخصي للمستخدم: {user.username} ({role})")
                        except Exception as e:
                            logger.error(f"[X] خطأ في إنشاء ملف شخصي للمستخدم {user.username}: {e}")

                    if created_count > 0:
                        logger.info(f"[OK] تم إنشاء {created_count} ملف شخصي للمستخدمين")
                    else:
                        logger.info("[i] جميع المستخدمين لديهم ملفات شخصية")

                except Exception as e:
                    logger.error(f"[X] خطأ في إنشاء الملفات الشخصية: {e}")

            # ✅ الإصلاح 2: تحويل MEDIA_ROOT إلى Path object
            try:
                from pathlib import Path
                from django.conf import settings as django_settings

                media_root = Path(django_settings.MEDIA_ROOT)

                required_dirs = [
                    media_root / 'backups',
                    media_root / 'backups' / 'dashboard',
                    media_root / 'backups' / 'contact',
                    media_root / 'backups' / 'projects',
                    media_root / 'uploads',
                    media_root / 'profiles' / 'avatars',
                ]

                for directory in required_dirs:
                    directory.mkdir(parents=True, exist_ok=True)

                logger.info("[OK] تم التحقق من المجلدات المطلوبة وإنشائها")

            except Exception as e:
                logger.error(f"[X] خطأ في إنشاء المجلدات: {e}")

            logger.info("[OK] تم إنشاء جميع البيانات الافتراضية بنجاح")

        except Exception as e:
            logger.error(f"[X] خطأ عام في إنشاء البيانات الافتراضية: {e}")