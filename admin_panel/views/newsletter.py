# admin_panel/views/newsletter.py

import json
import uuid
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.http import require_POST, require_http_methods

from contact.models import Newsletter, NewsletterLog, NewsletterSettings
from projects.models import Project
from beneficiary.models import OrphanForm, SpecialNeedsForm, FamilyForm

from .decorators import admin_required
from django.core.paginator import Paginator
User = get_user_model()


# ==================== الصفحة الرئيسية ====================

from django.core.paginator import Paginator

@admin_required
def newsletter_dashboard(request):
    nl_settings = NewsletterSettings.get_settings()

    stats = Newsletter.objects.aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(is_active=True)),
        inactive=Count('id', filter=Q(is_active=False)),
        confirmed=Count('id', filter=Q(confirmed_at__isnull=False)),
        daily=Count('id', filter=Q(frequency='daily',   is_active=True)),
        weekly=Count('id', filter=Q(frequency='weekly',  is_active=True)),
        monthly=Count('id', filter=Q(frequency='monthly', is_active=True)),
        total_sent=Sum('emails_sent'),
    )

    last_log = NewsletterLog.objects.first()

    # ── Pagination للسجل ──
    logs_qs   = NewsletterLog.objects.select_related('sent_by').order_by('-created_at')
    paginator = Paginator(logs_qs, 5)
    logs_page = paginator.get_page(request.GET.get('logs_page', 1))

    context = {
        'stats':       stats,
        'last_log':    last_log,
        'recent_logs': logs_page,
        'nl_settings': nl_settings,
        'page_title':  'إدارة النشرة البريدية',
    }
    return render(request, 'admin_panel/newsletter.html', context)


# ==================== بيانات المشتركين (AJAX) ====================

@admin_required
def newsletter_data(request):
    """جلب المشتركين مع فلترة وبحث"""
    search    = request.GET.get('q', '').strip()
    status    = request.GET.get('status', '')
    frequency = request.GET.get('frequency', '')
    page      = request.GET.get('page', 1)

    qs = Newsletter.objects.all().order_by('-subscribed_at')

    if search:
        qs = qs.filter(Q(email__icontains=search) | Q(name__icontains=search))
    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'inactive':
        qs = qs.filter(is_active=False)
    if frequency:
        qs = qs.filter(frequency=frequency)

    paginator = Paginator(qs, 10)
    page_obj  = paginator.get_page(page)

    data = []
    for sub in page_obj:
        data.append({
            'id':            sub.id,
            'email':         sub.email,
            'name':          sub.name,
            'frequency':     sub.get_frequency_display(),
            'frequency_val': sub.frequency,
            'is_active':     sub.is_active,
            'is_confirmed':  sub.is_confirmed,
            'emails_sent':   sub.emails_sent,
            'daily_sent':    sub.daily_sent,
            'weekly_sent':   sub.weekly_sent,
            'monthly_sent':  sub.monthly_sent,
            'last_sent':     sub.last_email_sent.strftime('%Y-%m-%d %H:%M') if sub.last_email_sent else None,
            'subscribed_at': sub.subscribed_at.strftime('%Y-%m-%d'),
        })

    return JsonResponse({
        'subscribers': data,
        'total':       paginator.count,
        'pages':       paginator.num_pages,
        'current':     page_obj.number,
    })


# ==================== تبديل حالة المشترك ====================

@require_POST
@admin_required
def toggle_subscriber(request):
    """تفعيل/إيقاف مشترك"""
    try:
        sub_id = request.POST.get('id')
        sub    = Newsletter.objects.get(id=sub_id)
        sub.is_active = not sub.is_active
        if not sub.is_active:
            sub.unsubscribed_at = timezone.now()
        sub.save(update_fields=['is_active', 'unsubscribed_at', 'updated_at'])
        return JsonResponse({'success': True, 'is_active': sub.is_active})
    except Newsletter.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'غير موجود'}, status=404)


# ==================== حذف مشترك ====================

@require_POST
@admin_required
def delete_subscriber(request):
    """حذف مشترك"""
    try:
        sub_id = request.POST.get('id')
        Newsletter.objects.filter(id=sub_id).delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ==================== تبديل إعدادات الإرسال ====================

@require_POST
@admin_required
def toggle_settings(request):
    """تفعيل/إيقاف الإرسال التلقائي"""
    try:
        data       = json.loads(request.body)
        nl_settings = NewsletterSettings.get_settings()
        field      = data.get('field')  # is_enabled, daily_enabled, weekly_enabled, monthly_enabled

        allowed = ['is_enabled', 'daily_enabled', 'weekly_enabled', 'monthly_enabled']
        if field not in allowed:
            return JsonResponse({'success': False, 'error': 'حقل غير صالح'}, status=400)

        setattr(nl_settings, field, not getattr(nl_settings, field))
        nl_settings.updated_by = request.user
        nl_settings.save()

        return JsonResponse({'success': True, 'value': getattr(nl_settings, field)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ==================== إرسال يدوي ====================

@require_POST
@admin_required
def send_manual(request):
    try:
        data      = json.loads(request.body)
        send_type = data.get('type', 'manual')
        targets   = data.get('targets', 'all')
        test_only = data.get('test_only', False)

        if test_only:
            _send_newsletter_email(
                to_email=request.user.email,
                send_type=send_type,
                unsubscribe_token='test-token',
            )
            return JsonResponse({'success': True, 'message': f'تم الإرسال التجريبي إلى {request.user.email}'})

        if targets == 'all':
            subscribers = Newsletter.objects.filter(is_active=True)
        else:
            subscriber_ids = data.get('subscriber_ids', [])
            subscribers    = Newsletter.objects.filter(id__in=subscriber_ids, is_active=True)

        total_sent = total_failed = 0
        recipients = []

        for sub in subscribers:
            try:
                _send_newsletter_email(
                    to_email=sub.email,
                    send_type=send_type,
                    unsubscribe_token=sub.confirmation_token,
                    subscriber_name=sub.name,
                )
                sub.increment_sent(send_type)
                total_sent += 1
                recipients.append({'email': sub.email, 'name': sub.name, 'success': True})
            except Exception:
                total_failed += 1
                recipients.append({'email': sub.email, 'name': sub.name, 'success': False})

        status = 'success' if total_failed == 0 else 'partial' if total_sent > 0 else 'failed'
        log = NewsletterLog.objects.create(
            send_type=send_type, status=status,
            sent_by=request.user, is_auto=False,
            total_sent=total_sent, total_failed=total_failed,
        )

        # حفظ المستلمين
        from contact.models import NewsletterLogRecipient
        NewsletterLogRecipient.objects.bulk_create([
            NewsletterLogRecipient(log=log, email=r['email'], name=r['name'], success=r['success'])
            for r in recipients
        ])

        return JsonResponse({'success': True, 'message': f'تم الإرسال: {total_sent} ناجح، {total_failed} فاشل'})


    # في newsletter_views.py عدّل send_manual مؤقتاً
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ==================== سجل العمليات ====================

@admin_required
def logs_data(request):
    """جلب سجل العمليات"""
    logs = NewsletterLog.objects.select_related('sent_by').values(
        'id', 'send_type', 'status', 'is_auto',
        'total_sent', 'total_failed', 'unsubscribed',
        'sent_by__username', 'created_at',
    )[:50]

    data = []
    for log in logs:
        data.append({
            **log,
            'send_type_display': dict(NewsletterLog.TYPE_CHOICES).get(log['send_type'], log['send_type']),
            'status_display':    dict(NewsletterLog.STATUS_CHOICES).get(log['status'], log['status']),
            'sent_by':           log['sent_by__username'] or 'تلقائي',
            'created_at':        log['created_at'].strftime('%Y-%m-%d %H:%M') if log['created_at'] else '',
        })

    return JsonResponse({'logs': data})


# ==================== دالة إرسال الإيميل ====================

def _build_stats():
    """بناء إحصائيات الموقع للرسالة"""
    orphans_free  = OrphanForm.objects.filter(sponsor__isnull=True).exclude(status='تم التكفل').count()
    specials_free = SpecialNeedsForm.objects.filter(sponsor__isnull=True).count()
    families_free = FamilyForm.objects.filter(sponsor__isnull=True).count()
    projects_active    = Project.objects.filter(is_active=True, status='active').count()
    projects_completed = Project.objects.filter(is_active=True, status='completed').count()

    # قصة مؤثرة
    story = OrphanForm.objects.filter(
        sponsor__isnull=True
    ).exclude(status='تم التكفل').order_by('?').first()

    # أبرز مشروع
    top_project = Project.objects.filter(
        is_active=True, status='active'
    ).order_by('-views_count').first()

    return {
        'orphans_free':       orphans_free,
        'specials_free':      specials_free,
        'families_free':      families_free,
        'total_need':         orphans_free + specials_free + families_free,
        'projects_active':    projects_active,
        'projects_completed': projects_completed,
        'story':              story,
        'top_project':        top_project,
    }


def _send_newsletter_email(to_email, send_type, unsubscribe_token, subscriber_name=''):
    """إرسال رسالة نشرة واحدة"""
    site_url  = getattr(settings, 'SITE_URL', 'https://nasaeem-palestine.com')
    site_name = getattr(settings, 'SITE_NAME', 'جمعية نسائم فلسطين الخيرية')

    type_labels = {
        'daily':   'النشرة اليومية',
        'weekly':  'النشرة الأسبوعية',
        'monthly': 'النشرة الشهرية',
        'manual':  'نشرة خاصة',
        'project': 'مشروع جديد',
    }

    stats = _build_stats()

    html_message = render_to_string('admin_panel/email/newsletter_email.html', {
        'subscriber_name':   subscriber_name or 'أخي/أختي الكريم/ة',
        'send_type':         send_type,
        'type_label':        type_labels.get(send_type, 'نشرة'),
        'site_name':         site_name,
        'site_url':          site_url,
        'unsubscribe_url':   f"{site_url}/contact/newsletter/unsubscribe/{unsubscribe_token}/",
        'donate_url':        f"{site_url}/projects/",
        'sponsor_url':       f"{site_url}/register/",
        'stats':             stats,
        'now':               timezone.now(),
    })

    send_mail(
        subject=f'{type_labels.get(send_type, "نشرة")} — {site_name}',
        message=strip_tags(html_message),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        html_message=html_message,
        fail_silently=False,
    )


# ==================== إرسال تلقائي (يُستدعى من Celery أو cron) ====================

def send_auto_newsletter(send_type):
    nl_settings = NewsletterSettings.get_settings()
    if not nl_settings.is_enabled:
        return 0, 0

    type_map = {
        'daily':   nl_settings.daily_enabled,
        'weekly':  nl_settings.weekly_enabled,
        'monthly': nl_settings.monthly_enabled,
    }
    if not type_map.get(send_type, False):
        return 0, 0

    subscribers  = Newsletter.objects.filter(
        is_active=True, confirmed_at__isnull=False, frequency=send_type,
    )
    total_sent = total_failed = 0
    recipients = []

    for sub in subscribers:
        try:
            _send_newsletter_email(
                to_email=sub.email, send_type=send_type,
                unsubscribe_token=sub.confirmation_token,
                subscriber_name=sub.name,
            )
            sub.increment_sent(send_type)
            total_sent += 1
            recipients.append({'email': sub.email, 'name': sub.name, 'success': True})
        except Exception:
            total_failed += 1
            recipients.append({'email': sub.email, 'name': sub.name, 'success': False})

    status = 'success' if total_failed == 0 else 'partial' if total_sent > 0 else 'failed'
    log = NewsletterLog.objects.create(
        send_type=send_type, status=status,
        sent_by=None, is_auto=True,
        total_sent=total_sent, total_failed=total_failed,
    )

    from contact.models import NewsletterLogRecipient
    NewsletterLogRecipient.objects.bulk_create([
        NewsletterLogRecipient(log=log, email=r['email'], name=r['name'], success=r['success'])
        for r in recipients
    ])

    return total_sent, total_failed


@admin_required
def log_recipients(request, log_id):
    """جلب المرسل إليهم في سجل معين"""
    from contact.models import NewsletterLogRecipient
    search = request.GET.get('q', '').strip()
    qs = NewsletterLogRecipient.objects.filter(log_id=log_id)
    if search:
        qs = qs.filter(email__icontains=search)
    data = list(qs.values('email', 'name', 'success', 'sent_at'))
    for r in data:
        r['sent_at'] = r['sent_at'].strftime('%Y-%m-%d %H:%M') if r['sent_at'] else ''
    return JsonResponse({'recipients': data, 'total': qs.count()})


@admin_required
def logs_page_data(request):
    """جلب سجل العمليات بـ AJAX"""
    page    = request.GET.get('page', 1)
    logs_qs = NewsletterLog.objects.select_related('sent_by').order_by('-created_at')
    paginator = Paginator(logs_qs, 5)
    logs_page = paginator.get_page(page)

    data = []
    for log in logs_page:
        data.append({
            'id':         log.id,
            'send_type':  log.send_type,
            'type_label': log.get_send_type_display(),
            'status':     log.status,
            'status_label': log.get_status_display(),
            'total_sent':   log.total_sent,
            'total_failed': log.total_failed,
            'unsubscribed': log.unsubscribed,
            'is_auto':      log.is_auto,
            'sent_by':      log.sent_by.username if log.sent_by else 'تلقائي',
            'created_at':   log.created_at.strftime('%Y/%m/%d %H:%M'),
        })

    return JsonResponse({
        'logs':    data,
        'pages':   paginator.num_pages,
        'current': logs_page.number,
        'total':   paginator.count,
    })