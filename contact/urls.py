from django.urls import path
from . import views

app_name = 'contact'

urlpatterns = [
    # ==========================================
    # Contact Pages
    # ==========================================
    path('',      views.contact_page_view, name='contact_page'),
    path('send/', views.contact_view,      name='contact'),

    # ==========================================
    # Newsletter
    # ==========================================
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
    path('newsletter/confirm/<str:token>/', views.newsletter_confirm, name='newsletter_confirm'),
    path('newsletter/unsubscribe/<str:token>/', views.newsletter_unsubscribe, name='newsletter_unsubscribe'),

    # ==========================================
    # FAQ Pages
    # ==========================================
    path('faq/', views.faq_list, name='faq_list'),
    path('faq/<int:faq_id>/', views.faq_detail, name='faq_detail'),
    path('faq/<int:faq_id>/helpful/', views.mark_faq_helpful, name='mark_faq_helpful'),
    path('faq/<int:faq_id>/track-view/', views.track_faq_view, name='track_faq_view'),
    path('faq/search-api/', views.faq_search_api, name='faq_search_api'),

    # ==========================================
    # AJAX APIs
    # ==========================================
    path('ajax/send-message/', views.send_message_ajax, name='send_message_ajax'),
    path('ajax/subscribe/', views.subscribe_ajax, name='subscribe_ajax'),
    path('ajax/social-click/<int:social_id>/', views.track_social_click, name='track_social_click'),
]