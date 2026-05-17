from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    # الصفحات الرئيسية
    path('', views.all_projects, name='all_projects'),
    path('search/', views.search_projects, name='search_projects'),
    path('category/<slug:slug>/', views.category_projects, name='category_projects'),
    path('project/<slug:slug>/', views.project_detail, name='project_detail'),


    # Ajax URLs
    path('ajax/like/<int:project_id>/', views.project_like, name='project_like'),
    path('ajax/share/<int:project_id>/', views.increment_project_share, name='increment_share'),
    path('ajax/stats/<int:project_id>/', views.get_project_stats, name='project_stats'),
    path('ajax/category/<int:category_id>/projects/', views.get_category_projects_ajax, name='category_projects_ajax'),
    path('not-found/', views.project_not_found_page, name='project_not_found'),
    # تحميل الملفات
    path('document/<int:document_id>/download/', views.download_document, name='download_document'),

    # Class-based Views البديلة (معلقة)
    # path('list/', views.ProjectListView.as_view(), name='projects_list'),
    # path('detail/<slug:slug>/', views.ProjectDetailView.as_view(), name='project_detail_cbv'),

    # API endpoints للتطبيق الجوال
    path('api/featured/', views.get_featured_projects_api, name='api_featured_projects'),
    path('api/recent/', views.get_recent_projects_api, name='api_recent_projects'),
    path('api/popular/', views.get_popular_projects_api, name='api_popular_projects'),
    path('api/statistics/', views.get_project_statistics_api, name='api_project_statistics'),
    path('api/categories/', views.get_categories_api, name='api_categories'),
]

handler404 = 'projects.views.project_not_found'