
import logging
import csv
import io
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid
import os

from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.db.models import Count, Q, Avg
from django.core.files.storage import default_storage
from django.core.cache import cache

from . import models

try:
    from celery import shared_task
    from celery.exceptions import Retry

    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False


    # إنشاء decorator بديل إذا لم يكن Celery متوفر
    def shared_task(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

from .models import ContactMessage, Newsletter, SocialMediaContact, ContactInfo, FAQ

logger = logging.getLogger('contact.tasks')


# =================== مهام إرسال الإيميلات ===================

@shared_task(bind=True, max_retries=3)
def send_contact_notification(self, message_id: int):
    """إرسال إشعار للإدارة برسالة تواصل جديدة"""
    try:
        message = ContactMessage.objects.get(id=message_id)

        # التحقق من أن الرسالة جديدة
        if message.status != 'new':
            logger.info(f"تم تخطي إرسال الإشعار للرسالة {message_id} - الحالة: {message.status}")
            return

        # تحديد قائمة الإداريين
        admin_emails = getattr(settings, 'ADMIN_EMAIL_LIST', [])
        if not admin_emails:
            admin_emails = [settings.DEFAULT_FROM_EMAIL]

        # إعداد الموضوع
        priority_prefix = "🔥 عاجل - " if message.priority == 'urgent' else "📩 "
        subject = f'{priority_prefix}رسالة تواصل جديدة: {message.subject}'

        # إنشاء محتوى HTML
        html_message = render_to_string('contact/email/admin_notification.html', {
            'message': message,
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
            'admin_panel_url': f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/admin/",
        })

        text_message = strip_tags(html_message)

        # إرسال البريد
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=admin_emails,
        )
        email.attach_alternative(html_message, "text/html")

        # إرفاق الملف إذا كان موجوداً
        if message.attachment:
            try:
                email.attach_file(message.attachment.path)
            except Exception as e:
                logger.warning(f"فشل في إرفاق الملف للرسالة {message_id}: {e}")

        email.send()

        # تسجيل النجاح
        logger.info(f"تم إرسال إشعار الإدارة بنجاح للرسالة {message_id}")

        # تحديث الإحصائيات
        cache.delete('admin_notifications_count')

        return {
            'success': True,
            'message_id': message_id,
            'sent_to': len(admin_emails),
            'timestamp': timezone.now().isoformat()
        }

    except ContactMessage.DoesNotExist:
        logger.error(f"الرسالة {message_id} غير موجودة")
        return {'success': False, 'error': 'Message not found'}

    except Exception as exc:
        logger.error(f"فشل في إرسال إشعار الإدارة للرسالة {message_id}: {exc}")

        if self.request.retries < self.max_retries:
            # إعادة المحاولة بعد 5 دقائق
            raise self.retry(countdown=300, exc=exc)

        return {'success': False, 'error': str(exc)}


@shared_task(bind=True, max_retries=3)
def send_contact_confirmation(self, message_id: int):
    """إرسال رسالة تأكيد استلام للمرسل"""
    try:
        message = ContactMessage.objects.get(id=message_id)

        subject = f'تم استلام رسالتك - {getattr(settings, "SITE_NAME", "جمعية نسائم فلسطين الخيرية")}'

        html_message = render_to_string('contact/email/confirmation.html', {
            'message': message,
            'site_name': getattr(settings, 'SITE_NAME', 'جمعية نسائم فلسطين الخيرية'),
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', settings.DEFAULT_FROM_EMAIL),
        })

        text_message = strip_tags(html_message)

        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[message.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"تم إرسال تأكيد الاستلام بنجاح للرسالة {message_id}")

        return {
            'success': True,
            'message_id': message_id,
            'sent_to': message.email,
            'timestamp': timezone.now().isoformat()
        }

    except ContactMessage.DoesNotExist:
        logger.error(f"الرسالة {message_id} غير موجودة")
        return {'success': False, 'error': 'Message not found'}

    except Exception as exc:
        logger.error(f"فشل في إرسال تأكيد الاستلام للرسالة {message_id}: {exc}")

        if self.request.retries < self.max_retries:
            raise self.retry(countdown=180, exc=exc)  # إعادة المحاولة بعد 3 دقائق

        return {'success': False, 'error': str(exc)}


@shared_task(bind=True, max_retries=3)
def send_newsletter_confirmation(self, subscription_id: int):
    """إرسال رسالة تأكيد اشتراك النشرة البريدية"""
    try:
        subscription = Newsletter.objects.get(id=subscription_id)

        # إنشاء token جديد إذا لم يكن موجوداً
        if not subscription.confirmation_token:
            subscription.confirmation_token = str(uuid.uuid4())
            subscription.save(update_fields=['confirmation_token'])

        subject = f'تأكيد الاشتراك في النشرة البريدية - {getattr(settings, "SITE_NAME", "نسائم فلسطين")}'

        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        confirmation_url = f"{site_url}/contact/newsletter/confirm/{subscription.confirmation_token}/"
        unsubscribe_url = f"{site_url}/contact/newsletter/unsubscribe/{subscription.confirmation_token}/"

        html_message = render_to_string('contact/email/newsletter_confirmation.html', {
            'subscription': subscription,
            'confirmation_url': confirmation_url,
            'unsubscribe_url': unsubscribe_url,
            'site_name': getattr(settings, 'SITE_NAME', 'جمعية نسائم فلسطين الخيرية'),
            'site_url': site_url,
        })

        text_message = strip_tags(html_message)

        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[subscription.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"تم إرسال تأكيد اشتراك النشرة إلى {subscription.email}")

        return {
            'success': True,
            'subscription_id': subscription_id,
            'email': subscription.email,
            'confirmation_url': confirmation_url,
            'timestamp': timezone.now().isoformat()
        }

    except Newsletter.DoesNotExist:
        logger.error(f"الاشتراك {subscription_id} غير موجود")
        return {'success': False, 'error': 'Subscription not found'}

    except Exception as exc:
        logger.error(f"فشل في إرسال تأكيد النشرة للاشتراك {subscription_id}: {exc}")

        if self.request.retries < self.max_retries:
            raise self.retry(countdown=240, exc=exc)  # إعادة المحاولة بعد 4 دقائق

        return {'success': False, 'error': str(exc)}


@shared_task
def send_newsletter_bulk(subject: str, content: str, recipient_ids: List[int] = None):
    """إرسال النشرة البريدية بالجملة"""
    try:
        # تحديد المستلمين
        recipients_query = Newsletter.objects.filter(
            is_active=True,
            confirmed_at__isnull=False
        )

        if recipient_ids:
            recipients_query = recipients_query.filter(id__in=recipient_ids)

        recipients = list(recipients_query.values('id', 'email', 'name', 'confirmation_token'))

        if not recipients:
            logger.warning("لا يوجد مشتركين نشطين لإرسال النشرة")
            return {'success': False, 'error': 'No active subscribers'}

        # إعداد الاتصال بالبريد
        connection = get_connection()

        sent_count = 0
        failed_count = 0
        failed_emails = []

        # إرسال بالدفعات (50 إيميل في المرة)
        batch_size = 50
        for i in range(0, len(recipients), batch_size):
            batch = recipients[i:i + batch_size]

            for recipient in batch:
                try:
                    # تخصيص المحتوى لكل مستلم
                    unsubscribe_url = f"{getattr(settings, 'SITE_URL', '')}/contact/newsletter/unsubscribe/{recipient['confirmation_token']}/"

                    personalized_content = content + f"""

                    ---
                    إذا كنت لا تريد تلقي هذه الرسائل، يمكنك إلغاء الاشتراك من خلال الرابط التالي:
                    {unsubscribe_url}
                    """

                    email = EmailMultiAlternatives(
                        subject=subject,
                        body=personalized_content,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[recipient['email']],
                        connection=connection
                    )

                    # إضافة اسم المستلم إذا كان متوفراً
                    if recipient['name']:
                        email.extra_headers['To'] = f"{recipient['name']} <{recipient['email']}>"

                    email.send()
                    sent_count += 1

                    # تحديث إحصائيات المشترك
                    Newsletter.objects.filter(id=recipient['id']).update(
                        emails_sent=models.F('emails_sent') + 1,
                        last_email_sent=timezone.now()
                    )

                except Exception as e:
                    failed_count += 1
                    failed_emails.append(recipient['email'])
                    logger.error(f"فشل في إرسال النشرة إلى {recipient['email']}: {e}")

            # راحة قصيرة بين الدفعات لتجنب الحمولة الزائدة
            if i + batch_size < len(recipients):
                import time
                time.sleep(2)

        connection.close()

        logger.info(f"تم إرسال النشرة البريدية: {sent_count} نجح، {failed_count} فشل")

        return {
            'success': True,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'failed_emails': failed_emails,
            'total_recipients': len(recipients),
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"فشل في إرسال النشرة البريدية بالجملة: {e}")
        return {'success': False, 'error': str(e)}


# =================== مهام الصيانة والتنظيف ===================

@shared_task
def cleanup_old_messages(days: int = 365):
    """تنظيف الرسائل القديمة"""
    try:
        cutoff_date = timezone.now() - timedelta(days=days)

        # البحث عن الرسائل القديمة المكتملة
        old_messages = ContactMessage.objects.filter(
            created_at__lt=cutoff_date,
            status='closed'
        )

        # حفظ الإحصائيات قبل الحذف
        deleted_count = old_messages.count()

        if deleted_count == 0:
            logger.info("لا توجد رسائل قديمة للحذف")
            return {'success': True, 'deleted_count': 0}

        # إنشاء نسخة احتياطية قبل الحذف
        backup_data = []
        for message in old_messages:
            backup_data.append({
                'id': message.id,
                'name': message.name,
                'email': message.email,
                'subject': message.subject,
                'message': message.message,
                'created_at': message.created_at.isoformat(),
                'status': message.status,
            })

        # حفظ النسخة الاحتياطية
        backup_filename = f'contact_messages_backup_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json'
        backup_path = os.path.join('backups', 'contact', backup_filename)

        import json
        backup_content = json.dumps(backup_data, ensure_ascii=False, indent=2)
        default_storage.save(backup_path, io.StringIO(backup_content))

        # حذف الرسائل
        old_messages.delete()

        logger.info(f"تم حذف {deleted_count} رسالة قديمة وحفظ نسخة احتياطية في {backup_path}")

        return {
            'success': True,
            'deleted_count': deleted_count,
            'backup_path': backup_path,
            'cutoff_date': cutoff_date.isoformat()
        }

    except Exception as e:
        logger.error(f"فشل في تنظيف الرسائل القديمة: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def cleanup_unconfirmed_subscriptions(days: int = 7):
    """حذف الاشتراكات غير المؤكدة بعد فترة معينة"""
    try:
        cutoff_date = timezone.now() - timedelta(days=days)

        unconfirmed = Newsletter.objects.filter(
            subscribed_at__lt=cutoff_date,
            confirmed_at__isnull=True,
            is_active=True
        )

        deleted_count = unconfirmed.count()

        if deleted_count > 0:
            # حفظ قائمة الإيميلات المحذوفة للمراجعة
            deleted_emails = list(unconfirmed.values_list('email', flat=True))
            unconfirmed.delete()

            logger.info(f"تم حذف {deleted_count} اشتراك غير مؤكد")

            return {
                'success': True,
                'deleted_count': deleted_count,
                'deleted_emails': deleted_emails,
                'cutoff_date': cutoff_date.isoformat()
            }
        else:
            return {'success': True, 'deleted_count': 0}

    except Exception as e:
        logger.error(f"فشل في تنظيف الاشتراكات غير المؤكدة: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def optimize_database_tables():
    """تحسين جداول قاعدة البيانات"""
    try:
        from django.db import connection

        with connection.cursor() as cursor:
            # تحسين جداول التطبيق
            tables = [
                'contact_contactmessage',
                'contact_newsletter',
                'contact_socialmediacontact',
                'contact_contactinfo',
                'contact_faq'
            ]

            optimized_tables = []

            for table in tables:
                try:
                    # للـ MySQL
                    if connection.vendor == 'mysql':
                        cursor.execute(f"OPTIMIZE TABLE {table}")
                    # للـ PostgreSQL
                    elif connection.vendor == 'postgresql':
                        cursor.execute(f"VACUUM ANALYZE {table}")

                    optimized_tables.append(table)

                except Exception as table_error:
                    logger.warning(f"فشل في تحسين الجدول {table}: {table_error}")

        logger.info(f"تم تحسين {len(optimized_tables)} جدول من جداول قاعدة البيانات")

        return {
            'success': True,
            'optimized_tables': optimized_tables,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"فشل في تحسين جداول قاعدة البيانات: {e}")
        return {'success': False, 'error': str(e)}


# =================== مهام التقارير والإحصائيات ===================

@shared_task
def generate_daily_report():
    """إنشاء تقرير يومي لأنشطة التواصل"""
    try:
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        # إحصائيات الرسائل
        today_messages = ContactMessage.objects.filter(created_at__date=today).count()
        yesterday_messages = ContactMessage.objects.filter(created_at__date=yesterday).count()

        new_messages = ContactMessage.objects.filter(status='new').count()
        urgent_messages = ContactMessage.objects.filter(
            priority='urgent',
            status__in=['new', 'reading']
        ).count()

        # إحصائيات النشرة البريدية
        today_subscriptions = Newsletter.objects.filter(
            subscribed_at__date=today,
            is_active=True
        ).count()

        total_active_subscribers = Newsletter.objects.filter(
            is_active=True,
            confirmed_at__isnull=False
        ).count()

        # إحصائيات وسائل التواصل الاجتماعي
        social_clicks_today = SocialMediaContact.objects.filter(
            is_active=True,
            updated_at__date=today
        ).aggregate(
            total_clicks=models.Sum('clicks_count')
        )['total_clicks'] or 0

        # إحصائيات الأسئلة الشائعة
        faq_views_today = FAQ.objects.filter(
            updated_at__date=today
        ).aggregate(
            total_views=models.Sum('views_count')
        )['total_views'] or 0

        # إعداد التقرير
        report_data = {
            'date': today.isoformat(),
            'messages': {
                'today': today_messages,
                'yesterday': yesterday_messages,
                'change': today_messages - yesterday_messages,
                'pending': new_messages,
                'urgent': urgent_messages,
            },
            'newsletter': {
                'new_subscriptions_today': today_subscriptions,
                'total_active_subscribers': total_active_subscribers,
            },
            'social_media': {
                'clicks_today': social_clicks_today,
            },
            'faq': {
                'views_today': faq_views_today,
            },
            'summary': {
                'total_interactions': today_messages + today_subscriptions + social_clicks_today,
                'requires_attention': new_messages + urgent_messages > 0,
            }
        }

        # حفظ التقرير
        report_filename = f'daily_report_{today.strftime("%Y_%m_%d")}.json'
        report_path = os.path.join('reports', 'contact', 'daily', report_filename)

        import json
        report_json = json.dumps(report_data, ensure_ascii=False, indent=2)
        default_storage.save(report_path, io.StringIO(report_json))

        # إرسال التقرير للإدارة إذا كان هناك نشاط مهم
        if (new_messages > 0 or urgent_messages > 0 or today_messages > yesterday_messages * 1.5):
            send_daily_report_email.delay(report_data, report_path)

        logger.info(f"تم إنشاء التقرير اليومي: {report_path}")

        return {
            'success': True,
            'report_path': report_path,
            'report_data': report_data,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"فشل في إنشاء التقرير اليومي: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_daily_report_email(report_data: Dict[str, Any], report_path: str):
    """إرسال التقرير اليومي بالبريد الإلكتروني"""
    try:
        admin_emails = getattr(settings, 'ADMIN_EMAIL_LIST', [settings.DEFAULT_FROM_EMAIL])

        subject = f"التقرير اليومي لنشاطات التواصل - {report_data['date']}"

        # إنشاء محتوى التقرير
        template_context = {
            'report': report_data,
            'site_name': getattr(settings, 'SITE_NAME', 'جمعية نسائم فلسطين الخيرية'),
            'date': report_data['date']
        }

        html_content = render_to_string('contact/email/daily_report.html', template_context)
        text_content = f"""
        التقرير اليومي لنشاطات التواصل - {report_data['date']}

        الرسائل:
        - اليوم: {report_data['messages']['today']}
        - أمس: {report_data['messages']['yesterday']}
        - التغيير: {report_data['messages']['change']:+}
        - في الانتظار: {report_data['messages']['pending']}
        - عاجلة: {report_data['messages']['urgent']}

        النشرة البريدية:
        - اشتراكات جديدة اليوم: {report_data['newsletter']['new_subscriptions_today']}
        - إجمالي المشتركين النشطين: {report_data['newsletter']['total_active_subscribers']}

        وسائل التواصل الاجتماعي:
        - نقرات اليوم: {report_data['social_media']['clicks_today']}

        الأسئلة الشائعة:
        - مشاهدات اليوم: {report_data['faq']['views_today']}
        """

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=admin_emails,
        )
        email.attach_alternative(html_content, "text/html")

        # إرفاق ملف التقرير JSON
        if default_storage.exists(report_path):
            report_content = default_storage.open(report_path).read()
            email.attach(f"daily_report_{report_data['date']}.json", report_content, 'application/json')

        email.send()

        logger.info(f"تم إرسال التقرير اليومي بالبريد الإلكتروني إلى {len(admin_emails)} مدير")

        return {
            'success': True,
            'sent_to': admin_emails,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"فشل في إرسال التقرير اليومي: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def export_contact_data(export_type: str = 'csv', date_from: str = None, date_to: str = None):
    """تصدير بيانات التواصل"""
    try:
        # تحديد نطاق التاريخ
        if date_from:
            date_from = datetime.fromisoformat(date_from).date()
        if date_to:
            date_to = datetime.fromisoformat(date_to).date()

        # جلب البيانات
        messages_query = ContactMessage.objects.all()
        if date_from:
            messages_query = messages_query.filter(created_at__date__gte=date_from)
        if date_to:
            messages_query = messages_query.filter(created_at__date__lte=date_to)

        messages = messages_query.order_by('-created_at')

        # إنشاء الملف
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f'contact_export_{timestamp}.{export_type}'

        if export_type == 'csv':
            # تصدير CSV
            output = io.StringIO()
            writer = csv.writer(output)

            # العناوين
            writer.writerow([
                'ID', 'الاسم', 'البريد الإلكتروني', 'الهاتف', 'الموضوع',
                'الرسالة', 'الحالة', 'الأولوية', 'تاريخ الإرسال', 'تاريخ الرد'
            ])

            # البيانات
            for message in messages:
                writer.writerow([
                    message.id,
                    message.name,
                    message.email,
                    message.phone or '',
                    message.subject,
                    message.message,
                    message.get_status_display(),
                    message.get_priority_display(),
                    message.created_at.strftime('%Y-%m-%d %H:%M'),
                    message.replied_at.strftime('%Y-%m-%d %H:%M') if message.replied_at else ''
                ])

            content = output.getvalue().encode('utf-8-sig')  # BOM للعربية
            content_type = 'text/csv'

        elif export_type == 'json':
            # تصدير JSON
            data = []
            for message in messages:
                data.append({
                    'id': message.id,
                    'name': message.name,
                    'email': message.email,
                    'phone': message.phone,
                    'subject': message.subject,
                    'message': message.message,
                    'status': message.status,
                    'priority': message.priority,
                    'created_at': message.created_at.isoformat(),
                    'replied_at': message.replied_at.isoformat() if message.replied_at else None,
                })

            import json
            content = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
            content_type = 'application/json'

        else:
            raise ValueError(f"نوع التصدير غير مدعوم: {export_type}")

        # حفظ الملف
        export_path = os.path.join('exports', 'contact', filename)
        default_storage.save(export_path, io.BytesIO(content))

        logger.info(f"تم تصدير {messages.count()} رسالة إلى {export_path}")

        return {
            'success': True,
            'filename': filename,
            'export_path': export_path,
            'records_count': messages.count(),
            'export_type': export_type,
            'date_range': {
                'from': date_from.isoformat() if date_from else None,
                'to': date_to.isoformat() if date_to else None,
            },
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"فشل في تصدير البيانات: {e}")
        return {'success': False, 'error': str(e)}


# =================== مهام مجدولة دورية ===================

@shared_task
def update_social_media_stats():
    """تحديث إحصائيات وسائل التواصل الاجتماعي"""
    try:
        social_platforms = SocialMediaContact.objects.filter(is_active=True)
        updated_count = 0

        for platform in social_platforms:
            # هنا يمكن إضافة تكامل مع APIs الخاصة بكل منصة
            # للحصول على إحصائيات حقيقية (المتابعين، التفاعل، إلخ)

            # حالياً نحدث فقط timestamp للتتبع
            platform.updated_at = timezone.now()
            platform.save(update_fields=['updated_at'])
            updated_count += 1

        # مسح الكاش المرتبط
        cache.delete('social_links_cache')
        cache.delete('social_statistics')

        logger.info(f"تم تحديث إحصائيات {updated_count} منصة تواصل اجتماعي")

        return {
            'success': True,
            'updated_count': updated_count,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"فشل في تحديث إحصائيات وسائل التواصل الاجتماعي: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def calculate_response_time_metrics():
    """حساب متوسط أوقات الاستجابة"""
    try:
        # الرسائل التي تم الرد عليها خلال آخر 30 يوم
        thirty_days_ago = timezone.now() - timedelta(days=30)

        replied_messages = ContactMessage.objects.filter(
            status='replied',
            replied_at__isnull=False,
            replied_at__gte=thirty_days_ago
        )

        if not replied_messages.exists():
            logger.info("لا توجد رسائل تم الرد عليها لحساب أوقات الاستجابة")
            return {'success': True, 'message': 'No replied messages to calculate'}

        # حساب أوقات الاستجابة
        response_times = []
        for message in replied_messages:
            if message.replied_at and message.created_at:
                response_time = message.replied_at - message.created_at
                response_times.append(response_time.total_seconds() / 3600)  # بالساعات

        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)

            # حساب النسبة المئوية للرد خلال 24 ساعة
            quick_responses = [t for t in response_times if t <= 24]
            quick_response_rate = (len(quick_responses) / len(response_times)) * 100

            # حفظ الإحصائيات في الكاش
            metrics = {
                'avg_response_time_hours': round(avg_response_time, 2),
                'min_response_time_hours': round(min_response_time, 2),
                'max_response_time_hours': round(max_response_time, 2),
                'quick_response_rate_24h': round(quick_response_rate, 1),
                'total_replied_messages': len(response_times),
                'calculated_at': timezone.now().isoformat(),
            }

            cache.set('response_time_metrics', metrics, 60 * 60 * 24)  # 24 ساعة

            logger.info(f"تم حساب أوقات الاستجابة: متوسط {avg_response_time:.1f} ساعة")

            return {
                'success': True,
                'metrics': metrics,
                'timestamp': timezone.now().isoformat()
            }

        return {'success': True, 'message': 'No response times to calculate'}

    except Exception as e:
        logger.error(f"فشل في حساب أوقات الاستجابة: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_weekly_newsletter():
    """إرسال النشرة الأسبوعية التلقائية"""
    try:
        # الحصول على المشتركين الأسبوعيين النشطين
        weekly_subscribers = Newsletter.objects.filter(
            is_active=True,
            confirmed_at__isnull=False,
            frequency='weekly'
        )

        if not weekly_subscribers.exists():
            logger.info("لا يوجد مشتركين أسبوعيين نشطين")
            return {'success': True, 'message': 'No weekly subscribers'}

        # إنشاء محتوى النشرة الأسبوعية
        week_start = timezone.now() - timedelta(days=7)

        # أحدث المشاريع (من تطبيق المشاريع إذا كان متوفراً)
        recent_content = []
        try:
            from projects.models import Project
            recent_projects = Project.objects.filter(
                is_active=True,
                created_at__gte=week_start
            ).order_by('-created_at')[:3]

            if recent_projects:
                recent_content.append("🆕 مشاريع جديدة:")
                for project in recent_projects:
                    recent_content.append(f"• {project.title_ar}")
        except ImportError:
            pass

        # إحصائيات الأسبوع
        week_stats = {
            'new_messages': ContactMessage.objects.filter(created_at__gte=week_start).count(),
            'new_subscribers': Newsletter.objects.filter(subscribed_at__gte=week_start).count(),
        }

        # بناء محتوى النشرة
        newsletter_content = f"""
مرحباً بك في النشرة الأسبوعية لجمعية نسائم فلسطين الخيرية

{chr(10).join(recent_content) if recent_content else ""}

📊 إحصائيات الأسبوع:
- رسائل جديدة: {week_stats['new_messages']}
- مشتركين جدد: {week_stats['new_subscribers']}

شكراً لك لكونك جزءاً من عائلتنا الكريمة.

مع تحياتنا،
فريق جمعية نسائم فلسطين الخيرية
        """

        # إرسال النشرة
        result = send_newsletter_bulk.delay(
            subject=f"النشرة الأسبوعية - {timezone.now().strftime('%d/%m/%Y')}",
            content=newsletter_content,
            recipient_ids=list(weekly_subscribers.values_list('id', flat=True))
        )

        logger.info(f"تم جدولة إرسال النشرة الأسبوعية لـ {weekly_subscribers.count()} مشترك")

        return {
            'success': True,
            'subscribers_count': weekly_subscribers.count(),
            'task_id': result.id if hasattr(result, 'id') else None,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"فشل في إرسال النشرة الأسبوعية: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def backup_contact_data():
    """إنشاء نسخة احتياطية من بيانات التواصل"""
    try:
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')

        # بيانات للنسخ الاحتياطي
        backup_data = {
            'backup_date': timezone.now().isoformat(),
            'contact_messages': [],
            'newsletter_subscriptions': [],
            'social_media_contacts': [],
            'contact_info': [],
            'faqs': [],
        }

        # نسخ رسائل التواصل (آخر 3 أشهر)
        three_months_ago = timezone.now() - timedelta(days=90)
        messages = ContactMessage.objects.filter(created_at__gte=three_months_ago)

        for message in messages:
            backup_data['contact_messages'].append({
                'id': message.id,
                'name': message.name,
                'email': message.email,
                'phone': message.phone,
                'subject': message.subject,
                'message': message.message,
                'status': message.status,
                'priority': message.priority,
                'created_at': message.created_at.isoformat(),
                'replied_at': message.replied_at.isoformat() if message.replied_at else None,
            })

        # نسخ اشتراكات النشرة البريدية النشطة
        subscriptions = Newsletter.objects.filter(is_active=True)
        for sub in subscriptions:
            backup_data['newsletter_subscriptions'].append({
                'id': sub.id,
                'email': sub.email,
                'name': sub.name,
                'frequency': sub.frequency,
                'topics': sub.topics,
                'subscribed_at': sub.subscribed_at.isoformat(),
                'confirmed_at': sub.confirmed_at.isoformat() if sub.confirmed_at else None,
            })

        # نسخ وسائل التواصل الاجتماعي
        social_links = SocialMediaContact.objects.all()
        for link in social_links:
            backup_data['social_media_contacts'].append({
                'id': link.id,
                'platform': link.platform,
                'username': link.username,
                'url': link.url,
                'is_active': link.is_active,
                'clicks_count': link.clicks_count,
            })

        # نسخ معلومات التواصل
        contact_info = ContactInfo.objects.all()
        for info in contact_info:
            backup_data['contact_info'].append({
                'id': info.id,
                'type': info.type,
                'label': info.label,
                'value': info.value,
                'is_active': info.is_active,
            })

        # نسخ الأسئلة الشائعة
        faqs = FAQ.objects.filter(is_active=True)
        for faq in faqs:
            backup_data['faqs'].append({
                'id': faq.id,
                'question_ar': faq.question_ar,
                'answer_ar': faq.answer_ar,
                'category': faq.category,
                'views_count': faq.views_count,
                'helpful_votes': faq.helpful_votes,
            })

        # حفظ النسخة الاحتياطية
        import json
        backup_json = json.dumps(backup_data, ensure_ascii=False, indent=2)
        backup_filename = f'contact_backup_{timestamp}.json'
        backup_path = os.path.join('backups', 'contact', 'full', backup_filename)

        default_storage.save(backup_path, io.StringIO(backup_json))

        # ضغط النسخة الاحتياطية
        import gzip
        compressed_content = gzip.compress(backup_json.encode('utf-8'))
        compressed_filename = f'contact_backup_{timestamp}.json.gz'
        compressed_path = os.path.join('backups', 'contact', 'compressed', compressed_filename)

        default_storage.save(compressed_path, io.BytesIO(compressed_content))

        # حساب الإحصائيات
        stats = {
            'messages_count': len(backup_data['contact_messages']),
            'subscriptions_count': len(backup_data['newsletter_subscriptions']),
            'social_links_count': len(backup_data['social_media_contacts']),
            'contact_info_count': len(backup_data['contact_info']),
            'faqs_count': len(backup_data['faqs']),
        }

        logger.info(f"تم إنشاء نسخة احتياطية: {backup_path}")

        # حذف النسخ الاحتياطية القديمة (الاحتفاظ بآخر 30 نسخة)
        cleanup_old_backups.delay()

        return {
            'success': True,
            'backup_path': backup_path,
            'compressed_path': compressed_path,
            'statistics': stats,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"فشل في إنشاء النسخة الاحتياطية: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def cleanup_old_backups(keep_count: int = 30):
    """حذف النسخ الاحتياطية القديمة"""
    try:
        import os
        from django.core.files.storage import default_storage

        # مجلدات النسخ الاحتياطية
        backup_folders = [
            'backups/contact/full/',
            'backups/contact/compressed/',
            'backups/contact/',
        ]

        deleted_files = []

        for folder in backup_folders:
            try:
                # الحصول على قائمة الملفات
                if default_storage.exists(folder):
                    files = default_storage.listdir(folder)[1]  # الملفات فقط، ليس المجلدات

                    # ترتيب الملفات حسب التاريخ (من الاسم)
                    backup_files = [f for f in files if f.startswith('contact_backup_')]
                    backup_files.sort(reverse=True)  # الأحدث أولاً

                    # حذف الملفات الزائدة
                    if len(backup_files) > keep_count:
                        files_to_delete = backup_files[keep_count:]

                        for file_to_delete in files_to_delete:
                            file_path = os.path.join(folder, file_to_delete)
                            if default_storage.exists(file_path):
                                default_storage.delete(file_path)
                                deleted_files.append(file_path)

            except Exception as folder_error:
                logger.warning(f"فشل في تنظيف المجلد {folder}: {folder_error}")

        logger.info(f"تم حذف {len(deleted_files)} ملف نسخة احتياطية قديمة")

        return {
            'success': True,
            'deleted_files_count': len(deleted_files),
            'deleted_files': deleted_files,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"فشل في تنظيف النسخ الاحتياطية القديمة: {e}")
        return {'success': False, 'error': str(e)}


# =================== مهام مساعدة ===================

@shared_task
def clear_all_caches():
    """مسح جميع كاش التطبيق"""
    try:
        from .context_processors import clear_contact_context_cache

        # مسح كاش معالجات السياق
        clear_contact_context_cache()

        # مسح كاش إضافي
        cache_keys = [
            'contact_statistics',
            'popular_faqs',
            'social_stats',
            'newsletter_stats',
            'response_time_metrics',
        ]

        deleted_keys = []
        for key in cache_keys:
            if cache.delete(key):
                deleted_keys.append(key)

        logger.info(f"تم مسح {len(deleted_keys)} مفتاح كاش")

        return {
            'success': True,
            'cleared_keys': deleted_keys,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"فشل في مسح الكاش: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def health_check():
    """فحص حالة التطبيق"""
    try:
        health_status = {
            'database': False,
            'email': False,
            'storage': False,
            'cache': False,
        }

        # فحص قاعدة البيانات
        try:
            ContactMessage.objects.count()
            health_status['database'] = True
        except Exception as db_error:
            logger.error(f"مشكلة في قاعدة البيانات: {db_error}")

        # فحص البريد الإلكتروني
        try:
            from django.core.mail import get_connection
            connection = get_connection()
            connection.open()
            connection.close()
            health_status['email'] = True
        except Exception as email_error:
            logger.error(f"مشكلة في البريد الإلكتروني: {email_error}")

        # فحص التخزين
        try:
            test_file = 'health_check_test.txt'
            default_storage.save(test_file, io.StringIO('test'))
            default_storage.delete(test_file)
            health_status['storage'] = True
        except Exception as storage_error:
            logger.error(f"مشكلة في التخزين: {storage_error}")

        # فحص الكاش
        try:
            cache.set('health_check', 'test', 60)
            if cache.get('health_check') == 'test':
                health_status['cache'] = True
            cache.delete('health_check')
        except Exception as cache_error:
            logger.error(f"مشكلة في الكاش: {cache_error}")

        overall_health = all(health_status.values())

        result = {
            'success': True,
            'overall_health': overall_health,
            'components': health_status,
            'timestamp': timezone.now().isoformat()
        }

        if overall_health:
            logger.info("فحص الحالة: جميع المكونات تعمل بشكل طبيعي")
        else:
            logger.warning(f"فحص الحالة: مشاكل في المكونات: {health_status}")

        return result

    except Exception as e:
        logger.error(f"فشل في فحص الحالة: {e}")
        return {'success': False, 'error': str(e)}


# =================== إعداد المهام الدورية ===================

if CELERY_AVAILABLE:
    # يمكن استخدام celery beat لجدولة المهام الدورية
    # مثال على الإعداد في settings.py:
    """
    from celery.schedules import crontab

    CELERY_BEAT_SCHEDULE = {
        'daily-report': {
            'task': 'contact.tasks.generate_daily_report',
            'schedule': crontab(hour=8, minute=0),  # كل يوم الساعة 8 صباحاً
        },
        'weekly-newsletter': {
            'task': 'contact.tasks.send_weekly_newsletter', 
            'schedule': crontab(day_of_week=0, hour=9, minute=0),  # كل أحد الساعة 9 صباحاً
        },
        'cleanup-old-messages': {
            'task': 'contact.tasks.cleanup_old_messages',
            'schedule': crontab(day_of_month=1, hour=2, minute=0),  # أول كل شهر الساعة 2 فجراً
        },
        'backup-contact-data': {
            'task': 'contact.tasks.backup_contact_data',
            'schedule': crontab(hour=1, minute=0),  # كل يوم الساعة 1 فجراً
        },
        'update-social-stats': {
            'task': 'contact.tasks.update_social_media_stats',
            'schedule': crontab(minute='*/30'),  # كل 30 دقيقة
        },
        'calculate-response-metrics': {
            'task': 'contact.tasks.calculate_response_time_metrics',
            'schedule': crontab(hour='*/6'),  # كل 6 ساعات
        },
        'health-check': {
            'task': 'contact.tasks.health_check',
            'schedule': crontab(minute='*/15'),  # كل 15 دقيقة
        },
    }
    """
    pass

# تسجيل تحميل المهام
logger.info(f"تم تحميل مهام تطبيق التواصل - Celery متوفر: {CELERY_AVAILABLE}")

# تصدير المهام للاستخدام الخارجي
__all__ = [
    'send_contact_notification',
    'send_contact_confirmation',
    'send_newsletter_confirmation',
    'send_newsletter_bulk',
    'cleanup_old_messages',
    'cleanup_unconfirmed_subscriptions',
    'optimize_database_tables',
    'generate_daily_report',
    'send_daily_report_email',
    'export_contact_data',
    'update_social_media_stats',
    'calculate_response_time_metrics',
    'send_weekly_newsletter',
    'backup_contact_data',
    'cleanup_old_backups',
    'clear_all_caches',
    'health_check',
]