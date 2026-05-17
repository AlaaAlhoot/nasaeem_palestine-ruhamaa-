from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from django.core.mail import send_mail
from django.conf import settings
import logging
from datetime import timedelta

from .models import Project, ProjectCategory, ProjectLike, ProjectImage

logger = logging.getLogger('projects.tasks')


class ProjectMaintenanceTasks:
    """مهام صيانة المشاريع"""

    @staticmethod
    def update_project_statistics():
        """تحديث إحصائيات المشاريع"""
        try:
            projects = Project.objects.filter(is_active=True)

            # تحديث عدد المشاهدات والإعجابات
            for project in projects:
                likes_count = project.project_likes.count()
                if project.likes_count != likes_count:
                    project.likes_count = likes_count
                    project.save(update_fields=['likes_count'])

            # تحديث إحصائيات main app
            try:
                from main.models import Statistic, SiteSettings

                total_projects = projects.count()
                total_beneficiaries = projects.aggregate(Sum('beneficiaries_count'))['beneficiaries_count__sum'] or 0

                # تحديث الإحصائيات
                projects_stat = Statistic.objects.filter(auto_update_from='projects').first()
                if projects_stat:
                    projects_stat.number = total_projects
                    projects_stat.save()

                beneficiaries_stat = Statistic.objects.filter(auto_update_from='beneficiaries').first()
                if beneficiaries_stat:
                    beneficiaries_stat.number = total_beneficiaries
                    beneficiaries_stat.save()

                logger.info(f"تم تحديث إحصائيات المشاريع: {total_projects} مشروع، {total_beneficiaries} مستفيد")

            except ImportError:
                pass

            return total_projects

        except Exception as e:
            logger.error(f"خطأ في تحديث إحصائيات المشاريع: {e}")
            return 0

    @staticmethod
    def cleanup_unused_images():
        """تنظيف الصور غير المستخدمة"""
        try:
            cleaned_count = 0

            # حذف الصور غير النشطة والقديمة
            old_images = ProjectImage.objects.filter(
                is_active=False,
                created_at__lt=timezone.now() - timedelta(days=30)
            )

            for image in old_images:
                if image.image:
                    image.image.delete()
                image.delete()
                cleaned_count += 1

            logger.info(f"تم حذف {cleaned_count} صورة غير مستخدمة")
            return cleaned_count

        except Exception as e:
            logger.error(f"خطأ في تنظيف الصور: {e}")
            return 0

    @staticmethod
    def clear_expired_cache():
        """مسح الكاش المنتهي الصلاحية"""
        try:
            cache_keys = [
                'featured_projects', 'recent_projects_6', 'popular_projects_6',
                'project_statistics', 'project_categories'
            ]

            cleared_count = 0
            for key in cache_keys:
                if cache.get(key):
                    cache.delete(key)
                    cleared_count += 1

            logger.info(f"تم مسح {cleared_count} عنصر من كاش المشاريع")
            return cleared_count

        except Exception as e:
            logger.error(f"خطأ في مسح الكاش: {e}")
            return 0

    @staticmethod
    def update_project_progress():
        """تحديث تقدم المشاريع"""
        try:
            updated_count = 0
            projects = Project.objects.filter(is_active=True, status__in=['active', 'planning'])

            for project in projects:
                # تحديث الحالة حسب التقدم
                progress = project.get_progress_percentage()

                if progress >= 100 and project.status != 'completed':
                    project.status = 'completed'
                    project.save(update_fields=['status'])
                    updated_count += 1
                    logger.info(f"تم تحديث حالة المشروع {project.title_ar} إلى مكتمل")

            return updated_count

        except Exception as e:
            logger.error(f"خطأ في تحديث تقدم المشاريع: {e}")
            return 0


class ProjectReportTasks:
    """مهام تقارير المشاريع"""

    @staticmethod
    def generate_projects_report():
        """تقرير المشاريع"""
        try:
            today    = timezone.now().date()
            week_ago = today - timedelta(days=7)

            # ── query واحدة بدل 6 ──
            qs = Project.objects.filter(is_active=True)
            stats = qs.aggregate(
                total=Count('id'),
                completed=Count('id', filter=Q(status='completed')),
                active=Count('id',    filter=Q(status='active')),
                new_week=Count('id',  filter=Q(created_at__date__gte=week_ago)),
                total_target=Sum('target_amount'),
                total_raised=Sum('raised_amount'),
            )

            total_projects        = stats['total']
            completed_projects    = stats['completed']
            active_projects       = stats['active']
            new_projects_this_week = stats['new_week']
            total_target          = stats['total_target'] or 0
            total_raised          = stats['total_raised'] or 0

            top_viewed = qs.only('title_ar', 'views_count').order_by('-views_count')[:5]

            collection_rate = (total_raised / total_target * 100) if total_target > 0 else 0

            report = f"""
تقرير المشاريع - {today}
========================

الإحصائيات العامة:
- إجمالي المشاريع: {total_projects}
- المشاريع المكتملة: {completed_projects}
- المشاريع النشطة: {active_projects}
- مشاريع جديدة هذا الأسبوع: {new_projects_this_week}

المعلومات المالية:
- إجمالي المبلغ المستهدف: {total_target:,.2f}
- إجمالي المبلغ المجمع: {total_raised:,.2f}
- نسبة التحصيل: {collection_rate:.1f}%

أكثر المشاريع مشاهدة:
"""
            for i, project in enumerate(top_viewed, 1):
                report += f"{i}. {project.title_ar} - {project.views_count} مشاهدة\n"

            cache.set(f'projects_report_{today}', report, 60 * 60 * 24)
            logger.info(f"تم إنشاء تقرير المشاريع لـ {today}")
            return report

        except Exception as e:
            logger.error(f"خطأ في إنشاء تقرير المشاريع: {e}")
            return None

    @staticmethod
    def send_weekly_report():
        """إرسال التقرير الأسبوعي"""
        if settings.DEBUG or not hasattr(settings, 'ADMIN_EMAIL'):
            return

        try:
            report = ProjectReportTasks.generate_projects_report()
            if report:
                send_mail(
                    subject='التقرير الأسبوعي للمشاريع - جمعية نسائم فلسطين',
                    message=report,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.ADMIN_EMAIL],
                    fail_silently=True,
                )
                logger.info("تم إرسال التقرير الأسبوعي للمشاريع")

        except Exception as e:
            logger.error(f"فشل في إرسال التقرير الأسبوعي: {e}")


# Django Management Command
class Command(BaseCommand):
    """قيادة Django لمهام المشاريع"""

    help = 'تنفيذ مهام صيانة المشاريع'

    def add_arguments(self, parser):
        parser.add_argument('--task', type=str, choices=[
            'stats', 'cleanup', 'cache', 'progress', 'report', 'all'
        ])

    def handle(self, *args, **options):
        task = options.get('task')

        self.stdout.write(self.style.SUCCESS('بدء تنفيذ مهام المشاريع...'))

        if task == 'stats' or task == 'all':
            count = ProjectMaintenanceTasks.update_project_statistics()
            self.stdout.write(f'تم تحديث إحصائيات {count} مشروع')

        if task == 'cleanup' or task == 'all':
            count = ProjectMaintenanceTasks.cleanup_unused_images()
            self.stdout.write(f'تم تنظيف {count} صورة')

        if task == 'cache' or task == 'all':
            count = ProjectMaintenanceTasks.clear_expired_cache()
            self.stdout.write(f'تم مسح {count} عنصر كاش')

        if task == 'progress' or task == 'all':
            count = ProjectMaintenanceTasks.update_project_progress()
            self.stdout.write(f'تم تحديث {count} مشروع')

        if task == 'report' or task == 'all':
            report = ProjectReportTasks.generate_projects_report()
            if report:
                self.stdout.write('تم إنشاء تقرير المشاريع')

        self.stdout.write(self.style.SUCCESS('انتهت مهام المشاريع'))


# دوال للاستخدام مع Celery
def daily_projects_maintenance():
    """مهام يومية للمشاريع"""
    ProjectMaintenanceTasks.update_project_statistics()
    ProjectMaintenanceTasks.clear_expired_cache()
    ProjectMaintenanceTasks.update_project_progress()


def weekly_projects_maintenance():
    """مهام أسبوعية للمشاريع"""
    ProjectMaintenanceTasks.cleanup_unused_images()
    ProjectReportTasks.send_weekly_report()