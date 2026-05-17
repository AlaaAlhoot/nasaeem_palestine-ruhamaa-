from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth.signals import user_logged_in
import logging
from django.db.models import Sum
from contact import models
from projects import models
from  main import  models
from .models import Project, ProjectCategory, ProjectImage, ProjectLike

logger = logging.getLogger('projects')


# إشارات تحديث الكاش
@receiver([post_save, post_delete], sender=Project)
def clear_projects_cache(sender, **kwargs):
    """مسح كاش المشاريع عند التحديث"""
    cache_keys = [
        'featured_projects', 'recent_projects_6', 'popular_projects_6',
        'project_statistics', 'navigation_data', 'site_settings'
    ]
    for key in cache_keys:
        cache.delete(key)
    logger.info("تم مسح كاش المشاريع")


@receiver([post_save, post_delete], sender=ProjectCategory)
def clear_categories_cache(sender, **kwargs):
    """مسح كاش الفئات"""
    cache.delete('navigation_data')
    cache.delete('project_categories')
    logger.info("تم مسح كاش فئات المشاريع")


# تحديث الإحصائيات التلقائية
@receiver(post_save, sender=Project)
def update_project_statistics(sender, instance, created, **kwargs):
    """تحديث الإحصائيات عند إضافة/تحديث المشاريع"""
    try:
        from main.models import Statistic, SiteSettings

        # تحديث عدد المشاريع
        total_projects = Project.objects.filter(is_active=True).count()
        projects_stat = Statistic.objects.filter(auto_update_from='projects').first()
        if projects_stat and projects_stat.number != total_projects:
            projects_stat.number = total_projects
            projects_stat.save()

        # تحديث إعدادات الموقع
        site_settings = SiteSettings.get_settings()
        if site_settings.total_projects != total_projects:
            site_settings.total_projects = total_projects

            # تحديث إجمالي المستفيدين
            total_beneficiaries = Project.objects.filter(is_active=True).aggregate(
                total=Sum('beneficiaries_count')
            )['total'] or 0
            site_settings.total_beneficiaries = total_beneficiaries

            site_settings.save()

        logger.info(f"تم تحديث إحصائيات المشاريع: {total_projects}")

    except Exception as e:
        logger.error(f"خطأ في تحديث إحصائيات المشاريع: {e}")


@receiver(post_save, sender=ProjectLike)
def update_project_likes(sender, instance, created, **kwargs):
    """تحديث عدد الإعجابات"""
    if created:
        project = instance.project
        project.likes_count = project.project_likes.count()
        project.save(update_fields=['likes_count'])


# تحسين الأداء والSEO
@receiver(pre_save, sender=Project)
def optimize_project_data(sender, instance, **kwargs):
    """تحسين بيانات المشروع قبل الحفظ"""

    # تحديد وصف SEO تلقائياً إذا لم يكن موجود
    if not instance.meta_description_ar and instance.summary_ar:
        instance.meta_description_ar = instance.summary_ar[:160]

    if not instance.meta_description_en and instance.summary_en:
        instance.meta_description_en = instance.summary_en[:160]

    # ✅ تنسيق الكلمات المفتاحية بالعربية
    if instance.keywords_ar:
        keywords = [k.strip() for k in instance.keywords_ar.split(',') if k.strip()]
        instance.keywords_ar = ', '.join(keywords[:10])  # أقصى 10 كلمات

    # ✅ تنسيق الكلمات المفتاحية بالإنجليزية
    if instance.keywords_en:
        keywords = [k.strip() for k in instance.keywords_en.split(',') if k.strip()]
        instance.keywords_en = ', '.join(keywords[:10])  # أقصى 10 كلمات

    logger.debug(f"تم تحسين بيانات المشروع: {instance.title_ar}")


@receiver(post_save, sender=ProjectImage)
def update_project_main_image(sender, instance, created, **kwargs):
    """تحديث الصورة الرئيسية للمشروع"""
    if created and instance.is_active and not instance.project.main_image:
        instance.project.main_image = instance.image
        instance.project.save(update_fields=['main_image'])


# إشعارات المدير
@receiver(post_save, sender=Project)
def notify_new_project(sender, instance, created, **kwargs):
    """إشعار عند إضافة مشروع جديد"""
    if created:
        from django.core.mail import send_mail
        from django.conf import settings

        if not settings.DEBUG and hasattr(settings, 'ADMIN_EMAIL'):
            try:
                send_mail(
                    subject=f'مشروع جديد: {instance.title_ar}',
                    message=f'تم إضافة مشروع جديد: {instance.title_ar}\nالفئة: {instance.category.name_ar}',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.ADMIN_EMAIL],
                    fail_silently=True,
                )
                logger.info(f"تم إرسال إشعار المشروع الجديد: {instance.title_ar}")
            except Exception as e:
                logger.error(f"فشل في إرسال إشعار المشروع: {e}")