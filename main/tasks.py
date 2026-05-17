# main/tasks.py
"""مهام مجدولة لتطبيق main
يمكن استخدامها مع Celery أو Django-cron أو أي نظام مهام آخر
"""

import logging
import os
from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone

from .models import SiteSettings, Statistic, Goal, BoardMember, HomeSlider
from .sitemaps import update_search_engines, validate_sitemap

logger = logging.getLogger('main.tasks')


class MaintenanceTasks:
    """مهام الصيانة الدورية"""

    @staticmethod
    def clear_expired_cache():
        """مسح الكاش المنتهي الصلاحية"""
        try:
            cache_keys = [
                'site_settings',
                'navigation_data',
                'footer_statistics',
                'main_statistics',
                'featured_goals',
                'board_members',
                'home_slider',

            ]
            cleared_count = 0
            for key in cache_keys:
                if cache.get(key):
                    cache.delete(key)
                    cleared_count += 1
            logger.info(f"تم مسح {cleared_count} عنصر من الكاش")
            return cleared_count
        except Exception as e:
            logger.error(f"خطأ في مسح الكاش: {e}")
            return 0

    @staticmethod
    def update_automatic_statistics():
        """تحديث الإحصائيات التلقائية"""
        try:
            updated_count = 0

            # تحديث عدد الأهداف
            goals_count = Goal.objects.filter(is_active=True).count()
            goals_stat = Statistic.objects.filter(auto_update_from='goals').first()
            if goals_stat and goals_stat.number != goals_count:
                goals_stat.number = goals_count
                goals_stat.save()
                updated_count += 1

            # تحديث عدد أعضاء مجلس الإدارة
            board_count = BoardMember.objects.filter(is_active=True).count()
            board_stat = Statistic.objects.filter(auto_update_from='board_members').first()
            if board_stat and board_stat.number != board_count:
                board_stat.number = board_count
                board_stat.save()
                updated_count += 1

            # تحديث عدد المشاريع والمستفيدين
            try:
                from projects.models import Project

                projects_count = Project.objects.filter(is_active=True).count()
                projects_stat = Statistic.objects.filter(auto_update_from='projects').first()
                if projects_stat and projects_stat.number != projects_count:
                    projects_stat.number = projects_count
                    projects_stat.save()
                    updated_count += 1

                total_beneficiaries = Project.objects.filter(
                    is_active=True
                ).aggregate(
                    total=Sum('beneficiaries_count')
                )['total'] or 0

                beneficiaries_stat = Statistic.objects.filter(auto_update_from='beneficiaries').first()
                if beneficiaries_stat and beneficiaries_stat.number != total_beneficiaries:
                    beneficiaries_stat.number = total_beneficiaries
                    beneficiaries_stat.save()
                    updated_count += 1

            except ImportError:
                logger.info("تطبيق المشاريع غير متاح لتحديث الإحصائيات")

            logger.info(f"تم تحديث {updated_count} إحصائية تلقائياً")
            return updated_count

        except Exception as e:
            logger.error(f"خطأ في تحديث الإحصائيات: {e}")
            return 0

    @staticmethod
    def backup_site_settings():
        """نسخ احتياطي من إعدادات الموقع"""
        try:
            settings_obj = SiteSettings.get_settings()
            backup_data = {
                'site_name_ar': settings_obj.site_name_ar,
                'site_name_en': settings_obj.site_name_en,
                'phone': settings_obj.phone,
                'email': settings_obj.email,
                'address_ar': settings_obj.address_ar,
                'about_summary_ar': settings_obj.about_summary_ar,
                'facebook_url': settings_obj.facebook_url,
                'twitter_url': settings_obj.twitter_url,
                'instagram_url': settings_obj.instagram_url,
                'backup_date': timezone.now().isoformat(),
            }
            cache.set('site_settings_backup', backup_data, 60 * 60 * 24 * 7)  # أسبوع
            logger.info("تم إنشاء نسخة احتياطية من إعدادات الموقع")
            return True
        except Exception as e:
            logger.error(f"خطأ في النسخ الاحتياطي: {e}")
            return False

    @staticmethod
    def cleanup_old_data():
        """تنظيف البيانات القديمة"""
        try:
            cleaned_count = 0
            old_slides = HomeSlider.objects.filter(
                is_active=False,
                updated_at__lt=timezone.now() - timedelta(days=30),
            )
            for slide in old_slides:
                if slide.image and hasattr(slide.image, 'delete'):
                    slide.image.delete()
                slide.delete()
                cleaned_count += 1
            logger.info(f"تم تنظيف {cleaned_count} عنصر من البيانات القديمة")
            return cleaned_count
        except Exception as e:
            logger.error(f"خطأ في تنظيف البيانات: {e}")
            return 0


class ReportingTasks:
    """مهام التقارير"""

    @staticmethod
    def generate_daily_report():
        """تقرير يومي للإحصائيات"""
        try:
            today = timezone.now().date()

            total_goals = Goal.objects.filter(is_active=True).count()
            total_board_members = BoardMember.objects.filter(is_active=True).count()

            active_slides = HomeSlider.objects.filter(is_active=True).count()

            try:
                from projects.models import Project
                total_projects = Project.objects.filter(is_active=True).count()
            except ImportError:
                total_projects = 0

            report = f"""تقرير يومي - {today}
========================
الإحصائيات العامة:
- عدد الأهداف النشطة: {total_goals}
- أعضاء مجلس الإدارة: {total_board_members}
- المشاريع النشطة: {total_projects}

- شرائح السلايدر النشطة: {active_slides}

تم إنشاء هذا التقرير تلقائياً.
"""
            cache.set(f'daily_report_{today}', report, 60 * 60 * 24)
            logger.info(f"تم إنشاء التقرير اليومي لـ {today}")
            return report
        except Exception as e:
            logger.error(f"خطأ في إنشاء التقرير اليومي: {e}")
            return None

    @staticmethod
    def generate_weekly_report():
        """تقرير أسبوعي مفصل"""
        try:
            today = timezone.now().date()
            week_start = today - timedelta(days=7)

            new_goals = Goal.objects.filter(created_at__date__gte=week_start, is_active=True).count()
            new_board_members = BoardMember.objects.filter(created_at__date__gte=week_start, is_active=True).count()

            settings_updates = SiteSettings.objects.filter(updated_at__date__gte=week_start).count()

            report = f"""تقرير أسبوعي - {week_start} إلى {today}
==========================================
النشاطات الجديدة:
- أهداف جديدة: {new_goals}
- أعضاء مجلس إدارة جدد: {new_board_members}

- تحديثات الإعدادات: {settings_updates}

الحالة العامة:
- إجمالي الأهداف النشطة: {Goal.objects.filter(is_active=True).count()}
- إجمالي أعضاء المجلس: {BoardMember.objects.filter(is_active=True).count()}


تم إنشاء هذا التقرير تلقائياً.
"""
            if not settings.DEBUG and hasattr(settings, 'ADMIN_EMAIL'):
                try:
                    send_mail(
                        subject='التقرير الأسبوعي - جمعية نسائم فلسطين',
                        message=report,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[settings.ADMIN_EMAIL],
                        fail_silently=True,
                    )
                except Exception as mail_error:
                    logger.error(f"فشل في إرسال التقرير الأسبوعي: {mail_error}")

            cache.set(f'weekly_report_{today}', report, 60 * 60 * 24 * 7)
            logger.info("تم إنشاء التقرير الأسبوعي")
            return report
        except Exception as e:
            logger.error(f"خطأ في إنشاء التقرير الأسبوعي: {e}")
            return None


class SEOTasks:
    """مهام تحسين محركات البحث"""

    @staticmethod
    def update_sitemap():
        """تحديث خريطة الموقع وإشعار محركات البحث"""
        try:
            errors = validate_sitemap()
            if errors:
                logger.warning(f"أخطاء في خريطة الموقع: {errors}")

            cache.delete('sitemap_urls')
            cache.delete('sitemap_lastmod')

            if not settings.DEBUG:
                update_search_engines()
                logger.info("تم إشعار محركات البحث بتحديث خريطة الموقع")

            logger.info("تم تحديث خريطة الموقع")
            return True
        except Exception as e:
            logger.error(f"خطأ في تحديث خريطة الموقع: {e}")
            return False

    @staticmethod
    def check_broken_links():
        """فحص الروابط المعطلة"""
        import requests

        try:
            broken_links = []
            settings_obj = SiteSettings.get_settings()
            external_links = [
                ('فيسبوك', settings_obj.facebook_url),
                ('تويتر', settings_obj.twitter_url),
                ('انستغرام', settings_obj.instagram_url),
                ('تيك توك', settings_obj.tiktok_url),
                ('يوتيوب', settings_obj.youtube_url),
            ]

            for name, url in external_links:
                if url:
                    try:
                        response = requests.head(url, timeout=10, allow_redirects=True)
                        if response.status_code >= 400:
                            broken_links.append(f'{name}: {url} (Status: {response.status_code})')
                    except requests.RequestException:
                        broken_links.append(f'{name}: {url} (غير قابل للوصول)')

            if broken_links:
                logger.warning(f"تم العثور على روابط معطلة: {broken_links}")
                if not settings.DEBUG and hasattr(settings, 'ADMIN_EMAIL'):
                    try:
                        send_mail(
                            subject='تقرير الروابط المعطلة - جمعية نسائم فلسطين',
                            message='تم العثور على الروابط المعطلة التالية:\n\n' + '\n'.join(broken_links),
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[settings.ADMIN_EMAIL],
                            fail_silently=True,
                        )
                    except Exception as mail_error:
                        logger.error(f"فشل في إرسال تقرير الروابط المعطلة: {mail_error}")
            else:
                logger.info("جميع الروابط الخارجية تعمل بشكل صحيح")

            return broken_links
        except Exception as e:
            logger.error(f"خطأ في فحص الروابط المعطلة: {e}")
            return []


class SecurityTasks:
    """مهام الأمان"""

    @staticmethod
    def check_admin_activity():
        """مراقبة نشاط المدير"""
        try:
            from django.contrib.admin.models import LogEntry
            from django.contrib.auth import get_user_model
            User = get_user_model()

            today = timezone.now().date()
            recent_admin_activity = LogEntry.objects.filter(
                action_time__date=today,
                user__is_superuser=True
            ).count()
            active_admins = User.objects.filter(
                is_superuser=True,
                is_active=True,
                last_login__date__gte=today - timedelta(days=7)
            ).count()

            logger.info(f"نشاط المدير اليوم: {recent_admin_activity} عملية")
            logger.info(f"المدراء النشطين هذا الأسبوع: {active_admins}")
            return {'daily_activity': recent_admin_activity, 'active_admins': active_admins}
        except Exception as e:
            logger.error(f"خطأ في مراقبة نشاط المدير: {e}")
            return None

    @staticmethod
    def backup_database():
        """نسخة احتياطية من قاعدة البيانات"""
        try:
            backup_filename = f"backup_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_path = os.path.join(settings.BASE_DIR, 'backups', backup_filename)

            os.makedirs(os.path.dirname(backup_path), exist_ok=True)

            with open(backup_path, 'w') as backup_file:
                call_command('dumpdata', 'main', stdout=backup_file, indent=2)

            logger.info(f"تم إنشاء نسخة احتياطية: {backup_path}")

            backup_dir = os.path.dirname(backup_path)
            cutoff_date = timezone.now() - timedelta(days=30)
            for filename in os.listdir(backup_dir):
                if filename.startswith('backup_') and filename.endswith('.json'):
                    file_path = os.path.join(backup_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    if file_time < cutoff_date:
                        os.remove(file_path)
                        logger.info(f"تم حذف النسخة القديمة: {filename}")

            return backup_path
        except Exception as e:
            logger.error(f"خطأ في إنشاء النسخة الاحتياطية: {e}")
            return None


# Command Classes for Django Management
class Command(BaseCommand):
    """قيادة Django للمهام الدورية"""

    help = 'تنفيذ مهام الصيانة الدورية'

    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            type=str,
            help='نوع المهمة المطلوب تنفيذها',
            choices=[
                'cache', 'stats', 'backup', 'cleanup',
                'daily_report', 'weekly_report', 'sitemap',
                'check_links', 'admin_activity', 'db_backup'
            ]
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='تنفيذ جميع مهام الصيانة'
        )

    def handle(self, *args, **options):
        task = options.get('task')
        run_all = options.get('all')

        self.stdout.write(self.style.SUCCESS('بدء تنفيذ مهام الصيانة...'))

        if run_all or task == 'cache':
            cleared = MaintenanceTasks.clear_expired_cache()
            self.stdout.write(f'تم مسح {cleared} عنصر من الكاش')

        if run_all or task == 'stats':
            updated = MaintenanceTasks.update_automatic_statistics()
            self.stdout.write(f'تم تحديث {updated} إحصائية')

        if run_all or task == 'backup':
            success = MaintenanceTasks.backup_site_settings()
            if success:
                self.stdout.write('تم إنشاء نسخة احتياطية من الإعدادات')

        if run_all or task == 'cleanup':
            cleaned = MaintenanceTasks.cleanup_old_data()
            self.stdout.write(f'تم تنظيف {cleaned} عنصر من البيانات القديمة')

        if run_all or task == 'daily_report':
            report = ReportingTasks.generate_daily_report()
            if report:
                self.stdout.write('تم إنشاء التقرير اليومي')

        if run_all or task == 'weekly_report':
            report = ReportingTasks.generate_weekly_report()
            if report:
                self.stdout.write('تم إنشاء التقرير الأسبوعي')

        if run_all or task == 'sitemap':
            success = SEOTasks.update_sitemap()
            if success:
                self.stdout.write('تم تحديث خريطة الموقع')

        if run_all or task == 'check_links':
            broken_links = SEOTasks.check_broken_links()
            if broken_links:
                self.stdout.write(self.style.WARNING(f'تم العثور على {len(broken_links)} رابط معطل'))
            else:
                self.stdout.write('جميع الروابط تعمل بشكل صحيح')

        if run_all or task == 'admin_activity':
            activity = SecurityTasks.check_admin_activity()
            if activity:
                self.stdout.write(f'نشاط المدير: {activity}')

        if run_all or task == 'db_backup':
            backup_path = SecurityTasks.backup_database()
            if backup_path:
                self.stdout.write(f'تم إنشاء نسخة احتياطية: {backup_path}')

        self.stdout.write(self.style.SUCCESS('تم انتهاء جميع مهام الصيانة'))


# دوال للاستخدام مع Celery
def daily_maintenance():
    """مهام الصيانة اليومية"""
    MaintenanceTasks.clear_expired_cache()
    MaintenanceTasks.update_automatic_statistics()
    ReportingTasks.generate_daily_report()
    SEOTasks.check_broken_links()
    SecurityTasks.check_admin_activity()


def weekly_maintenance():
    """مهام الصيانة الأسبوعية"""
    MaintenanceTasks.backup_site_settings()
    MaintenanceTasks.cleanup_old_data()
    ReportingTasks.generate_weekly_report()
    SEOTasks.update_sitemap()
    SecurityTasks.backup_database()


# جدولة المهام (للاستخدام مع django-cron)
class DailyMaintenanceCronJob:
    """مهمة يومية مجدولة"""
    RUN_AT_TIMES = ['02:00']

    def do(self):
        daily_maintenance()


class WeeklyMaintenanceCronJob:
    """مهمة أسبوعية مجدولة"""
    RUN_ON_DAYS = ['0']  # يوم الأحد
    RUN_AT_TIMES = ['03:00']

    def do(self):
        weekly_maintenance()


# دالة تهيئة المهام
def setup_scheduled_tasks():
    """إعداد المهام المجدولة"""
    logger.info("تم إعداد المهام المجدولة لتطبيق main")
    return True


if __name__ == '__main__':
    print("تنفيذ مهام الصيانة...")
    daily_maintenance()
    print("انتهى تنفيذ المهام")
