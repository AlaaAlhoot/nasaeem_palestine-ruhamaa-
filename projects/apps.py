from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ProjectsConfig(AppConfig):
    """تكوين تطبيق المشاريع"""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'projects'
    verbose_name = _('المشاريع')

    def ready(self):
        """يتم تنفيذها عند جاهزية التطبيق"""

        # استيراد الإشارات
        try:
            from . import signals
        except ImportError:
            pass

        # استيراد المهام المجدولة
        try:
            from . import tasks
        except ImportError:
            pass

        # إعداد إضافي للتطبيق
        self.setup_app_permissions()
        self.register_project_signals()

    def setup_app_permissions(self):
        """إعداد الصلاحيات الخاصة بالتطبيق"""
        try:
            from django.contrib.auth.models import Group, Permission
            from django.contrib.contenttypes.models import ContentType
            from .models import Project, ProjectCategory

            # إنشاء مجموعة مدير المشاريع
            project_managers, created = Group.objects.get_or_create(
                name='مدير المشاريع'
            )

            if created:
                # إضافة صلاحيات للمجموعة
                project_ct = ContentType.objects.get_for_model(Project)
                category_ct = ContentType.objects.get_for_model(ProjectCategory)

                permissions = Permission.objects.filter(
                    content_type__in=[project_ct, category_ct]
                )

                project_managers.permissions.set(permissions)

        except Exception:
            # تجاهل الأخطاء أثناء Migration
            pass

    def register_project_signals(self):
        """تسجيل إشارات المشاريع"""
        try:
            from django.db.models.signals import post_save, post_delete
            from django.core.cache import cache
            from .models import Project, ProjectCategory

            def clear_project_cache(sender, **kwargs):
                """مسح كاش المشاريع عند التحديث"""
                cache_keys = [
                    'featured_projects',
                    'recent_projects_6',
                    'popular_projects_6',
                    'project_statistics'
                ]
                for key in cache_keys:
                    cache.delete(key)

            # ربط الإشارات
            post_save.connect(clear_project_cache, sender=Project)
            post_delete.connect(clear_project_cache, sender=Project)
            post_save.connect(clear_project_cache, sender=ProjectCategory)
            post_delete.connect(clear_project_cache, sender=ProjectCategory)

        except Exception:
            pass

    def get_app_statistics(self):
        """إحصائيات التطبيق"""
        try:
            from .models import Project, ProjectCategory
            return {
                'total_projects': Project.objects.filter(is_active=True).count(),
                'total_categories': ProjectCategory.objects.filter(is_active=True).count(),
                'completed_projects': Project.objects.filter(is_active=True, status='completed').count(),
                'featured_projects': Project.objects.filter(is_active=True, is_featured=True).count(),
            }
        except Exception:
            return {}