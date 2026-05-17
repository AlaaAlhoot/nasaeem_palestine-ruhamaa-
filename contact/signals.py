from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.cache import cache
import logging

from .models import ContactMessage, Newsletter, SocialMediaContact, ContactInfo, FAQ

logger = logging.getLogger('contact')


# =================== إشارات رسائل التواصل ===================

@receiver(post_save, sender=ContactMessage)
def handle_contact_message_created(sender, instance, created, **kwargs):
    """معالجة إنشاء رسالة تواصل جديدة"""
    if created:
        # مسح الكاش
        clear_contact_cache()

        # تسجيل النشاط فقط
        logger.info(f"تم إنشاء رسالة تواصل جديدة: {instance.id} من {instance.email}")


@receiver(pre_save, sender=ContactMessage)
def handle_contact_message_status_change(sender, instance, **kwargs):
    """معالجة تغيير حالة الرسالة"""
    if instance.pk:
        try:
            from django.utils import timezone
            old_instance = ContactMessage.objects.get(pk=instance.pk)

            if old_instance.status != 'replied' and instance.status == 'replied':
                instance.replied_at = timezone.now()
                logger.info(f"تم تحديث حالة الرسالة {instance.id} إلى 'تم الرد'")
        except ContactMessage.DoesNotExist:
            pass


@receiver(post_delete, sender=ContactMessage)
def handle_contact_message_deleted(sender, instance, **kwargs):
    """معالجة حذف رسالة التواصل"""
    clear_contact_cache()
    logger.info(f"تم حذف رسالة التواصل: {instance.id}")


# =================== إشارات النشرة البريدية ===================

@receiver(post_save, sender=Newsletter)
def handle_newsletter_subscription(sender, instance, created, **kwargs):
    """معالجة اشتراك النشرة البريدية"""
    if created:
        import uuid
        if not instance.confirmation_token:
            instance.confirmation_token = str(uuid.uuid4())
            instance.save(update_fields=['confirmation_token'])

        clear_newsletter_cache()
        logger.info(f"اشتراك جديد في النشرة البريدية: {instance.email}")


@receiver(post_delete, sender=Newsletter)
def handle_newsletter_unsubscribed(sender, instance, **kwargs):
    """معالجة إلغاء اشتراك النشرة"""
    clear_newsletter_cache()
    logger.info(f"تم حذف اشتراك النشرة البريدية: {instance.email}")


# =================== إشارات وسائل التواصل الاجتماعي ===================

@receiver([post_save, post_delete], sender=SocialMediaContact)
def handle_social_media_change(sender, instance, **kwargs):
    """معالجة تغيير روابط التواصل الاجتماعي"""
    clear_social_cache()
    logger.info(f"تم تحديث وسائل التواصل الاجتماعي: {instance.platform}")


# =================== إشارات معلومات التواصل ===================

@receiver([post_save, post_delete], sender=ContactInfo)
def handle_contact_info_change(sender, instance, **kwargs):
    """معالجة تغيير معلومات التواصل"""
    clear_contact_cache()
    logger.info(f"تم تحديث معلومات التواصل: {instance.type}")


# =================== إشارات الأسئلة الشائعة ===================

@receiver(post_save, sender=FAQ)
def handle_faq_change(sender, instance, created, **kwargs):
    """معالجة تغيير الأسئلة الشائعة"""
    clear_faq_cache()
    if created:
        logger.info(f"تم إنشاء سؤال شائع جديد: {instance.id}")


@receiver(post_delete, sender=FAQ)
def handle_faq_deleted(sender, instance, **kwargs):
    """معالجة حذف سؤال شائع"""
    clear_faq_cache()
    logger.info(f"تم حذف السؤال الشائع: {instance.id}")


# =================== دوال مساعدة لمسح الكاش ===================

def clear_contact_cache():
    """مسح كاش معلومات التواصل"""
    cache_keys = [
        'contact_page_context',
        'contact_info_cache',
        'contact_statistics',
        'header_contact_info',
        'footer_contact_info'
    ]
    for key in cache_keys:
        cache.delete(key)


def clear_newsletter_cache():
    """مسح كاش النشرة البريدية"""
    cache_keys = [
        'newsletter_stats',
        'newsletter_subscribers_count',
        'newsletter_form_cache'
    ]
    for key in cache_keys:
        cache.delete(key)


def clear_social_cache():
    """مسح كاش وسائل التواصل الاجتماعي"""
    cache_keys = [
        'social_links_cache',
        'active_social_platforms',
        'social_statistics'
    ]
    for key in cache_keys:
        cache.delete(key)


def clear_faq_cache():
    """مسح كاش الأسئلة الشائعة"""
    cache_keys = [
        'faq_list_cache',
        'faq_categories',
        'popular_faqs',
        'faq_statistics'
    ]
    for key in cache_keys:
        cache.delete(key)


