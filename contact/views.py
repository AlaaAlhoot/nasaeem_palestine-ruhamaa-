import re
import json
import logging
import uuid

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives, send_mail
from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from django.utils.translation import get_language
from django.views.decorators.csrf import csrf_exempt, csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST

from .forms import ContactForm, NewsletterForm
from .models import ContactInfo, ContactMessage, FAQ, Newsletter, SocialMediaContact, Category
from core.models import Complaint
from core.utils import notify_admins

logger = logging.getLogger("contact")

_UNSAFE = re.compile(r'<script|javascript:|onerror=', re.I)


# ==========================================
# Helper Functions
# ==========================================

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR')


def get_contact_page_context():
    cached = cache.get('contact_page_context')
    if cached:
        return cached
    try:
        context = {
            'contact_info_all': ContactInfo.objects.filter(is_active=True).order_by('order'),
            'social_links_all': SocialMediaContact.objects.filter(is_active=True).order_by('order'),
            'recent_faqs':      FAQ.objects.filter(is_active=True).order_by('-helpful_votes', '-views_count', 'order')[:4],
        }
        cache.set('contact_page_context', context, 60 * 30)
        return context
    except Exception as e:
        logger.error(f"Error fetching contact data: {e}")
        return {'contact_info_all': [], 'social_links_all': [], 'recent_faqs': []}


def send_admin_notification(message):
    try:
        admin_emails  = getattr(settings, 'ADMIN_EMAIL_LIST', [settings.DEFAULT_FROM_EMAIL])
        html_message  = render_to_string('contact/email/admin_notification.html', {
            'message':  message,
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        })
        email = EmailMultiAlternatives(
            subject=f'{_("رسالة تواصل جديدة")}: {message.subject}',
            body=strip_tags(html_message),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=admin_emails,
        )
        email.attach_alternative(html_message, "text/html")
        if message.attachment:
            email.attach_file(message.attachment.path)
        email.send()
        logger.info(f"Admin notification sent for message ID: {message.id}")
    except Exception as e:
        logger.error(f"Failed to send admin notification: {e}")
        raise


def send_confirmation_email(message):
    try:
        html_message = render_to_string('contact/email/confirmation.html', {
            'message':   message,
            'site_name': getattr(settings, 'SITE_NAME', _('جمعية نسائم فلسطين الخيرية')),
        })
        send_mail(
            subject=_('تم استلام رسالتك - جمعية نسائم فلسطين الخيرية'),
            message=strip_tags(html_message),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[message.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Confirmation email sent for message ID: {message.id}")
    except Exception as e:
        logger.error(f"Failed to send confirmation email: {e}")
        raise





# ==========================================
# Contact Views
# ==========================================

def contact_page_view(request):
    from core.models import SystemSettings

    # ── معلومات التواصل ──
    contact_info = ContactInfo.objects.filter(is_active=True).order_by('order')

    # ── منصات التواصل الاجتماعي ──
    social_links = SocialMediaContact.objects.filter(is_active=True).order_by('order')

    # ── الأسئلة الشائعة ──
    recent_faqs = FAQ.objects.filter(is_active=True).order_by(
        '-helpful_votes', '-views_count', 'order'
    )[:4]

    # ── أوقات العمل ──
    work_days_type   = SystemSettings.get('work_days_type',   'week')
    work_days_from   = SystemSettings.get('work_days_from',   '')
    work_days_to     = SystemSettings.get('work_days_to',     '')
    work_days_custom = SystemSettings.get('work_days_custom', '')
    work_time_from   = f"{SystemSettings.get('work_time_from_h','9')}:{SystemSettings.get('work_time_from_m','00')} {SystemSettings.get('work_time_from_p','صباحاً')}"
    work_time_to     = f"{SystemSettings.get('work_time_to_h','4')}:{SystemSettings.get('work_time_to_m','00')} {SystemSettings.get('work_time_to_p','مساءً')}"

    return render(request, 'contact/contact.html', {
        # معلومات التواصل
        'contact_info':    contact_info,
        'social_links':    social_links,
        'recent_faqs':     recent_faqs,
        # أوقات العمل
        'work_days_type':   work_days_type,
        'work_days_from':   work_days_from,
        'work_days_to':     work_days_to,
        'work_days_custom': work_days_custom,
        'work_time_from':   work_time_from,
        'work_time_to':     work_time_to,
    })

@csrf_protect
@require_POST
def contact_view(request):
    """استقبال رسالة التواصل (POST → JSON)"""
    name          = request.POST.get('name',          '').strip()
    phone         = request.POST.get('phone',         '').strip()
    phone_country = request.POST.get('phone_country', '+970').strip()
    email         = request.POST.get('email',         '').strip()
    subject       = request.POST.get('subject',       '').strip()
    message       = request.POST.get('message',       '').strip()

    errors = {}
    if not name or len(name) > 100:
        errors['name']    = 'الاسم مطلوب ولا يتجاوز 100 حرف'
    if not phone:
        errors['phone']   = 'رقم التواصل مطلوب'
    if not email or not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        errors['email']   = 'البريد الإلكتروني غير صالح'
    if not subject or len(subject) > 200:
        errors['subject'] = 'العنوان مطلوب ولا يتجاوز 200 حرف'
    if not message or len(message) > 700:
        errors['message'] = 'الرسالة مطلوبة ولا تتجاوز 700 حرف'

    if errors:
        return JsonResponse({'status': 'error', 'errors': errors})

    for val in (name, subject, message):
        if _UNSAFE.search(val):
            return JsonResponse({'status': 'error', 'message': 'مدخل غير صالح'}, status=400)

    try:
        Complaint.objects.create(
            name=name, phone=phone, phone_country=phone_country,
            email=email, subject=subject, message=message,
            ip_address=get_client_ip(request),
        )
        notify_admins(
            ntype='SYSTEM',
            title='رسالة تواصل جديدة 📩',
            message=f'رسالة من {name} — {subject}',
            action_url='/admin-panel/complaints/',
        )
        return JsonResponse({'status': 'success', 'message': 'تم إرسال رسالتك بنجاح ✅'})
    except Exception as e:
        logger.error(f'contact_view error: {e}', exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'حدث خطأ، يرجى المحاولة مجدداً'}, status=500)


# ==========================================
# AJAX Views
# ==========================================

@require_POST
def send_message_ajax(request):
    """إرسال رسالة تواصل عبر Ajax (الفورم القديم)"""
    try:
        form = ContactForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.ip_address = get_client_ip(request)
            message.user_agent = request.META.get('HTTP_USER_AGENT', '')
            message.save()
            try:
                send_admin_notification(message)
                send_confirmation_email(message)
            except Exception as e:
                logger.error(f"Failed to send notifications: {e}")
            return JsonResponse({'success': True, 'message': str(_('تم إرسال رسالتك بنجاح'))})
        errors = {f: [str(e) for e in el] for f, el in form.errors.items()}
        return JsonResponse({'success': False, 'errors': errors}, status=400)
    except Exception as e:
        logger.error(f"Error sending message: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(_('حدث خطأ غير متوقع'))}, status=500)


@require_POST
def track_social_click(request, social_id):
    try:
        social = get_object_or_404(SocialMediaContact, id=social_id, is_active=True)
        social.clicks_count = F('clicks_count') + 1
        social.save(update_fields=['clicks_count'])
        social.refresh_from_db()
        return JsonResponse({'success': True, 'clicks': social.clicks_count})
    except Http404:
        return JsonResponse({'success': False, 'error': str(_('الرابط غير موجود'))}, status=404)
    except Exception as e:
        logger.error(f"Error tracking click: {e}")
        return JsonResponse({'success': False, 'error': str(_('حدث خطأ'))}, status=500)


# ==========================================
# Newsletter Views
# ==========================================

@require_POST
def newsletter_subscribe(request):
    try:
        is_json = request.content_type == 'application/json'
        if is_json:
            data  = json.loads(request.body)
            email = data.get('email')
            name  = data.get('name', '')
        else:
            email = request.POST.get('email')
            name  = request.POST.get('name', '')

        if not email:
            msg = str(_('البريد الإلكتروني مطلوب'))
            return JsonResponse({'success': False, 'error': msg}) if is_json else redirect('contact:contact_page')

        subscription, created = Newsletter.objects.get_or_create(
            email=email,
            defaults={'name': name, 'ip_address': get_client_ip(request), 'confirmation_token': str(uuid.uuid4())}
        )

        if created:
            try:
                send_newsletter_confirmation(subscription)
                msg = _('تم تسجيل اشتراكك. يرجى تأكيد البريد الإلكتروني.')
            except Exception as e:
                logger.error(f"Failed to send confirmation: {e}")
                msg = _('تم تسجيل اشتراكك بنجاح.')
        elif subscription.is_active:
            msg = _('أنت مشترك بالفعل في النشرة البريدية.')
        else:
            subscription.is_active = True
            subscription.save()
            msg = _('تم إعادة تفعيل اشتراكك.')

        if is_json:
            return JsonResponse({'success': True, 'message': str(msg)})
        messages.success(request, msg)
        return redirect('contact:contact_page')

    except Exception as e:
        logger.error(f"Error in subscription: {e}")
        msg = str(_('حدث خطأ في الاشتراك'))
        if request.content_type == 'application/json':
            return JsonResponse({'success': False, 'error': msg})
        messages.error(request, msg)
        return redirect('contact:contact_page')


@require_http_methods(["GET"])
def newsletter_confirm(request, token):
    try:
        subscription = get_object_or_404(Newsletter, confirmation_token=token)
        if not subscription.is_confirmed:
            subscription.confirm_subscription()
            messages.success(request, _('تم تأكيد اشتراكك في النشرة البريدية بنجاح.'))
        else:
            messages.info(request, _('تم تأكيد اشتراكك مسبقاً.'))
    except Http404:
        messages.error(request, _('رابط التأكيد غير صحيح أو منتهي الصلاحية.'))
    return redirect('main:home')


@require_http_methods(["GET"])
def newsletter_unsubscribe(request, token):
    try:
        subscription = get_object_or_404(Newsletter, confirmation_token=token)
        subscription.is_active = False
        subscription.save()
        messages.success(request, _('تم إلغاء اشتراكك في النشرة البريدية.'))
    except Http404:
        messages.error(request, _('رابط إلغاء الاشتراك غير صحيح.'))
    return redirect('main:home')


@require_POST
@csrf_exempt
def subscribe_ajax(request):
    return newsletter_subscribe(request)

def send_newsletter_confirmation(subscription):
    try:
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        html_message = render_to_string('contact/email/newsletter_confirmation.html', {
            'subscription':     subscription,
            'confirmation_url': f"{site_url}/contact/newsletter/confirm/{subscription.confirmation_token}/",
            'unsubscribe_url':  f"{site_url}/contact/newsletter/unsubscribe/{subscription.confirmation_token}/",
            'site_name':        getattr(settings, 'SITE_NAME', _('جمعية نسائم فلسطين الخيرية')),
        })
        send_mail(
            subject=_('تأكيد الاشتراك في النشرة البريدية'),
            message=strip_tags(html_message),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[subscription.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Newsletter confirmation sent to: {subscription.email}")
    except Exception as e:
        logger.error(f"Failed to send newsletter confirmation: {e}")
        raise
# ==========================================
# FAQ Views
# ==========================================

def faq_list(request):
    try:
        search_query = request.GET.get('q', '').strip()
        category_id  = request.GET.get('category', '').strip()
        page_number  = request.GET.get('page', 1)
        current_lang = get_language()

        faqs = FAQ.objects.filter(is_active=True).select_related('category')

        if search_query:
            if current_lang == 'en':
                faqs = faqs.filter(
                    Q(question_en__icontains=search_query) | Q(answer_en__icontains=search_query) |
                    Q(tags_en__icontains=search_query)     | Q(category__category_en__icontains=search_query)
                )
            else:
                faqs = faqs.filter(
                    Q(question_ar__icontains=search_query) | Q(answer_ar__icontains=search_query) |
                    Q(tags_ar__icontains=search_query)     | Q(category__category_ar__icontains=search_query)
                )

        if category_id:
            try:
                faqs = faqs.filter(category_id=int(category_id))
            except ValueError:
                pass

        faqs      = faqs.order_by('order', '-helpful_votes', '-views_count')
        paginator = Paginator(faqs, 10)
        page_obj  = paginator.get_page(page_number)

        context = {
            'faqs':              page_obj,
            'categories':        Category.objects.filter(faq__is_active=True).distinct().order_by('category_ar'),
            'popular_faqs':      FAQ.objects.filter(is_active=True).select_related('category').order_by('-views_count', '-helpful_votes')[:5],
            'search_query':      search_query,
            'selected_category': category_id,
            'total_faqs':        paginator.count,
            'page_title':        _('الأسئلة الشائعة'),
        }
        return render(request, 'contact/faq.html', context)

    except Exception as e:
        logger.error(f"Error in FAQ page: {e}", exc_info=True)
        return render(request, 'contact/faq.html', {
            'faqs': [], 'categories': [], 'popular_faqs': [],
            'search_query': '', 'selected_category': '', 'total_faqs': 0,
            'page_title': _('الأسئلة الشائعة'),
            'error_message': _('حدث خطأ في تحميل الأسئلة الشائعة'),
        })


def faq_detail(request, faq_id):
    try:
        faq = get_object_or_404(FAQ, id=faq_id, is_active=True)
        viewed_faqs = request.session.get('viewed_faqs', [])
        if faq_id not in viewed_faqs:
            faq.views_count = F('views_count') + 1
            faq.save(update_fields=['views_count'])
            faq.refresh_from_db()
            viewed_faqs.append(faq_id)
            request.session['viewed_faqs'] = viewed_faqs
            request.session.modified = True

        return render(request, 'contact/faq_detail.html', {
            'faq':          faq,
            'related_faqs': FAQ.objects.filter(is_active=True, category=faq.category).exclude(id=faq_id).order_by('-views_count')[:5],
            'page_title':   faq.question_ar,
        })
    except Exception as e:
        logger.error(f"Error viewing FAQ #{faq_id}: {e}", exc_info=True)
        return render(request, '404.html', status=404)


@require_POST
@ensure_csrf_cookie
def mark_faq_helpful(request, faq_id):
    try:
        faq = get_object_or_404(FAQ, id=faq_id, is_active=True)
        voted_faqs = request.session.get('voted_faqs', [])
        if faq_id in voted_faqs:
            return JsonResponse({'success': False, 'message': str(_('لقد قمت بالتصويت مسبقاً على هذا السؤال'))}, status=400)

        faq.helpful_votes = F('helpful_votes') + 1
        faq.save(update_fields=['helpful_votes'])
        faq.refresh_from_db()
        voted_faqs.append(faq_id)
        request.session['voted_faqs'] = voted_faqs
        request.session.modified = True
        return JsonResponse({'success': True, 'helpful_votes': faq.helpful_votes, 'message': str(_('شكراً لك! تم تسجيل تصويتك بنجاح'))})

    except FAQ.DoesNotExist:
        return JsonResponse({'success': False, 'message': str(_('السؤال غير موجود أو غير نشط'))}, status=404)
    except Exception as e:
        logger.error(f"Error voting: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': str(_('حدث خطأ في معالجة التصويت'))}, status=500)


@require_POST
def track_faq_view(request, faq_id):
    try:
        faq = get_object_or_404(FAQ, id=faq_id, is_active=True)
        viewed_faqs = request.session.get('viewed_faqs', [])
        if faq_id not in viewed_faqs:
            faq.views_count = F('views_count') + 1
            faq.save(update_fields=['views_count'])
            faq.refresh_from_db()
            viewed_faqs.append(faq_id)
            request.session['viewed_faqs'] = viewed_faqs
            request.session.modified = True
        return JsonResponse({'success': True, 'views_count': faq.views_count})
    except Exception as e:
        logger.error(f"Error tracking view: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@require_http_methods(["GET"])
def faq_search_api(request):
    try:
        query = request.GET.get('q', '').strip()
        if len(query) < 2:
            return JsonResponse({'success': False, 'message': str(_('يجب إدخال حرفين على الأقل'))})

        current_lang = get_language()
        if current_lang == 'en':
            faqs = FAQ.objects.filter(
                Q(question_en__icontains=query) | Q(answer_en__icontains=query) | Q(tags__icontains=query),
                is_active=True
            ).order_by('-views_count')[:10]
        else:
            faqs = FAQ.objects.filter(
                Q(question_ar__icontains=query) | Q(answer_ar__icontains=query) | Q(tags__icontains=query),
                is_active=True
            ).order_by('-views_count')[:10]

        results = [{'id': f.id, 'question': f.question_en if current_lang == 'en' else f.question_ar,
                    'category': f.category or '', 'views': f.views_count} for f in faqs]
        return JsonResponse({'success': True, 'results': results, 'count': len(results)})

    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': str(_('حدث خطأ في البحث'))}, status=500)


# ==========================================
# Utility Functions
# ==========================================

def get_faq_stats():
    try:
        return FAQ.objects.filter(is_active=True).aggregate(
            total_faqs=Count('id'), total_views=Sum('views_count'),
            total_helpful=Sum('helpful_votes'), avg_helpful=Avg('helpful_votes')
        )
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return {'total_faqs': 0, 'total_views': 0, 'total_helpful': 0, 'avg_helpful': 0}