from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db import models

from django_ckeditor_5.widgets import CKEditor5Widget
from .models import (
    ProjectCategory, Project, ProjectImage,
    ProjectVideo, ProjectDocument, ProjectLike
)


# Inline Classes
class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 1
    fields = ('image', 'title_ar', 'order', 'is_active')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover;" />', obj.image.url)
        return "لا توجد صورة"

    image_preview.short_description = _('معاينة')


class ProjectVideoInline(admin.TabularInline):
    model = ProjectVideo
    extra = 1
    fields = ('title_ar', 'youtube_url', 'order', 'is_active')


class ProjectDocumentInline(admin.TabularInline):
    model = ProjectDocument
    extra = 1
    fields = ('title_ar', 'document_type', 'file', 'is_public', 'is_active')


# Main Admin Classes
@admin.register(ProjectCategory)
class ProjectCategoryAdmin(admin.ModelAdmin):
    list_display = ['name_ar', 'projects_count', 'icon_preview', 'color_preview', 'order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name_ar', 'name_en', 'description_ar']
    prepopulated_fields = {'slug': ('name_ar',)}
    ordering = ['order', 'created_at']

    fieldsets = (
        (_('المعلومات الأساسية'), {
            'fields': ('name_ar', 'name_en', 'slug', 'description_ar', 'description_en')
        }),
        (_('المظهر'), {
            'fields': ('icon', 'color', 'image', 'order')
        }),
        (_('الإعدادات'), {
            'fields': ('is_active',)
        }),
    )

    def projects_count(self, obj):
        return obj.get_projects_count()

    projects_count.short_description = _('عدد المشاريع')

    def icon_preview(self, obj):
        return format_html('<i class="{}" style="font-size: 20px; color: {};"></i>', obj.icon, obj.color)

    icon_preview.short_description = _('الأيقونة')

    def color_preview(self, obj):
        return format_html(
            '<div style="width: 20px; height: 20px; background: {}; border-radius: 50%; display: inline-block;"></div>',
            obj.color
        )

    color_preview.short_description = _('اللون')

    actions = ['make_active', 'make_inactive']

    def make_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, _('تم تفعيل الفئات المحددة'))

    make_active.short_description = _('تفعيل الفئات المحددة')

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, _('تم إلغاء تفعيل الفئات المحددة'))

    make_inactive.short_description = _('إلغاء تفعيل الفئات المحددة')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = [
        'title_ar', 'category', 'status_colored', 'priority', 'progress_bar',
        'views_count', 'likes_count', 'is_featured', 'is_active', 'created_at'
    ]
    list_filter = ['status', 'priority', 'category', 'is_featured', 'is_active', 'created_at']
    search_fields = ['title_ar', 'title_en', 'description_ar', 'keywords_ar','keywords_en', 'location_ar']
    prepopulated_fields = {'slug': ('title_ar',)}
    ordering = ['-is_featured', '-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        (_('المعلومات الأساسية'), {
            'fields': ('title_ar', 'title_en', 'slug', 'category', 'main_image')
        }),
        (_('الوصف'), {
            'fields': ('summary_ar', 'summary_en', 'description_ar', 'description_en'),
            'classes': ('collapse',)
        }),
        (_('حالة المشروع'), {
            'fields': ('status', 'priority', 'start_date', 'end_date')
        }),
        (_('المعلومات المالية'), {
            'fields': ('target_amount', 'raised_amount', 'beneficiaries_count', 'target_beneficiaries')
        }),
        (_('الموقع والكلمات المفتاحية'), {
            'fields': ('location_ar', 'location_en', 'keywords_ar','keywords_en'),
            'classes': ('collapse',)
        }),
        (_('الإعدادات'), {
            'fields': ('is_featured', 'is_active', 'allow_comments')
        }),
        (_('تحسين محركات البحث'), {
            'fields': ('meta_description_ar', 'meta_description_en'),
            'classes': ('collapse',)
        }),
        (_('الإحصائيات'), {
            'fields': ('views_count', 'likes_count', 'shares_count'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('views_count', 'likes_count', 'shares_count', 'created_at', 'updated_at')

    formfield_overrides = {
        models.TextField: {'widget': CKEditor5Widget()},
    }

    inlines = [ProjectImageInline, ProjectVideoInline, ProjectDocumentInline]

    def status_colored(self, obj):
        color = obj.get_status_color()
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )

    status_colored.short_description = _('الحالة')

    def progress_bar(self, obj):
        progress = obj.get_progress_percentage()
        color = '#28a745' if progress >= 100 else '#17a2b8' if progress >= 50 else '#ffc107'
        return format_html(
            '<div style="width: 100px; height: 10px; background: #ddd; border-radius: 5px;">'
            '<div style="width: {}%; height: 100%; background: {}; border-radius: 5px;"></div>'
            '</div> <small>{}%</small>',
            min(progress, 100), color, int(progress)
        )

    progress_bar.short_description = _('التقدم')

    actions = ['make_featured', 'remove_featured', 'make_active', 'make_inactive']

    def make_featured(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, _('تم جعل المشاريع مميزة'))

    make_featured.short_description = _('جعل مميز')

    def remove_featured(self, request, queryset):
        queryset.update(is_featured=False)
        self.message_user(request, _('تم إلغاء تمييز المشاريع'))

    remove_featured.short_description = _('إلغاء التمييز')

    def make_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, _('تم تفعيل المشاريع'))

    make_active.short_description = _('تفعيل')

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, _('تم إلغاء تفعيل المشاريع'))

    make_inactive.short_description = _('إلغاء التفعيل')


@admin.register(ProjectImage)
class ProjectImageAdmin(admin.ModelAdmin):
    list_display = ['project', 'title_ar', 'image_preview', 'order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'project__category']
    search_fields = ['title_ar', 'project__title_ar']
    ordering = ['project', 'order', 'created_at']

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 60px; height: 60px; object-fit: cover; border-radius: 5px;" />',
                obj.image.url)
        return "لا توجد صورة"

    image_preview.short_description = _('المعاينة')


@admin.register(ProjectVideo)
class ProjectVideoAdmin(admin.ModelAdmin):
    list_display = ['project', 'title_ar', 'youtube_preview', 'order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'project__category']
    search_fields = ['title_ar', 'project__title_ar']
    ordering = ['project', 'order', 'created_at']

    def youtube_preview(self, obj):
        if obj.youtube_url:
            youtube_id = obj.get_youtube_id()
            if youtube_id:
                return format_html(
                    '<a href="{}" target="_blank"><i class="fab fa-youtube" style="color: #ff0000; font-size: 20px;"></i></a>',
                    obj.youtube_url
                )
        return "لا يوجد فيديو"

    youtube_preview.short_description = _('يوتيوب')


@admin.register(ProjectDocument)
class ProjectDocumentAdmin(admin.ModelAdmin):
    list_display = ['project', 'title_ar', 'document_type', 'file_info', 'download_count', 'is_public', 'is_active']
    list_filter = ['document_type', 'is_public', 'is_active', 'created_at', 'project__category']
    search_fields = ['title_ar', 'project__title_ar']
    ordering = ['-created_at']

    def file_info(self, obj):
        if obj.file:
            extension = obj.get_file_extension()
            size = obj.get_formatted_file_size()
            return f"{extension} ({size})"
        return "لا يوجد ملف"

    file_info.short_description = _('معلومات الملف')


@admin.register(ProjectLike)
class ProjectLikeAdmin(admin.ModelAdmin):
    list_display = ['project', 'ip_address', 'created_at']
    list_filter = ['created_at', 'project__category']
    search_fields = ['project__title_ar', 'ip_address']
    ordering = ['-created_at']
    readonly_fields = ['project', 'ip_address', 'user_agent', 'created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# # تخصيص عناوين لوحة الإدارة للمشاريع
# admin.site.register(ProjectCategory, ProjectCategoryAdmin)