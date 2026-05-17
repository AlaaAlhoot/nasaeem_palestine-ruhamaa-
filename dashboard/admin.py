from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.forms import Textarea

from .models import (
    UserProfile,
    SiteSetting,
    ActivityLog,
    SystemHealth,
    NotificationSettings,
    QuickAction,
    ReportLog
)


# ========================================
# UserProfile Admin
# ========================================
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name_ar', 'role', 'department', 'is_active_staff', 'last_activity', 'avatar_preview']
    list_filter = ['role', 'is_active_staff', 'dashboard_theme', 'created_at']
    search_fields = ['user__username', 'user__email', 'full_name_ar', 'full_name_en', 'department']
    readonly_fields = ['created_at', 'updated_at', 'last_activity', 'login_count', 'avatar_preview']

    fieldsets = (
        (_('معلومات المستخدم'), {
            'fields': ('user', 'full_name_ar', 'full_name_en', 'avatar', 'avatar_preview', 'phone', 'bio')
        }),
        (_('معلومات العمل'), {
            'fields': ('role', 'department', 'is_active_staff')
        }),
        (_('تفضيلات اللوحة'), {
            'fields': ('dashboard_theme', 'language_preference', 'items_per_page')
        }),
        (_('الإشعارات'), {
            'fields': ('email_notifications', 'browser_notifications', 'sms_notifications')
        }),
        (_('إحصائيات'), {
            'fields': ('last_login_ip', 'login_count', 'last_activity')
        }),
        (_('التواريخ'), {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width:50px;height:50px;border-radius:50%;object-fit:cover;" />',
                obj.avatar.url
            )
        return format_html('<span style="color:#999;">لا توجد صورة</span>')

    avatar_preview.short_description = _('الصورة')


# ========================================
# SiteSetting Admin - محدث
# ========================================
@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = [
        '__str__',
        'maintenance_mode',
        'enable_two_factor',
        'enable_compression',
        'updated_at'
    ]
    readonly_fields = ['updated_at']

    fieldsets = (
        (_('عام'), {
            'fields': (
                'site_name_ar',
                'site_name_en',
                'site_description',
                'site_email',
                'site_phone'
            ),
            'classes': ('collapse',)
        }),
        (_('الصيانة'), {
            'fields': (
                'maintenance_mode',
                'maintenance_message_ar',
                'maintenance_message_en'
            )
        }),
        (_('الأمان'), {
            'fields': (
                'enable_two_factor',
                'session_timeout',
                'max_login_attempts',
                'force_https',
                'enable_ip_blocking'
            ),
            'classes': ('collapse',)
        }),
        (_('الأداء'), {
            'fields': (
                'cache_timeout',
                'enable_compression',
                'enable_lazy_loading',
                'enable_minification'
            ),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        """منع إضافة أكثر من سجل واحد"""
        return not SiteSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """منع حذف الإعدادات"""
        return False


# ========================================
# ActivityLog Admin
# ========================================
@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp',
        'username',
        'action',
        'title',
        'level_badge',
        'ip_address'
    ]
    list_filter = ['action', 'level', 'timestamp']
    search_fields = ['username', 'title', 'description', 'ip_address']
    readonly_fields = [
        'timestamp',
        'user',
        'username',
        'action',
        'title',
        'description',
        'level',
        'ip_address',
        'user_agent',
        'session_key',
        'content_type',
        'object_id'
    ]
    date_hierarchy = 'timestamp'

    def level_badge(self, obj):
        colors = {
            'info': '#17a2b8',
            'warning': '#ffc107',
            'error': '#dc3545',
            'success': '#28a745',
        }
        color = colors.get(obj.level, '#6c757d')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; border-radius:3px;">{}</span>',
            color,
            obj.get_level_display()
        )

    level_badge.short_description = _('المستوى')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ========================================
# SystemHealth Admin
# ========================================
@admin.register(SystemHealth)
class SystemHealthAdmin(admin.ModelAdmin):
    list_display = [
        'checked_at',
        'status_badge',
        'response_time',
        'memory_usage_percent',
        'cpu_usage_percent',
        'disk_usage_percent'
    ]
    list_filter = ['status', 'checked_at']
    readonly_fields = [
        'checked_at',
        'status',
        'response_time',
        'memory_usage_percent',
        'memory_total',
        'memory_used',
        'disk_usage_percent',
        'disk_total',
        'disk_used',
        'cpu_usage_percent',
        'db_connections',
        'db_query_time',
        'active_users',
        'errors_count',
        'warnings_count'
    ]
    date_hierarchy = 'checked_at'

    def status_badge(self, obj):
        return format_html(
            '<span style="color:{};">●</span> {}',
            obj.get_status_color(),
            obj.get_status_display()
        )

    status_badge.short_description = _('الحالة')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ========================================
# NotificationSettings Admin
# ========================================
@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'notification_type',
        'email_enabled',
        'browser_enabled',
        'send_immediately'
    ]
    list_filter = [
        'notification_type',
        'email_enabled',
        'browser_enabled',
        'send_immediately'
    ]
    search_fields = ['user__username', 'notification_type']

    fieldsets = (
        (_('المستخدم'), {
            'fields': ('user', 'notification_type')
        }),
        (_('قنوات التنبيه'), {
            'fields': ('email_enabled', 'sms_enabled', 'browser_enabled')
        }),
        (_('توقيت الإرسال'), {
            'fields': ('send_immediately', 'send_daily_digest', 'send_weekly_digest')
        }),
        (_('التواريخ'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']


# ========================================
# QuickAction Admin
# ========================================
@admin.register(QuickAction)
class QuickActionAdmin(admin.ModelAdmin):
    list_display = [
        'title_ar',
        'action_type',
        'required_role',
        'order',
        'is_active',
        'icon_preview'
    ]
    list_filter = ['action_type', 'required_role', 'is_active']
    search_fields = ['title_ar', 'title_en', 'action_url']
    list_editable = ['order', 'is_active']

    fieldsets = (
        (_('المعلومات الأساسية'), {
            'fields': ('title_ar', 'title_en', 'description_ar', 'description_en')
        }),
        (_('الإعدادات'), {
            'fields': ('icon', 'color', 'action_type', 'action_url')
        }),
        (_('الصلاحيات'), {
            'fields': ('required_permission', 'required_role')
        }),
        (_('العرض'), {
            'fields': ('is_active', 'order')
        }),
        (_('التواريخ'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    def icon_preview(self, obj):
        return format_html(
            '<i class="{}" style="color:{}; font-size:20px;"></i>',
            obj.icon,
            obj.color
        )

    icon_preview.short_description = _('الأيقونة')


# ========================================
# ReportLog Admin
# ========================================
@admin.register(ReportLog)
class ReportLogAdmin(admin.ModelAdmin):
    list_display = [
        'report_type',
        'period_type',
        'generated_by',
        'records_count',
        'file_size_display',
        'created_at'
    ]
    list_filter = ['report_type', 'period_type', 'created_at']
    search_fields = ['file_name', 'generated_by__username']
    readonly_fields = [
        'report_type',
        'period_type',
        'generated_by',
        'date_from',
        'date_to',
        'user_filter',
        'file_name',
        'file_path',
        'file_size',
        'records_count',
        'created_at'
    ]
    date_hierarchy = 'created_at'

    fieldsets = (
        (_('معلومات التقرير'), {
            'fields': ('report_type', 'period_type', 'generated_by')
        }),
        (_('الفترة الزمنية'), {
            'fields': ('date_from', 'date_to', 'user_filter')
        }),
        (_('معلومات الملف'), {
            'fields': ('file_name', 'file_path', 'file_size', 'records_count')
        }),
        (_('التاريخ'), {
            'fields': ('created_at',)
        }),
    )

    def file_size_display(self, obj):
        return obj.get_file_size_display()

    file_size_display.short_description = _('حجم الملف')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ========================================
# تخصيص واجهة الإدارة
# ========================================
admin.site.site_header = "لوحة تحكم جمعية نسائم فلسطين"
admin.site.site_title = "Dashboard Admin"
admin.site.index_title = "إدارة لوحة التحكم"