# nasaeem_palestine/main/urls.py

from django.urls import path
from django.views.generic import TemplateView
from . import views
from admin_panel.views import complaints

app_name = 'main'

urlpatterns = [
    # ==================== الصفحة الرئيسية ====================
    path('', views.home_view, name='home'),

    # ==================== الصفحات الثابتة ====================
    path('about/', views.about_view, name='about'),
    path('vision/', views.vision_view, name='vision'),
    path('goals/', views.goals_view, name='goals'),
    path('board/', views.board_view, name='board'),
    path('partners/', views.partners_view, name='partners'),
    # path('location/', views.location_view, name='location'),

    # ==================== البحث ====================
    path('search/', views.search_view, name='search'),

    # ==================== API Endpoints نسائم ====================
    path('api/site-settings/', views.get_site_settings_api, name='api_site_settings'),
    path('api/statistics/', views.get_statistics_api, name='api_statistics'),
    path('api/update-statistics/', views.update_statistics, name='update_statistics'),

    # ==================== API Endpoints رحماء ====================
    path('api/countries/', views.countries_api, name='countries_api'),
    path('api/rates/', views.exchange_rates_api, name='exchange_rates'),
    path('api/check-unique/', views.check_unique_api, name='check_unique'),

    # ==================== صفحات رحماء ====================
    path('ruhamaa/', views.ruhamaa_home_view, name='ruhamaa_home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('faq/', views.faq_view, name='faq'),
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('contact/submit/', complaints.public_submit, name='public_contact'),

    # ==================== صفحات قانونية ====================
    path('privacy-policy/', TemplateView.as_view(
        template_name='main/privacy_policy.html',
        extra_context={'page_title': 'سياسة الخصوصية'}
    ), name='privacy_policy'),

    path('terms-of-service/', TemplateView.as_view(
        template_name='main/terms_of_service.html',
        extra_context={'page_title': 'شروط الخدمة'}
    ), name='terms_of_service'),

    # ==================== صفحات SEO ====================
    path('sitemap/', TemplateView.as_view(
        template_name='main/sitemap.html',
        extra_context={'page_title': 'خريطة الموقع'}
    ), name='sitemap_page'),

    path('robots.txt', TemplateView.as_view(
        template_name='main/robots.txt',
        content_type='text/plain'
    ), name='robots_txt'),
]