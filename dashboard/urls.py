from django.urls import path
from django.views.decorators.cache import cache_page
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'dashboard'

urlpatterns = [
    # ========================================
    # الصفحات الرئيسية
    # ========================================
    path('', views.dashboard_home, name='home'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('reports/', views.reports_view, name='reports'),

    # ========================================
    # الاعدادات
    # ========================================
    path('settings/', views.settings_view, name='settings'),

    # API الإعدادات
    path('api/settings/reset/', views.reset_settings_api, name='reset_settings'),  # ✅ جديد
    path('api/cache/clear/', views.clear_cache_api, name='clear_cache'),
    path('api/database/optimize/', views.optimize_database_api, name='optimize_database'),
    path('api/performance/check/', views.check_performance_api, name='check_performance'),


    # ========================================
    # النسخ الاحتياطي
    # ========================================



    # ========================================
    # إدارة المحتوى
    # ========================================
    path('content/', views.content_management, name='content_management'),
    path('content/site-settings/', views.content_management, name='site_settings'),
    path('content/slider/', views.content_management, name='slider_management'),
    path('content/statistics/', views.content_management, name='statistics_management'),

    # ========================================
    # إدارة المستخدمين
    # ========================================
    path('users/', views.users_management, name='users_management'),

    # ========================================
    # Ajax APIs - المحددة أولاً (Specific APIs First)
    # ========================================

    # السلايدر
    path('api/slider/<int:item_id>/view/', views.view_slider_ajax, name='view_slider_ajax'),
    path('api/slider/<int:item_id>/edit/', views.edit_slider_ajax, name='api_slider_edit'),
    path('api/slider/<int:item_id>/delete/', views.delete_slider_ajax, name='api_slider_delete'),

    # الإحصائيات
    path('api/statistic/<int:item_id>/delete/', views.delete_statistic_ajax, name='api_statistic_delete'),
    path('api/statistic/<int:item_id>/edit/', views.edit_statistic_ajax, name='api_statistic_edit'),
    path('api/statistics/used-icons/', views.get_used_icons, name='get_used_icons'),
    path('api/stat/<int:item_id>/edit/', views.edit_stat_ajax, name='api_stat_edit'),

    # الأهداف
    path('api/goal/<int:item_id>/delete/', views.delete_goal_ajax, name='api_goal_delete'),
    path('api/goal/<int:item_id>/edit/', views.edit_goal_ajax, name='api_goal_edit'),
    path('api/goal/<int:item_id>/view/', views.view_goal_ajax, name='view_goal_ajax'),

    path('api/save-value/', views.save_value, name='save_value'),
    path('api/delete-value/', views.delete_value, name='delete_value'),

    # مجلس الإدارة
    path('api/board-member/<int:item_id>/delete/', views.delete_board_member_ajax, name='delete_board_member_ajax'),
    path('api/board-member/<int:item_id>/edit/', views.edit_board_member_ajax, name='edit_board_member_ajax'),
    path('api/board/<int:item_id>/delete/', views.delete_board_member_ajax, name='api_board_delete'),
    path('api/board/<int:item_id>/edit/', views.edit_board_member_ajax, name='api_board_edit'),
    path('api/board-member/<int:item_id>/view/', views.view_board_member_ajax, name='view_board_member_ajax'),

    # ========================================
    # APIs - التصنيفات (Categories)
    # ========================================
    path('api/categories/', views.get_categories_ajax, name='get_categories'),
    path('api/category/add/', views.add_category_ajax, name='add_category'),
    path('api/category/<int:cat_id>/edit/', views.edit_category_ajax, name='edit_category'),
    path('api/category/<int:cat_id>/delete/', views.delete_category_ajax, name='delete_category'),

    # ========================================
    # APIs - الأسئلة الشائعة (FAQ)
    # ========================================
    path('api/faq/add/', views.add_faq_ajax, name='add_faq'),
    path('api/faq/<int:item_id>/edit/', views.edit_faq_ajax, name='edit_faq'),
    path('api/faq/<int:item_id>/view/', views.view_faq_ajax, name='view_faq'),
    path('api/faq/<int:item_id>/delete/', views.delete_faq_ajax, name='delete_faq'),

    # الرسائل
    path('api/message/<int:item_id>/view/', views.view_message_ajax, name='view_message_ajax'),
    path('api/message/<int:item_id>/reply/', views.reply_message_ajax, name='reply_message_ajax'),
    path('api/message/<int:item_id>/delete/', views.delete_message_ajax, name='delete_message_ajax'),

    # Newsletter
    path('api/newsletter/<int:item_id>/view/', views.view_newsletter_ajax, name='view_newsletter_ajax'),
    path('api/newsletter/<int:item_id>/delete/', views.delete_newsletter_ajax, name='delete_newsletter_ajax'),

    # التواصل الاجتماعي
    path('api/social/<int:item_id>/view/', views.view_social_ajax, name='view_social_ajax'),
    path('api/social/<int:item_id>/edit/', views.edit_social_ajax, name='edit_social_ajax'),
    path('api/social/<int:item_id>/delete/', views.delete_social_ajax, name='delete_social_ajax'),
    path('api/social/available-platforms/', views.get_available_platforms_ajax, name='get_available_platforms_ajax'),

    # الشركاء
    path('api/partner/<int:item_id>/view/', views.view_partner_ajax, name='view_partner_ajax'),
    path('api/partner/<int:item_id>/edit/', views.edit_partner_ajax, name='edit_partner_ajax'),
    path('api/partner/<int:item_id>/delete/', views.delete_partner_ajax, name='delete_partner_ajax'),

    # معلومات الاتصال
    path('api/contact-info/<int:item_id>/view/', views.view_contact_info_ajax, name='view_contact_info_ajax'),
    path('api/contact-info/<int:item_id>/edit/', views.edit_contact_info_ajax, name='edit_contact_info_ajax'),
    path('api/contact-info/<int:item_id>/delete/', views.delete_contact_info_ajax, name='delete_contact_info_ajax'),

    # فئات المشاريع
    path('api/project-category/<int:item_id>/view/', views.view_project_category_ajax,
         name='view_project_category_ajax'),
    path('api/project-category/<int:item_id>/edit/', views.edit_project_category_ajax,
         name='edit_project_category_ajax'),
    path('api/project-category/<int:item_id>/delete/', views.delete_project_category_ajax,
         name='delete_project_category_ajax'),

    # المشاريع
    path('api/project/<int:item_id>/view/', views.view_project_ajax, name='view_project_ajax'),
    path('api/project/<int:item_id>/edit/', views.edit_project_ajax, name='edit_project_ajax'),
    path('api/project/<int:item_id>/delete/', views.delete_project_ajax, name='delete_project_ajax'),

# المستخدمين
path('api/users/create/',                    views.create_user_ajax,        name='api_user_create'),
path('api/users/<uuid:user_id>/view/',       views.view_user_ajax,          name='api_user_view'),
path('api/users/<uuid:user_id>/edit/',       views.edit_user_ajax,          name='api_user_edit'),
path('api/users/<uuid:user_id>/delete/',     views.delete_user_ajax,        name='api_user_delete'),
path('api/users/toggle-status/',             views.update_user_status_ajax, name='api_user_toggle_status'),
path('api/users/stats/',                     views.get_users_stats_ajax,    name='api_users_stats'),

    # نشاط المستخدمين
    path('activity-logs/', views.activity_logs_view, name='activity_logs'),

    # ========================================
    # Ajax APIs - العامة (General APIs)
    # ========================================
    path('api/statistics/', views.get_statistics_ajax, name='api_statistics'),
    path('api/chart-data/', views.get_chart_data_ajax, name='api_chart_data'),
    path('api/system-status/', views.get_statistics_ajax, name='api_system_status'),

    # التقارير
    path('reports/', views.reports_view, name='reports'),
    path('reports/generate/', views.generate_report_api, name='generate_report_api'),
    path('reports/logs/', views.report_logs_view, name='report_logs'),
    path('reports/logs/<int:log_id>/regenerate/', views.regenerate_report_ajax, name='regenerate_report_ajax'),
    path('reports/logs/<int:log_id>/delete/', views.delete_report_log_ajax, name='delete_report_log_ajax'),
    path('reports/logs/<int:log_id>/details/', views.report_details_ajax, name='report_details_ajax'),


    # ========================================
    # النسخ الاحتياطي
    # ========================================
    path('backup/', views.backup_view, name='backup'),
    path('backup/create/', views.create_backup_ajax, name='create_backup'),
    path('backup/restore/', views.restore_backup_ajax, name='restore_backup'),
    path('backup/delete/', views.delete_backup_ajax, name='delete_backup'),
    path('backup/download/<str:filename>/', views.download_backup, name='download_backup'),

    # ========================================
    # إدارة المشاريع (روابط سريعة)
    # ========================================
    path('projects/', views.dashboard_home, name='projects_management'),
    path('projects/categories/', views.dashboard_home, name='categories_management'),

    # ========================================
    # إدارة الرسائل (روابط سريعة)
    # ========================================
    path('messages/', views.dashboard_home, name='messages_management'),
    path('messages/contact/', views.dashboard_home, name='contact_messages'),
    path('messages/newsletter/', views.dashboard_home, name='newsletter_management'),

    # ========================================
    # الملف الشخصي
    # ========================================
    path('profile/', views.dashboard_home, name='profile'),
    path('profile/edit/', views.dashboard_home, name='profile_edit'),

    # ========================================
    # سجل الأنشطة
    # ========================================
    path('activity-log/', views.analytics_view, name='activity_log'),
    path('activity-log/<int:log_id>/', views.analytics_view, name='activity_detail'),

    # ========================================
    # صحة النظام
    # ========================================
    path('system-health/', views.analytics_view, name='system_health'),

    # ========================================
    # أدوات مساعدة
    # ========================================
    path('tools/', views.dashboard_home, name='tools'),
    path('tools/backup/', views.dashboard_home, name='backup_tool'),
    path('tools/cache-clear/', views.dashboard_home, name='cache_clear'),
    path('tools/maintenance/', views.dashboard_home, name='maintenance_mode'),

    # ========================================
    # الإعدادات المتقدمة
    # ========================================
    path('settings/security/', views.settings_view, name='security_settings'),
    path('settings/email/', views.settings_view, name='email_settings'),
    path('settings/backup/', views.settings_view, name='backup_settings'),
    path('settings/performance/', views.settings_view, name='performance_settings'),

    # ========================================
    # التصدير والاستيراد
    # ========================================
    path('export/', views.reports_view, name='export_data'),
    path('export/<str:data_type>/', views.reports_view, name='export_specific'),
    path('import/', views.reports_view, name='import_data'),

    # ========================================
    # الأرشيف والنسخ الاحتياطي
    # ========================================


    # ========================================
    # اختبارات النظام
    # ========================================
    path('tests/', views.analytics_view, name='system_tests'),
    path('tests/database/', views.analytics_view, name='database_test'),
    path('tests/email/', views.analytics_view, name='email_test'),
    path('tests/performance/', views.analytics_view, name='performance_test'),

    # ========================================
    # مسارات خاصة للتطبيق الجوال (مستقبلياً)
    # ========================================
    path('mobile/', views.dashboard_home, name='mobile_dashboard'),
    path('mobile/api/', views.get_statistics_ajax, name='mobile_api'),
]

# ========================================
# مسارات إضافية للتطوير وتصحيح الأخطاء
# ========================================
if hasattr(settings, 'DEBUG') and settings.DEBUG:
    urlpatterns += [
        # مسارات التطوير
        path('debug/logs/', views.analytics_view, name='debug_logs'),
        path('debug/cache/', views.analytics_view, name='debug_cache'),
        path('debug/sessions/', views.analytics_view, name='debug_sessions'),
        path('debug/permissions/', views.analytics_view, name='debug_permissions'),

        # اختصارات سريعة للمطورين
        path('quick/new-project/', views.dashboard_home, name='quick_new_project'),
        path('quick/new-user/', views.dashboard_home, name='quick_new_user'),
        path('quick/messages/', views.dashboard_home, name='quick_messages'),
        path('quick/backup/', views.dashboard_home, name='quick_backup'),
    ]

    # مسارات مع تخزين مؤقت للتطوير
    cached_patterns = [
        # تخزين الإحصائيات لمدة 5 دقائق
        path('api/statistics/cached/',
             cache_page(60 * 5)(views.get_statistics_ajax),
             name='api_statistics_cached'),

        # تخزين بيانات المخططات لمدة 10 دقائق
        path('api/chart-data/cached/',
             cache_page(60 * 10)(views.get_chart_data_ajax),
             name='api_chart_data_cached'),

        # تخزين صحة النظام لمدة دقيقة واحدة
        path('api/system-health/cached/',
             cache_page(60)(views.get_statistics_ajax),
             name='api_system_health_cached'),
    ]

    urlpatterns += cached_patterns

# ========================================
# معالجات الأخطاء
# ========================================
handler404 = 'dashboard.views.custom_404'
handler500 = 'dashboard.views.custom_500'

# ========================================
# معلومات تجميع المسارات (للتوثيق والتنظيم)
# ========================================
dashboard_patterns_info = {
    'main_pages': [
        '', 'analytics/', 'reports/', 'settings/'
    ],
    'content_management': [
        'content/', 'content/site-settings/', 'content/slider/', 'content/statistics/'
    ],
    'users_management': [
        'users/', 'users/create/', 'users/<int:user_id>/edit/', 'users/<int:user_id>/profile/'
    ],
    'api_endpoints': [
        'api/statistics/', 'api/chart-data/', 'api/system-status/',
        'api/users/toggle-status/', 'api/reports/generate/', 'api/settings/reset/'  # ✅ محدث
    ],
    'tools_utilities': [
        'tools/', 'tools/backup/', 'tools/cache-clear/', 'tools/maintenance/'
    ],
    'system_management': [
        'backup/', 'export/', 'import/', 'tests/'
    ]
}

# إحصائيات المسارات
urlpatterns_statistics = {
    'total_patterns': len(urlpatterns),
    'api_endpoints': len([p for p in urlpatterns if 'api/' in str(p.pattern)]),
    'main_pages': len([p for p in urlpatterns if not 'api/' in str(p.pattern) and not 'debug/' in str(p.pattern)]),
    'admin_only_patterns': len([p for p in urlpatterns if any(
        restricted in str(p.pattern) for restricted in ['users/', 'settings/', 'backup/'])]),
    'debug_patterns': len([p for p in urlpatterns if 'debug/' in str(p.pattern)]) if hasattr(settings,
                                                                                             'DEBUG') and settings.DEBUG else 0
}

# خريطة الصلاحيات للمسارات (للمرجع)
permission_required_patterns = {
    'super_admin_only': [
        'settings/security/', 'backup/', 'tools/maintenance/', 'debug/', 'api/settings/reset/'  # ✅ محدث
    ],
    'admin_required': [
        'users/', 'settings/', 'tools/', 'api/users/', 'api/backup/'
    ],
    'editor_allowed': [
        'content/', 'reports/', 'api/content/', 'api/reports/'
    ],
    'viewer_allowed': [
        '', 'analytics/', 'profile/', 'api/statistics/', 'api/chart-data/'
    ],
    'all_authenticated': [
        'profile/', 'api/notifications/', 'mobile/'
    ]
}

# مسارات خارجية (للمرجع)
external_links = {
    'main_site': '/',
    'django_admin': '/admin/',
    'projects_app': '/projects/',
    'contact_app': '/contact/',
    'api_root': '/api/'
}

# ✅ في نهاية الملف
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
