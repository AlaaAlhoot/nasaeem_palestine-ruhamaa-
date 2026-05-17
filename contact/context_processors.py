from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext as _, get_language
from django.db.models import Count, Q, Sum, F
from django.utils import timezone
from datetime import timedelta
import logging

from contact.models import ContactMessage, ContactInfo, SocialMediaContact, Newsletter, FAQ, Category

logger = logging.getLogger('contact')


# ==========================================
# Helper Functions
# ==========================================

def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR')


def _get_lang(request):
    try:
        return request.LANGUAGE_CODE
    except AttributeError:
        return get_language() or 'ar'


def _get_contact_breadcrumbs(request):
    breadcrumbs = [{'name': _('الرئيسية'), 'url': '/'}]
    path = request.path
    if '/contact/' in path:
        breadcrumbs.append({'name': _('تواصل معنا'), 'url': '/contact/'})
        if '/faq/' in path:
            breadcrumbs.append({'name': _('الأسئلة الشائعة'), 'url': '/contact/faq/'})
        elif '/newsletter/' in path:
            breadcrumbs.append({'name': _('النشرة البريدية'), 'url': '/contact/newsletter/'})
    return breadcrumbs


# ==========================================
# Processor رئيسي موحّد (يغني عن 6 processors)
# ==========================================

def contact_context(request):
    """
    معالج السياق الموحّد — يجمع كل بيانات Contact في query واحدة لكل نوع.
    يغني عن: contact_context, footer_context, social_links_processor,
              contact_seo_context, contact_forms_context, contact_security_context
    """
    try:
        lang = _get_lang(request)
        cache_key = f'contact_ctx_unified_{lang}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        # ── جلب البيانات مرة واحدة فقط ──
        contact_info_all    = list(ContactInfo.objects.filter(is_active=True).order_by('order'))
        social_links_all    = list(SocialMediaContact.objects.filter(is_active=True).order_by('order'))
        popular_faqs        = list(FAQ.objects.filter(is_active=True).order_by('-views_count', '-helpful_votes')[:5])
        faq_categories      = list(Category.objects.all())

        # ── تقسيم البيانات بدون queries إضافية ──
        footer_contact_info  = [c for c in contact_info_all if c.show_in_footer]
        header_contact_info  = [c for c in contact_info_all if c.type in ('phone', 'email', 'address')][:3]
        emergency_contacts   = [c for c in contact_info_all if c.type == 'phone'][:2]
        social_links_header  = social_links_all[:5]

        # ── SEO: أول عنصر من كل نوع ──
        main_phone   = next((c for c in contact_info_all if c.type == 'phone'),   None)
        main_email   = next((c for c in contact_info_all if c.type == 'email'),   None)
        main_address = next((c for c in contact_info_all if c.type == 'address'), None)

        def loc(obj, field):
            if not obj: return None
            return getattr(obj, f'{field}_ar', '') or getattr(obj, field, '') if lang == 'ar' \
                else getattr(obj, f'{field}_en', '') or getattr(obj, f'{field}_ar', '')

        # ── إحصائيات التواصل الاجتماعي (بدون query إضافية) ──
        total_clicks = sum(s.clicks_count for s in social_links_all)
        most_popular = max(social_links_all, key=lambda s: s.clicks_count) if social_links_all else None

        context_data = {
            # البيانات الأساسية
            'contact_info_all':      contact_info_all,
            'footer_contact_info':   footer_contact_info,
            'contact_info_header':   header_contact_info,
            'emergency_contacts':    emergency_contacts,
            'contact_info':          footer_contact_info,

            # التواصل الاجتماعي
            'social_links_all':      social_links_all,
            'social_links':          social_links_all,
            'social_links_header':   social_links_header,
            'social_links_footer':   social_links_all,
            'social_media_links':    social_links_all,
            'social_media_header':   social_links_header,

            # الأسئلة الشائعة
            'popular_faqs':          popular_faqs,
            'faq_categories':        faq_categories,

            # إحصائيات التواصل الاجتماعي
            'social_stats': {
                'total_platforms': len(social_links_all),
                'total_clicks':    total_clicks,
                'most_popular_platform': most_popular,
            },

            # SEO
            'contact_seo': {
                'organization_info': {
                    'name':        getattr(settings, 'ORGANIZATION_NAME', 'جمعية نسائم فلسطين الخيرية'),
                    'phone':       loc(main_phone,   'value'),
                    'email':       loc(main_email,   'value'),
                    'address':     loc(main_address, 'value'),
                    'url':         getattr(settings, 'SITE_URL', '/'),
                    'description': getattr(settings, 'ORGANIZATION_DESCRIPTION', ''),
                },
                'breadcrumb_items': _get_contact_breadcrumbs(request),
            },

            # إعدادات الفورم
            'contact_form_config': {
                'enable_phone_field':  getattr(settings, 'CONTACT_ENABLE_PHONE',      True),
                'require_phone_field': getattr(settings, 'CONTACT_REQUIRE_PHONE',     False),
                'enable_attachment':   getattr(settings, 'CONTACT_ENABLE_ATTACHMENT', True),
                'max_attachment_size': getattr(settings, 'MAX_ATTACHMENT_SIZE',       5 * 1024 * 1024),
            },

            # إعدادات عامة
            'contact_settings': {
                'show_emergency_banner':  bool(emergency_contacts),
                'show_newsletter_popup':  getattr(settings, 'SHOW_NEWSLETTER_POPUP', False),
                'show_social_share':      getattr(settings, 'SHOW_SOCIAL_SHARE',     True),
                'enable_live_chat':       getattr(settings, 'ENABLE_LIVE_CHAT',      False),
                'max_message_length':     getattr(settings, 'MAX_MESSAGE_LENGTH',    2000),
            },

            # أمان
            'contact_security': {
                'honeypot_field': getattr(settings, 'HONEYPOT_FIELD_NAME', 'website'),
                'rate_limits': {
                    'contact_form': getattr(settings, 'CONTACT_RATE_LIMIT',   '5/hour'),
                    'newsletter':   getattr(settings, 'NEWSLETTER_RATE_LIMIT','3/hour'),
                },
            },
        }

        # حفظ في الكاش 30 دقيقة
        cache.set(cache_key, context_data, 60 * 30)
        return context_data

    except Exception as e:
        logger.error(f"خطأ في contact_context الموحّد: {e}")
        return {}


# ==========================================
# Processor للإشعارات (للإدارة فقط)
# ==========================================

def contact_notifications_context(request):
    """إشعارات للإدارة فقط — لا يشتغل للزوار العاديين"""
    try:
        if not getattr(request, 'user', None) or \
           not request.user.is_authenticated or \
           not request.user.is_staff:
            return {}

        cache_key = f'contact_notif_{request.user.id}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        new_messages    = ContactMessage.objects.filter(status='new')
        urgent_messages = new_messages.filter(priority='urgent')
        pending_replies = ContactMessage.objects.filter(
            status='reading',
            created_at__lt=timezone.now() - timedelta(hours=24)
        )

        context_data = {
            'contact_notifications': {
                'new_messages_count':     new_messages.count(),
                'urgent_messages_count':  urgent_messages.count(),
                'pending_replies_count':  pending_replies.count(),
                'has_notifications':      new_messages.exists() or urgent_messages.exists(),
                'notification_list': {
                    'new_messages':    new_messages[:5],
                    'urgent_messages': urgent_messages[:3],
                    'pending_replies': pending_replies[:5],
                }
            }
        }

        cache.set(cache_key, context_data, 60 * 5)
        return context_data

    except Exception as e:
        logger.error(f"خطأ في contact_notifications_context: {e}")
        return {}


# ==========================================
# Processor للتحليلات (للإدارة فقط)
# ==========================================

def contact_analytics_context(request):
    """إحصائيات وتحليلات للإدارة فقط"""
    try:
        if not getattr(request, 'user', None) or \
           not request.user.is_authenticated or \
           not request.user.is_staff:
            return {}

        cache_key = 'contact_analytics_ctx'
        cached = cache.get(cache_key)
        if cached:
            return cached

        today    = timezone.now().date()
        week_ago = today - timedelta(days=7)

        # إحصائيات النشرة البريدية
        newsletter_qs = Newsletter.objects.filter(is_active=True)
        newsletter_stats = {
            'total_subscribers':     newsletter_qs.count(),
            'confirmed_subscribers': newsletter_qs.filter(confirmed_at__isnull=False).count(),
        }

        # إحصائيات الرسائل
        msg_qs = ContactMessage.objects
        message_stats = {
            'total_messages':   msg_qs.count(),
            'unread_messages':  msg_qs.filter(status='new').count(),
            'urgent_messages':  msg_qs.filter(priority='urgent', status__in=['new','reading']).count(),
            'today_messages':   msg_qs.filter(created_at__date=today).count(),
            'week_messages':    msg_qs.filter(created_at__date__gte=week_ago).count(),
        }

        context_data = {
            'newsletter_stats': newsletter_stats,
            'message_stats':    message_stats,
            'contact_analytics': {
                'messages': message_stats,
                'top_topics': msg_qs.values('subject').annotate(count=Count('id')).order_by('-count')[:5],
            }
        }

        cache.set(cache_key, context_data, 60 * 15)
        return context_data

    except Exception as e:
        logger.error(f"خطأ في contact_analytics_context: {e}")
        return {}


# ==========================================
# Cache Management
# ==========================================

def clear_contact_context_cache():
    keys = [
        'contact_ctx_unified_ar',
        'contact_ctx_unified_en',
        'contact_analytics_ctx',
        'contact_page_context',
    ]
    for user_id in range(1, 1001):
        keys.append(f'contact_notif_{user_id}')
    deleted = sum(1 for k in keys if cache.delete(k))
    logger.info(f"تم مسح {deleted} مفتاح من كاش Contact")
    return True


# ==========================================
# Aliases للتوافق مع settings.py القديم
# ==========================================

def footer_context(request):
    return {}   # البيانات موجودة في contact_context الموحّد

def social_links_processor(request):
    return {}   # البيانات موجودة في contact_context الموحّد

def contact_forms_context(request):
    return {}   # البيانات موجودة في contact_context الموحّد

def contact_seo_context(request):
    return {}   # البيانات موجودة في contact_context الموحّد

def contact_security_context(request):
    return {}   # البيانات موجودة في contact_context الموحّد


__all__ = [
    'contact_context',
    'contact_notifications_context',
    'contact_analytics_context',
    'footer_context',
    'social_links_processor',
    'contact_forms_context',
    'contact_seo_context',
    'contact_security_context',
    'clear_contact_context_cache',
]