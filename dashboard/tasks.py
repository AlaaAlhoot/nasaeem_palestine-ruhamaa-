import os

from celery import shared_task
from django.db.models import Count
from django.utils import timezone
from django.core.mail import send_mail, mail_admins
from django.conf import settings
from django.contrib.auth.models import User
from datetime import timedelta, datetime
import logging

from .models import ActivityLog, SystemHealth, SiteSetting
from .utils import get_system_health_data, backup_database, clean_old_logs, get_dashboard_statistics
from contact.models import ContactMessage, Newsletter

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def system_health_check(self):
    """فحص دوري لصحة النظام"""
    try:
        health_data = get_system_health_data()

        # إرسال تنبيهات في حالة المشاكل
        if health_data['status'] in ['warning', 'critical']:
            send_system_alert.delay(health_data)

        # إرسال إشارة مخصصة في حالة الحالة الحرجة
        if health_data['status'] == 'critical':
            from .signals import system_health_critical
            system_health_critical.send(
                sender=self.__class__,
                health_data=health_data
            )

        return {'status': 'success', 'health_status': health_data['status']}

    except Exception as exc:
        logger.error(f'خطأ في فحص صحة النظام: {exc}')
        raise self.retry(exc=exc, countdown=300)  # إعادة المحاولة بعد 5 دقائق


@shared_task
def send_system_alert(health_data):
    """إرسال تنبيهات صحة النظام"""
    try:
        settings_obj = SiteSetting.get_settings()
        if not settings_obj.admin_email_alerts:
            return {'status': 'disabled'}

        status_labels = {
            'warning': 'تحذير',
            'critical': 'حرج',
            'down': 'متوقف'
        }

        subject = f"تنبيه نظام: {status_labels.get(health_data['status'], health_data['status'])}"

        message = f"""
تم اكتشاف مشكلة في صحة النظام:

الحالة: {status_labels.get(health_data['status'], health_data['status'])}
استخدام المعالج: {health_data.get('cpu_percent', 0):.1f}%
استخدام الذاكرة: {health_data.get('memory_percent', 0):.1f}%
استخدام القرص: {health_data.get('disk_percent', 0):.1f}%
المستخدمون النشطون: {health_data.get('active_users', 0)}

الوقت: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

يرجى مراجعة النظام في أقرب وقت ممكن.
        """

        mail_admins(subject, message)
        return {'status': 'sent'}

    except Exception as e:
        logger.error(f'خطأ في إرسال التنبيه: {e}')
        return {'status': 'failed', 'error': str(e)}


@shared_task
def generate_daily_report():
    """توليد التقرير اليومي"""
    try:
        settings_obj = SiteSetting.get_settings()
        if not settings_obj.daily_report_enabled:
            return {'status': 'disabled'}

        yesterday = timezone.now() - timedelta(days=1)
        yesterday_date = yesterday.date()

        # جمع البيانات
        stats = get_dashboard_statistics()
        new_messages = ContactMessage.objects.filter(created_at__date=yesterday_date).count()
        new_users = User.objects.filter(date_joined__date=yesterday_date).count()
        activities = ActivityLog.objects.filter(timestamp__date=yesterday_date).count()

        # إحصائيات إضافية
        login_activities = ActivityLog.objects.filter(
            action='login',
            timestamp__date=yesterday_date
        ).count()

        # المشاريع الجديدة (إذا كان النموذج متاحاً)
        try:
            from projects.models import Project
            new_projects = Project.objects.filter(created_at__date=yesterday_date).count()
        except ImportError:
            new_projects = 0

        # أهم الأنشطة
        top_activities = ActivityLog.objects.filter(
            timestamp__date=yesterday_date
        ).values('action').annotate(
            count=Count('action')
        ).order_by('-count')[:5]

        # إنشاء التقرير
        report = f"""
التقرير اليومي - {yesterday_date.strftime('%Y-%m-%d')}

إحصائيات اليوم:
===============
- رسائل جديدة: {new_messages}
- مستخدمين جدد: {new_users}
- مشاريع جديدة: {new_projects}
- تسجيلات دخول: {login_activities}
- إجمالي الأنشطة: {activities}

أهم الأنشطة:
===========
"""
        for activity in top_activities:
            report += f"• {activity['action']}: {activity['count']} مرة\n"

        report += f"""

الحالة العامة:
============
- إجمالي المستخدمين: {stats.get('users', {}).get('total', 0)}
- المشاريع النشطة: {stats.get('projects', {}).get('active', 0)}
- الرسائل غير المقروءة: {stats.get('messages', {}).get('new', 0)}

تاريخ التقرير: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
        """

        # إرسال للإداريين
        mail_admins(
            f'التقرير اليومي - {yesterday_date.strftime("%Y-%m-%d")}',
            report
        )

        # تسجيل النشاط
        ActivityLog.objects.create(
            user=None,
            username='System',
            action='export',
            title='إنشاء التقرير اليومي',
            description=f'تم إنشاء التقرير اليومي ليوم {yesterday_date}',
            level='success',
            timestamp=timezone.now(),
            user_agent='',
            ip_address='',
            session_key='',
            extra_data={'report_date': yesterday_date.isoformat()}
        )

        return {'status': 'generated', 'date': yesterday_date.isoformat()}

    except Exception as e:
        logger.error(f'خطأ في توليد التقرير اليومي: {e}')
        return {'status': 'error', 'error': str(e)}


@shared_task
def auto_backup_system():
    """النسخ الاحتياطي التلقائي"""
    try:
        settings_obj = SiteSetting.get_settings()
        if not settings_obj.auto_backup_enabled:
            return {'status': 'disabled'}

        # إنشاء النسخة الاحتياطية
        backup_result = backup_database()

        if backup_result['success']:
            # تسجيل النشاط
            ActivityLog.objects.create(
                user=None,
                username='System',
                action='backup',
                title='نسخ احتياطي تلقائي',
                description=f'تم إنشاء نسخة احتياطية: {backup_result["filename"]}',
                level='success',
                timestamp=timezone.now(),
                user_agent='',
                ip_address='',
                session_key='',
                extra_data={
                    'filename': backup_result['filename'],
                    'backup_size': os.path.getsize(backup_result['path']) if os.path.exists(
                        backup_result['path']) else 0
                }
            )

            # إرسال إشارة اكتمال النسخ الاحتياطي
            from .signals import backup_completed
            backup_completed.send(
                sender=auto_backup_system,
                backup_info=backup_result
            )

            # تنظيف النسخ القديمة
            cleanup_old_backups.delay(settings_obj.keep_backups_count)

            return {'status': 'completed', 'filename': backup_result['filename']}
        else:
            logger.error(f'فشل النسخ الاحتياطي: {backup_result["error"]}')

            # إرسال تنبيه فشل النسخ الاحتياطي
            mail_admins(
                'فشل النسخ الاحتياطي التلقائي',
                f'فشل في إنشاء النسخة الاحتياطية: {backup_result["error"]}'
            )

            return {'status': 'failed', 'error': backup_result['error']}

    except Exception as e:
        logger.error(f'خطأ في النسخ الاحتياطي التلقائي: {e}')
        return {'status': 'error', 'error': str(e)}


@shared_task
def cleanup_old_backups(keep_count=30):
    """تنظيف النسخ الاحتياطية القديمة"""
    try:
        import os
        import glob

        backups_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        if not os.path.exists(backups_dir):
            return {'status': 'no_backups_dir'}

        # الحصول على جميع ملفات النسخ الاحتياطي
        backup_files = glob.glob(os.path.join(backups_dir, 'backup_*.sql'))
        backup_files.sort(key=os.path.getmtime, reverse=True)  # ترتيب حسب التاريخ

        # حذف الملفات الزائدة
        deleted_files = []
        if len(backup_files) > keep_count:
            files_to_delete = backup_files[keep_count:]
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    deleted_files.append(os.path.basename(file_path))
                except OSError as e:
                    logger.error(f'فشل في حذف الملف {file_path}: {e}')

        return {
            'status': 'completed',
            'total_backups': len(backup_files),
            'deleted_count': len(deleted_files),
            'deleted_files': deleted_files
        }

    except Exception as e:
        logger.error(f'خطأ في تنظيف النسخ الاحتياطية: {e}')
        return {'status': 'error', 'error': str(e)}


@shared_task
def cleanup_old_data():
    """تنظيف البيانات القديمة"""
    try:
        settings_obj = SiteSetting.get_settings()

        # تنظيف السجلات القديمة (أكثر من 90 يوم)
        logs_result = clean_old_logs(90)

        # تنظيف فحوصات صحة النظام القديمة (أكثر من 30 يوم)
        old_health_checks = SystemHealth.objects.filter(
            checked_at__lt=timezone.now() - timedelta(days=30)
        )
        health_deleted = old_health_checks.count()
        old_health_checks.delete()

        # تنظيف الجلسات المنتهية الصلاحية (Django sessions)
        try:
            from django.contrib.sessions.models import Session
            expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
            sessions_deleted = expired_sessions.count()
            expired_sessions.delete()
        except ImportError:
            sessions_deleted = 0

        # تسجيل النشاط
        ActivityLog.objects.create(
            user=None,
            username='System',
            action='maintenance',
            title='تنظيف البيانات القديمة',
            description=f'تم حذف {logs_result.get("deleted_count", 0)} سجل قديم و {health_deleted} فحص صحة',
            level='info',
            timestamp=timezone.now(),
            user_agent='',
            ip_address='',
            session_key='',
            extra_data={
                'logs_deleted': logs_result.get('deleted_count', 0),
                'health_checks_deleted': health_deleted,
                'sessions_deleted': sessions_deleted
            }
        )

        return {
            'status': 'completed',
            'logs_deleted': logs_result.get('deleted_count', 0),
            'health_checks_deleted': health_deleted,
            'sessions_deleted': sessions_deleted
        }

    except Exception as e:
        logger.error(f'خطأ في تنظيف البيانات: {e}')
        return {'status': 'error', 'error': str(e)}


@shared_task
def send_weekly_newsletter():
    """إرسال النشرة الأسبوعية"""
    try:
        settings_obj = SiteSetting.get_settings()
        if not settings_obj.weekly_report_enabled:
            return {'status': 'disabled'}

        # الحصول على المشتركين النشطين
        subscribers = Newsletter.objects.filter(
            is_active=True,
            confirmed_at__isnull=False
        )

        if not subscribers.exists():
            return {'status': 'no_subscribers'}

        # إحصائيات الأسبوع الماضي
        week_ago = timezone.now() - timedelta(days=7)

        # جمع البيانات
        try:
            from projects.models import Project
            new_projects = Project.objects.filter(created_at__gte=week_ago).count()
            featured_projects = Project.objects.filter(
                is_featured=True,
                is_active=True
            )[:3]
        except ImportError:
            new_projects = 0
            featured_projects = []

        new_messages = ContactMessage.objects.filter(created_at__gte=week_ago).count()

        # محتوى النشرة
        subject = f'النشرة الأسبوعية - {timezone.now().strftime("%Y-%m-%d")}'
        message = f"""
أحدث الأخبار والمشاريع من جمعية نسائم فلسطين الخيرية

إحصائيات هذا الأسبوع:
====================
- مشاريع جديدة: {new_projects}
- رسائل تواصل: {new_messages}

المشاريع المميزة:
===============
"""

        for project in featured_projects:
            message += f"• {project.title_ar}\n"

        message += f"""

نشكركم لاشتراككم في نشرتنا الأسبوعية.

للإلغاء الاشتراك، يرجى زيارة موقعنا.
        """

        sent_count = 0
        failed_count = 0

        for subscriber in subscribers:
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [subscriber.email],
                    fail_silently=False
                )
                sent_count += 1
            except Exception as e:
                logger.error(f'فشل إرسال النشرة إلى {subscriber.email}: {e}')
                failed_count += 1

        # تسجيل النشاط
        ActivityLog.objects.create(
            user=None,
            username='System',
            action='export',
            title='إرسال النشرة الأسبوعية',
            description=f'تم إرسال النشرة إلى {sent_count} مشترك، فشل في {failed_count}',
            level='success' if failed_count == 0 else 'warning',
            timestamp=timezone.now(),
            user_agent='',
            ip_address='',
            session_key='',
            extra_data={
                'sent_count': sent_count,
                'failed_count': failed_count,
                'total_subscribers': subscribers.count()
            }
        )

        return {
            'status': 'completed',
            'sent_count': sent_count,
            'failed_count': failed_count
        }

    except Exception as e:
        logger.error(f'خطأ في إرسال النشرة الأسبوعية: {e}')
        return {'status': 'error', 'error': str(e)}


@shared_task
def update_project_statistics():
    """تحديث إحصائيات المشاريع"""
    try:
        from projects.models import Project
        from main.models import Statistic

        # تحديث عدد المشاريع في الإحصائيات
        projects_count = Project.objects.filter(is_active=True).count()
        completed_projects = Project.objects.filter(status='completed').count()

        # تحديث الإحصائيات التلقائية
        updated_stats = []
        for stat in Statistic.objects.filter(auto_update_from__isnull=False):
            old_value = stat.number

            if stat.auto_update_from == 'projects':
                stat.number = projects_count
            elif stat.auto_update_from == 'completed_projects':
                stat.number = completed_projects
            elif stat.auto_update_from == 'users':
                stat.number = User.objects.filter(is_active=True).count()
            elif stat.auto_update_from == 'messages':
                stat.number = ContactMessage.objects.count()

            if stat.number != old_value:
                stat.save(update_fields=['number'])
                updated_stats.append({
                    'title': stat.title_ar,
                    'old_value': old_value,
                    'new_value': stat.number
                })

        return {
            'status': 'updated',
            'projects_count': projects_count,
            'completed_projects': completed_projects,
            'updated_stats': updated_stats
        }

    except ImportError:
        return {'status': 'no_projects_model'}
    except Exception as e:
        logger.error(f'خطأ في تحديث إحصائيات المشاريع: {e}')
        return {'status': 'error', 'error': str(e)}


@shared_task(bind=True, max_retries=3)
def send_notification_email(self, user_id, subject, message):
    """إرسال إشعار بالبريد الإلكتروني"""
    try:
        user = User.objects.get(id=user_id)

        # فحص تفضيلات المستخدم
        if hasattr(user, 'profile') and not user.profile.email_notifications:
            return {'status': 'skipped', 'reason': 'user_preference'}

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False
        )

        return {'status': 'sent', 'recipient': user.email}

    except User.DoesNotExist:
        logger.error(f'المستخدم غير موجود: {user_id}')
        return {'status': 'error', 'reason': 'user_not_found'}
    except Exception as exc:
        logger.error(f'خطأ في إرسال الإشعار: {exc}')
        raise self.retry(exc=exc, countdown=60)


@shared_task
def clear_cache():
    """تنظيف الكاش"""
    try:
        from django.core.cache import cache
        cache.clear()

        ActivityLog.objects.create(
            user=None,
            username='System',
            action='maintenance',
            title='تنظيف الكاش',
            description='تم تنظيف جميع بيانات الكاش',
            level='info',
            timestamp=timezone.now(),
            user_agent='',
            ip_address='',
            session_key='',
            extra_data={}
        )

        return {'status': 'cleared'}

    except Exception as e:
        logger.error(f'خطأ في تنظيف الكاش: {e}')
        return {'status': 'error', 'error': str(e)}


@shared_task
def monitor_failed_logins():
    """مراقبة محاولات الدخول الفاشلة"""
    try:
        # فحص محاولات الدخول الفاشلة في آخر ساعة
        failed_attempts = ActivityLog.objects.filter(
            action='login_failed',
            timestamp__gte=timezone.now() - timedelta(hours=1)
        ).count()

        # فحص المحاولات من نفس IP
        suspicious_ips = ActivityLog.objects.filter(
            action='login_failed',
            timestamp__gte=timezone.now() - timedelta(hours=1)
        ).values('ip_address').annotate(
            count=Count('ip_address')
        ).filter(count__gte=5)

        alerts_sent = 0
        if failed_attempts > 10:  # أكثر من 10 محاولات فاشلة
            mail_admins(
                'تحذير: محاولات دخول فاشلة متكررة',
                f'تم رصد {failed_attempts} محاولة دخول فاشلة في الساعة الماضية'
            )
            alerts_sent += 1

        if suspicious_ips.exists():
            suspicious_list = list(suspicious_ips)
            mail_admins(
                'تحذير: عناوين IP مشبوهة',
                f'عناوين IP مع محاولات دخول متكررة: {suspicious_list}'
            )
            alerts_sent += 1

        return {
            'status': 'checked',
            'failed_attempts': failed_attempts,
            'suspicious_ips_count': suspicious_ips.count(),
            'alerts_sent': alerts_sent
        }

    except Exception as e:
        logger.error(f'خطأ في مراقبة محاولات الدخول: {e}')
        return {'status': 'error', 'error': str(e)}


@shared_task
def optimize_database():
    """تحسين قاعدة البيانات"""
    try:
        from django.db import connection

        with connection.cursor() as cursor:
            # تحليل الجداول (PostgreSQL)
            if 'postgresql' in settings.DATABASES['default']['ENGINE']:
                cursor.execute("ANALYZE;")
                cursor.execute("VACUUM;")

            # أو تحسين SQLite
            elif 'sqlite' in settings.DATABASES['default']['ENGINE']:
                cursor.execute("VACUUM;")
                cursor.execute("REINDEX;")

        ActivityLog.objects.create(
            user=None,
            username='System',
            action='maintenance',
            title='تحسين قاعدة البيانات',
            description='تم تشغيل عملية تحسين قاعدة البيانات',
            level='info',
            timestamp=timezone.now(),
            user_agent='',
            ip_address='',
            session_key='',
            extra_data={}
        )

        return {'status': 'optimized'}

    except Exception as e:
        logger.error(f'خطأ في تحسين قاعدة البيانات: {e}')
        return {'status': 'error', 'error': str(e)}