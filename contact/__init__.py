__version__ = '1.0.0'
__author__ = 'Nasaeem Palestine Tech Team'
__email__ = 'tech@nasaeem-palestine.org'

# التكوين الافتراضي للتطبيق
default_app_config = 'contact.apps.ContactConfig'

# إعدادات التطبيق
CONTACT_SETTINGS = {
    'MAX_MESSAGE_LENGTH': 2000,
    'MAX_ATTACHMENT_SIZE': 5 * 1024 * 1024,  # 5MB
    'ALLOWED_ATTACHMENT_TYPES': [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'image/jpeg',
        'image/png',
        'image/gif',
        'text/plain'
    ],
    'DEFAULT_MESSAGE_STATUS': 'new',
    'DEFAULT_MESSAGE_PRIORITY': 'normal',
    'DEFAULT_NEWSLETTER_FREQUENCY': 'weekly',
    'NEWSLETTER_CONFIRMATION_REQUIRED': True,
    'AUTO_REPLY_ENABLED': True,
    'SOCIAL_TRACKING_ENABLED': True
}

# رسائل النجاح والأخطاء
MESSAGES = {
    'SUCCESS': {
        'MESSAGE_SENT': 'تم إرسال رسالتك بنجاح. سنقوم بالرد عليك قريباً.',
        'NEWSLETTER_SUBSCRIBED': 'تم الاشتراك في النشرة البريدية بنجاح.',
        'NEWSLETTER_CONFIRMED': 'تم تأكيد اشتراكك في النشرة البريدية.',
        'NEWSLETTER_UNSUBSCRIBED': 'تم إلغاء اشتراكك من النشرة البريدية.',
        'FAQ_HELPFUL': 'شكراً لك على تقييمك.'
    },
    'ERROR': {
        'MESSAGE_FAILED': 'فشل في إرسال الرسالة. يرجى المحاولة مرة أخرى.',
        'INVALID_EMAIL': 'البريد الإلكتروني غير صحيح.',
        'SPAM_DETECTED': 'تم اكتشاف نشاط مشبوه.',
        'FILE_TOO_LARGE': 'حجم الملف كبير جداً.',
        'INVALID_FILE_TYPE': 'نوع الملف غير مدعوم.',
        'RATE_LIMITED': 'تم تجاوز الحد المسموح من الطلبات.',
        'SUBSCRIPTION_EXISTS': 'أنت مشترك بالفعل في النشرة البريدية.',
        'INVALID_TOKEN': 'الرابط غير صحيح أو منتهي الصلاحية.'
    }
}

# إعدادات الأمان
SECURITY_SETTINGS = {
    'HONEYPOT_FIELD': 'website',
    'RATE_LIMIT': {
        'CONTACT_FORM': '5/hour',
        'NEWSLETTER': '3/hour',
        'SOCIAL_CLICKS': '100/hour'
    },
    'BLOCKED_DOMAINS': [
        '10minutemail.com',
        'tempmail.org',
        'guerrillamail.com',
        'mailinator.com'
    ],
    'SPAM_KEYWORDS': [
        'spam', 'viagra', 'casino', 'lottery', 'winner',
        'congratulations', 'free money', 'click here'
    ]
}

# إعدادات الإيميل
EMAIL_SETTINGS = {
    'ADMIN_NOTIFICATION_TEMPLATE': 'contact/email/admin_notification.html',
    'CONFIRMATION_TEMPLATE': 'contact/email/confirmation.html',
    'NEWSLETTER_CONFIRMATION_TEMPLATE': 'contact/email/newsletter_confirmation.html',
    'AUTO_REPLY_ENABLED': True,
    'ADMIN_NOTIFICATION_ENABLED': True,
    'NEWSLETTER_CONFIRMATION_ENABLED': True
}

# روابط مفيدة
USEFUL_LINKS = {
    'PRIVACY_POLICY': '/privacy-policy/',
    'TERMS_OF_SERVICE': '/terms-of-service/',
    'FAQ': '/contact/faq/',
    'UNSUBSCRIBE': '/contact/newsletter/unsubscribe/',
    'MAIN_WEBSITE': '/'
}

# معلومات التطبيق للـ Admin
APP_INFO = {
    'name': 'نظام التواصل والاتصال',
    'description': 'إدارة رسائل التواصل والنشرة البريدية ووسائل التواصل الاجتماعي',
    'version': __version__,
    'author': __author__,
    'features': [
        'نظام رسائل التواصل مع الحماية الأمنية',
        'النشرة البريدية مع التأكيد بالبريد الإلكتروني',
        'إدارة روابط وسائل التواصل الاجتماعي',
        'نظام الأسئلة الشائعة التفاعلي',
        'إحصائيات مفصلة وتتبع التفاعل',
        'واجهة إدارة متقدمة مع تصدير البيانات',
        'دعم كامل للغة العربية وRTL',
        'تصميم متجاوب لجميع الأجهزة'
    ]
}

# دوال مساعدة
def get_contact_statistics():
    """الحصول على إحصائيات التطبيق"""
    from django.utils import timezone
    from .models import ContactMessage, Newsletter, SocialMediaContact, FAQ
    try:
        stats = {
            'messages': {
                'total': ContactMessage.objects.count(),
                'new': ContactMessage.objects.filter(status='new').count(),
                'replied': ContactMessage.objects.filter(status='replied').count(),
                'today': ContactMessage.objects.filter(
                    created_at__date=timezone.now().date()
                ).count()
            },
            'newsletter': {
                'total_subscribers': Newsletter.objects.filter(is_active=True).count(),
                'confirmed_subscribers': Newsletter.objects.filter(
                    is_active=True, confirmed_at__isnull=False
                ).count(),
                'weekly_subscribers': Newsletter.objects.filter(
                    is_active=True, frequency='weekly'
                ).count(),
                'monthly_subscribers': Newsletter.objects.filter(
                    is_active=True, frequency='monthly'
                ).count()
            },
            'social': {
                'active_platforms': SocialMediaContact.objects.filter(is_active=True).count(),
                'total_clicks': sum(
                    SocialMediaContact.objects.filter(is_active=True).values_list(
                        'clicks_count', flat=True
                    )
                )
            },
            'faq': {
                'active_faqs': FAQ.objects.filter(is_active=True).count(),
                'total_views': sum(FAQ.objects.values_list('views_count', flat=True)),
                'helpful_votes': sum(FAQ.objects.values_list('helpful_votes', flat=True))
            }
        }
        return stats
    except Exception:
        return {}

def clear_contact_cache():
    """مسح جميع الكاش المتعلق بالتطبيق"""
    from django.core.cache import cache
    cache_keys = [
        'contact_page_context',
        'social_links_cache',
        'contact_info_cache',
        'faq_list_cache',
        'newsletter_stats'
    ]
    for key in cache_keys:
        cache.delete(key)
    return True

# تصدير للاستخدام الخارجي
__all__ = [
    'CONTACT_SETTINGS',
    'MESSAGES',
    'SECURITY_SETTINGS',
    'EMAIL_SETTINGS',
    'USEFUL_LINKS',
    'APP_INFO',
    'get_contact_statistics',
    'clear_contact_cache',
    '__version__',
    '__author__',
    '__email__'
]

# رسالة التحميل
import logging
logger = logging.getLogger(__name__)
