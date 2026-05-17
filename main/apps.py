from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MainConfig(AppConfig):
    """تكوين تطبيق Main"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'
    verbose_name = _('التطبيق الرئيسي')

    def ready(self):
        """يتم تنفيذها عند جاهزية التطبيق"""
        # استيراد الإشارات (signals) إذا كان لدينا
        try:
            from . import signals
        except ImportError:
            pass

        # تسجيل المهام المجدولة (scheduled tasks) إذا كان لدينا
        try:
            from . import tasks
        except ImportError:
            pass

        # إعداد إضافي للتطبيق
        self.setup_app_settings()

    def setup_app_settings(self):
        """إعداد التطبيق الإضافي"""
        # إنشاء إعدادات الموقع إذا لم تكن موجودة
        try:
            from .models import SiteSettings
            if not SiteSettings.objects.exists():
                SiteSettings.objects.create(
                    site_name_ar='جمعية نسائم فلسطين الخيرية',
                    site_name_en='Nasaeem Palestine Charity',
                    phone='056751504',
                    email='nasaempalstin2013@gmail.com',
                    address_ar='غزة - السامر - مقابل مدرسة الإمام الشافعي',
                    address_en='Gaza - Al-Samer - Opposite to Imam Al-Shafi\'i School',
                    about_summary_ar='مؤسسة خيرية تنموية إنسانية، تعمل على تنفيذ البرامج والمشاريع التي تساهم في تحقيق التنمية المتكاملة في المجتمع الفلسطيني.',
                    about_summary_en='A charitable, developmental and humanitarian institution that works to implement programs and projects that contribute to achieving comprehensive development in Palestinian society.',
                    established_year=2013,
                )
        except Exception:
            # تجاهل الأخطاء أثناء Migration
            pass