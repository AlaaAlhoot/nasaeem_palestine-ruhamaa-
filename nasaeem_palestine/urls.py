from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.views.decorators.http import require_GET
from django.views.decorators.cache import cache_control
from main.sitemaps import (
    StaticViewSitemap, ProjectSitemap, ProjectCategorySitemap,
    OrphanSitemap, SpecialNeedsSitemap, FamilySitemap, DynamicSitemap
)
import os

# ========================================
# تعريف السايت ماب
# ========================================
sitemaps = {
    'static': StaticViewSitemap,
    'projects': ProjectSitemap,
    'categories': ProjectCategorySitemap,
    'orphans': OrphanSitemap,
    'specials': SpecialNeedsSitemap,
    'families': FamilySitemap,
    'dynamic': DynamicSitemap,
}


# ========================================
# Service Worker View
# ========================================
@require_GET
@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
def service_worker(request):
    sw_path = os.path.join(settings.BASE_DIR, 'sw.js')
    try:
        with open(sw_path, 'r', encoding='utf-8') as f:
            sw_content = f.read()
        return HttpResponse(sw_content, content_type='application/javascript; charset=utf-8')
    except FileNotFoundError:
        return HttpResponse(
            'console.error("❌ Service Worker file not found at: ' + sw_path + '");',
            content_type='application/javascript', status=404
        )
    except Exception as e:
        return HttpResponse(
            f'console.error("❌ Error loading SW: {str(e)}");',
            content_type='application/javascript', status=500
        )


# ========================================
# Manifest View (PWA)
# ========================================
@require_GET
@cache_control(max_age=86400)
def manifest(request):
    manifest_path = os.path.join(settings.BASE_DIR, 'manifest.json')
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_content = f.read()
        return HttpResponse(manifest_content, content_type='application/json; charset=utf-8')
    except FileNotFoundError:
        default_manifest = '''{
            "name": "جمعية نسائم فلسطين الخيرية",
            "short_name": "نسائم فلسطين",
            "description": "مؤسسة خيرية تنموية إنسانية",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#ffffff",
            "theme_color": "#6B8E23",
            "dir": "rtl",
            "lang": "ar",
            "icons": [{"src": "/static/images/logo.png", "sizes": "192x192", "type": "image/png"}]
        }'''
        return HttpResponse(default_manifest, content_type='application/json; charset=utf-8')
    except Exception as e:
        return HttpResponse(
            f'{{"error": "Failed to load manifest: {str(e)}"}}',
            content_type='application/json; charset=utf-8', status=500
        )


# ========================================
# URL Patterns الرئيسية
# ========================================
urlpatterns = [
    # Admin Panel
    path('admin/', admin.site.urls),

    # PWA Files
    path('sw.js', service_worker, name='service_worker'),
    path('manifest.json', manifest, name='manifest'),

    # CKEditor
    path("ckeditor5/", include("django_ckeditor_5.urls")),

    # Sitemap
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),

    # Internationalization
    path('i18n/', include('django.conf.urls.i18n')),

    # Authentication
    path('accounts/', include('django.contrib.auth.urls')),

    # تطبيقات رحماء — بدون ترجمة
    path('admin-panel/', include('admin_panel.urls')),
    path('sponsor/', include('sponsor.urls')),
    path('beneficiary/', include('beneficiary.urls')),
]

# ========================================
# مسارات تدعم الترجمة
# ========================================
urlpatterns += i18n_patterns(
    path('', include('main.urls')),
    path('projects/', include('projects.urls')),
    path('contact/', include('contact.urls')),
    path('dashboard/', include('dashboard.urls')),
    prefix_default_language=False,
)

# ========================================
# ملفات Media و Static
# ========================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# ========================================
# تخصيص لوحة الإدارة
# ========================================
admin.site.site_header = "جمعية نسائم فلسطين الخيرية"
admin.site.site_title = "لوحة التحكم"
admin.site.index_title = "إدارة الموقع"

# ========================================
# معالجات الأخطاء
# ========================================
handler404 = 'main.views.handler404'
handler500 = 'main.views.handler500'
handler403 = 'main.views.handler403'
handler400 = 'main.views.handler400'


# ══ اختبار صفحات الخطأ في وضع التطوير ══
if settings.DEBUG:
    from main import views as main_views
    urlpatterns += [
        path('test/404/', lambda r: main_views.handler404(r, None)),
        path('test/500/', lambda r: main_views.handler500(r)),
        path('test/403/', lambda r: main_views.handler403(r, None)),
        path('test/400/', lambda r: main_views.handler400(r, None)),
    ]