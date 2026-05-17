from django.apps import AppConfig, apps
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_migrate
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class ContactConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'contact'
    verbose_name = _('التواصل والاتصال')

    def ready(self):
        """تشغيل الإعدادات عند تحميل التطبيق"""
        # تسجيل الإشارات
        try:
            import contact.signals
        except ImportError:
            pass

        # ربط إشارة post_migrate لإنشاء البيانات الأولية
        post_migrate.connect(self.create_initial_data, sender=self)

    def create_initial_data(self, sender, **kwargs):
        """إنشاء البيانات الأولية بعد Migration"""
        from django.contrib.auth.models import Group, Permission
        from django.contrib.contenttypes.models import ContentType

        # إنشاء مجموعة مديرو التواصل إذا لم تكن موجودة
        group_name = 'Contact Managers'
        if not Group.objects.filter(name=group_name).exists():
            contact_managers = Group.objects.create(name=group_name)
            content_types = ContentType.objects.filter(app_label='contact')
            permissions = Permission.objects.filter(content_type__in=content_types)
            contact_managers.permissions.set(permissions)
            logger.info(" تم إنشاء مجموعة مديرو التواصل")
        else:
            logger.info("️ مجموعة مديرو التواصل موجودة بالفعل")

        # التحقق من وجود الجداول قبل إنشاء البيانات الافتراضية
        existing_tables = connection.introspection.table_names()

        if 'contact_contactinfo' in existing_tables:
            self.create_default_contact_info()

        if 'contact_socialmediacontact' in existing_tables:
            self.create_default_social_links()

        if 'contact_faq' in existing_tables:
            self.create_default_faqs()

    def create_default_contact_info(self):
        """إنشاء معلومات التواصل الافتراضية وتصحيحها لتكون فريدة حسب النوع"""
        from .models import ContactInfo

        default_contacts = [
            {
                'type': 'phone',
                'value_ar': '+970 8 123 4567',
                'value_en': '+970 8 123 4567',
                'show_in_footer': True,
                'icon_class': 'fas fa-phone',
                'order': 1
            },
            {
                'type': 'email',
                'value_ar': 'info@nasaeem-palestine.org',
                'value_en': 'info@nasaeem-palestine.org',
                'show_in_footer': True,
                'icon_class': 'fas fa-envelope',
                'order': 2
            },
            {
                'type': 'address',
                'value_ar': 'غزة - فلسطين\nشارع الوحدة',
                'value_en': 'Gaza - Palestine\nAl-Wahda Street',
                'show_in_footer': True,
                'icon_class': 'fas fa-map-marker-alt',
                'order': 3
            },
        ]

        for contact_data in default_contacts:
            ContactInfo.objects.get_or_create(
                type=contact_data['type'],
                defaults=contact_data
            )

        logger.info(" تم إنشاء/تحديث معلومات التواصل الافتراضية")

    def create_default_social_links(self):
        """إنشاء روابط التواصل الاجتماعي الافتراضية"""
        from .models import SocialMediaContact

        default_socials = [
            {
                'platform': 'facebook',
                'username': 'nasaeem.palestine',
                'url': 'https://facebook.com/nasaeem.palestine',
                'order': 1
            },
            {
                'platform': 'twitter',
                'username': 'nasaeem_ps',
                'url': 'https://twitter.com/nasaeem_ps',
                'order': 2
            },
            {
                'platform': 'instagram',
                'username': 'nasaeem.palestine',
                'url': 'https://instagram.com/nasaeem.palestine',
                'order': 3
            },
            {
                'platform': 'youtube',
                'username': 'نسائم فلسطين',
                'url': 'https://youtube.com/@nasaeem-palestine',
                'order': 4
            },
            {
                'platform': 'whatsapp',
                'username': 'تواصل مباشر',
                'url': 'https://wa.me/970599123456',
                'order': 5
            }
        ]

        for social_data in default_socials:
            SocialMediaContact.objects.get_or_create(
                platform=social_data['platform'],
                defaults=social_data
            )

        logger.info(" تم إنشاء روابط التواصل الاجتماعي الافتراضية")

    def create_default_faqs(self):
        """إنشاء أسئلة شائعة افتراضية (اختياري)"""
        from .models import FAQ
        # يمكنك إضافة أسئلة افتراضية هنا إن أردت
        pass

    def get_app_statistics(self):
        """إحصائيات التطبيق"""
        try:
            from .models import ContactMessage, Newsletter, FAQ, SocialMediaContact
            return {
                'total_messages': ContactMessage.objects.count(),
                'unread_messages': ContactMessage.objects.filter(status='new').count(),
                'newsletter_subscribers': Newsletter.objects.filter(is_active=True).count(),
                'total_faqs': FAQ.objects.filter(is_active=True).count(),
                'social_platforms': SocialMediaContact.objects.filter(is_active=True).count(),
            }
        except Exception:
            return {}