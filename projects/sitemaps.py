from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone
from .models import Project, ProjectCategory
from contact import models
from projects import models
from  main import  models

class ProjectSitemap(Sitemap):
    """خريطة موقع المشاريع"""

    changefreq = 'weekly'
    priority = 0.9
    protocol = 'https'

    def items(self):
        return Project.objects.filter(is_active=True).select_related('category').order_by('-updated_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()

    def priority_func(self, obj):
        """أولوية المشروع"""
        if obj.is_featured:
            return 1.0
        elif obj.status == 'active':
            return 0.9
        elif obj.status == 'completed':
            return 0.8
        else:
            return 0.7

    def changefreq_func(self, obj):
        """تكرار التحديث"""
        if obj.status == 'active':
            return 'daily'
        elif obj.status == 'planning':
            return 'weekly'
        else:
            return 'monthly'


class ProjectCategorySitemap(Sitemap):
    """خريطة موقع فئات المشاريع"""

    changefreq = 'monthly'
    priority = 0.8
    protocol = 'https'

    def items(self):
        return ProjectCategory.objects.filter(is_active=True).annotate(
            projects_count=models.Count('projects', filter=models.Q(projects__is_active=True))
        ).filter(projects_count__gt=0).order_by('-updated_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()

    def priority_func(self, obj):
        """أولوية الفئة حسب عدد المشاريع"""
        projects_count = obj.get_projects_count()
        if projects_count >= 10:
            return 1.0
        elif projects_count >= 5:
            return 0.9
        else:
            return 0.8


class ProjectsStaticSitemap(Sitemap):
    """خريطة موقع الصفحات الثابتة للمشاريع"""

    changefreq = 'weekly'
    priority = 0.7
    protocol = 'https'

    def items(self):
        return ['projects:all_projects']

    def location(self, item):
        return reverse(item)

    def lastmod(self, item):
        # آخر تحديث لأي مشروع
        try:
            return Project.objects.filter(is_active=True).latest('updated_at').updated_at
        except Project.DoesNotExist:
            return timezone.now()


# تجميع خرائط المواقع
sitemaps = {
    'projects': ProjectSitemap,
    'project-categories': ProjectCategorySitemap,
    'projects-static': ProjectsStaticSitemap,
}