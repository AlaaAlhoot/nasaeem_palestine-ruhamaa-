# main/sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone
from .models import SiteSettings, Goal, BoardMember, HomeSlider


# ==================== الصفحات الثابتة ====================

class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return [
            'main:home',
            'main:about',
            'main:vision',
            'main:goals',
            'main:board',
            'main:location',
            'main:search',
            'main:privacy_policy',
            'main:terms_of_service',
            'main:sitemap_page',
        ]

    def location(self, item):
        return reverse(item)

    def lastmod(self, item):
        if item == 'main:home':
            try:
                slider_update = HomeSlider.objects.filter(is_active=True).latest('updated_at')
                settings_update = SiteSettings.get_settings()
                return max(slider_update.updated_at, settings_update.updated_at)
            except:
                return timezone.now()
        elif item == 'main:goals':
            try:
                return Goal.objects.filter(is_active=True).latest('updated_at').updated_at
            except:
                return timezone.now()
        elif item == 'main:board':
            try:
                return BoardMember.objects.filter(is_active=True).latest('updated_at').updated_at
            except:
                return timezone.now()
        return timezone.now()

    def priority_func(self, item):
        priorities = {
            'main:home': 1.0,
            'main:about': 0.9,
            'main:vision': 0.8,
            'main:goals': 0.8,
            'main:board': 0.7,
            'main:location': 0.7,
            'main:search': 0.5,
            'main:privacy_policy': 0.4,
            'main:terms_of_service': 0.4,
            'main:sitemap_page': 0.3,
        }
        return priorities.get(item, 0.5)

    def changefreq_func(self, item):
        frequencies = {
            'main:home': 'daily',
            'main:about': 'monthly',
            'main:vision': 'monthly',
            'main:goals': 'monthly',
            'main:board': 'yearly',
            'main:location': 'yearly',
            'main:search': 'daily',
            'main:privacy_policy': 'yearly',
            'main:terms_of_service': 'yearly',
            'main:sitemap_page': 'weekly',
        }
        return frequencies.get(item, 'monthly')


# ==================== المشاريع ====================

class ProjectSitemap(Sitemap):
    priority = 0.9
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        try:
            from projects.models import Project
            return Project.objects.filter(is_active=True).order_by('-created_at')
        except ImportError:
            return []

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()

    def priority_func(self, obj):
        base_priority = 0.8
        if hasattr(obj, 'views_count') and obj.views_count > 100:
            return min(1.0, base_priority + 0.2)
        return base_priority


# ==================== فئات المشاريع ====================

class ProjectCategorySitemap(Sitemap):
    priority = 0.7
    changefreq = 'monthly'
    protocol = 'https'

    def items(self):
        try:
            from projects.models import ProjectCategory
            return ProjectCategory.objects.filter(is_active=True).order_by('order')
        except ImportError:
            return []

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f'/projects/category/{obj.slug}/'


# ==================== الأيتام المقبولون ====================

class OrphanSitemap(Sitemap):
    priority = 0.6
    changefreq = 'monthly'
    protocol = 'https'

    def items(self):
        try:
            from beneficiary.models import OrphanForm
            return OrphanForm.objects.filter(status='تم التكفل').order_by('-updated_at')
        except ImportError:
            return []

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f'/beneficiary/orphan/{obj.form_number}/'


# ==================== ذوو الاحتياجات الخاصة المقبولون ====================

class SpecialNeedsSitemap(Sitemap):
    priority = 0.6
    changefreq = 'monthly'
    protocol = 'https'

    def items(self):
        try:
            from beneficiary.models import SpecialNeedsForm
            return SpecialNeedsForm.objects.filter(status='تم التكفل').order_by('-updated_at')
        except ImportError:
            return []

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f'/beneficiary/special/{obj.form_number}/'


# ==================== الأسر المقبولة ====================

class FamilySitemap(Sitemap):
    priority = 0.6
    changefreq = 'monthly'
    protocol = 'https'

    def items(self):
        try:
            from beneficiary.models import FamilyForm
            return FamilyForm.objects.filter(status='تم التكفل').order_by('-updated_at')
        except ImportError:
            return []

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f'/beneficiary/family/{obj.form_number}/'


# ==================== الصفحات الديناميكية ====================

class DynamicSitemap(Sitemap):
    priority = 0.6
    changefreq = 'monthly'

    def items(self):
        items = []
        goals = Goal.objects.filter(is_active=True)
        for goal in goals:
            items.append(('goal', goal.id, goal.updated_at))
        board_members = BoardMember.objects.filter(is_active=True)
        for member in board_members:
            items.append(('board_member', member.id, member.updated_at))
        return items

    def location(self, item):
        item_type, item_id, _ = item
        if item_type == 'goal':
            return f'/goals/{item_id}/'
        elif item_type == 'board_member':
            return f'/board/{item_id}/'
        return '/'

    def lastmod(self, item):
        _, _, lastmod = item
        return lastmod


# ==================== تجميع جميع خرائط المواقع ====================

sitemaps = {
    'static': StaticViewSitemap,
    'projects': ProjectSitemap,
    'categories': ProjectCategorySitemap,
    'orphans': OrphanSitemap,
    'specials': SpecialNeedsSitemap,
    'families': FamilySitemap,
    'dynamic': DynamicSitemap,
}


# ==================== دوال مساعدة ====================

def generate_sitemap_index():
    from django.http import HttpResponse
    from django.template import Template, Context

    template = Template("""<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    {% for sitemap_name, sitemap_class in sitemaps.items %}
        <sitemap>
            <loc>{{ protocol }}://{{ domain }}/sitemap-{{ sitemap_name }}.xml</loc>
            <lastmod>{{ current_date|date:"Y-m-d" }}</lastmod>
        </sitemap>
    {% endfor %}
    </sitemapindex>""")

    context = Context({
        'sitemaps': sitemaps,
        'protocol': 'https',
        'domain': 'www.nasaeem-palestine.com',
        'current_date': timezone.now(),
    })

    return HttpResponse(template.render(context), content_type='application/xml')


def get_sitemap_urls():
    from django.urls import reverse
    urls = []

    static_sitemap = StaticViewSitemap()
    for item in static_sitemap.items():
        try:
            url = reverse(item)
            urls.append({
                'url': url,
                'priority': static_sitemap.priority_func(item),
                'changefreq': static_sitemap.changefreq_func(item),
                'lastmod': static_sitemap.lastmod(item),
            })
        except:
            continue

    project_sitemap = ProjectSitemap()
    for project in project_sitemap.items():
        urls.append({
            'url': project.get_absolute_url(),
            'priority': project_sitemap.priority_func(project),
            'changefreq': project_sitemap.changefreq,
            'lastmod': project_sitemap.lastmod(project),
        })

    return urls


def validate_sitemap():
    errors = []

    static_sitemap = StaticViewSitemap()
    for item in static_sitemap.items():
        try:
            reverse(item)
        except Exception as e:
            errors.append(f"خطأ في الرابط {item}: {e}")

    try:
        from projects.models import Project
        inactive_projects = Project.objects.filter(is_active=False).count()
        if inactive_projects > 0:
            errors.append(f"يوجد {inactive_projects} مشروع غير مفعل في قاعدة البيانات")
    except ImportError:
        errors.append("تطبيق المشاريع غير متاح")

    return errors


def update_search_engines():
    import requests
    from django.conf import settings

    if not settings.DEBUG:
        sitemap_url = "https://www.nasaeem-palestine.com/sitemap.xml"
        try:
            requests.get(f"https://www.google.com/ping?sitemap={sitemap_url}", timeout=10)
        except:
            pass
        try:
            requests.get(f"https://www.bing.com/ping?sitemap={sitemap_url}", timeout=10)
        except:
            pass