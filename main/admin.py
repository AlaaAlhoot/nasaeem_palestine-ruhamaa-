# main/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    SiteSettings, AboutPage, VisionPage, Goal, BoardMember,
    HomeSlider, Statistic,
)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """إدارة إعدادات الموقع"""

    list_display = ['site_name_ar', 'phone', 'email', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('site_name_ar', 'site_name_en', 'logo', 'favicon', 'default_image')
        }),
        (_('معلومات الاتصال'), {
            'fields': ('phone', 'whatsapp_number', 'email', 'address_ar', 'address_en')
        }),
        (_('الموقع الجغرافي'), {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        (_('وسائل التواصل الاجتماعي'), {
            'fields': ('facebook_url', 'twitter_url', 'instagram_url', 'tiktok_url', 'youtube_url'),
            'classes': ('collapse',)
        }),
        (_('معلومات الجمعية'), {
            'fields': ('about_summary_ar', 'about_summary_en', 'established_year')
        }),
        (_('الإحصائيات'), {
            'fields': ('total_projects', 'total_beneficiaries', 'total_donations'),
            'classes': ('collapse',)
        }),
        (_('التواريخ'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        # السماح بإنشاء إعدادات واحدة فقط
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # منع حذف الإعدادات
        return False


@admin.register(HomeSlider)
class HomeSliderAdmin(admin.ModelAdmin):
    """إدارة شرائح السلايدر"""

    list_display = ['title_ar', 'order', 'is_active', 'image_preview', 'created_at']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title_ar', 'title_en', 'subtitle_ar', 'description_ar']
    ordering = ['order', '-created_at']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (_('المحتوى الأساسي'), {
            'fields': ('title_ar', 'title_en', 'subtitle_ar', 'subtitle_en',
                       'description_ar', 'description_en', 'image')
        }),
        (_('زر الإجراء'), {
            'fields': ('button_text_ar', 'button_text_en', 'button_url'),
            'classes': ('collapse',)
        }),
        (_('إعدادات العرض'), {
            'fields': ('order', 'is_active')
        }),
    )

    def image_preview(self, obj):
        """عرض معاينة الصورة"""
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 80px; height: 45px; object-fit: cover; border-radius: 4px;" />',
                obj.image.url
            )
        return '-'

    image_preview.short_description = _('معاينة الصورة')


@admin.register(Statistic)
class StatisticAdmin(admin.ModelAdmin):
    """إدارة الإحصائيات"""

    list_display = ['title_ar', 'number', 'suffix_ar', 'icon_preview', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active', 'auto_update_from', 'created_at']
    search_fields = ['title_ar', 'title_en']
    ordering = ['order', '-created_at']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (_('المحتوى'), {
            'fields': ('title_ar', 'title_en', 'number', 'suffix_ar', 'suffix_en')
        }),
        (_('التصميم'), {
            'fields': ('icon', 'color')
        }),
        (_('الإعدادات'), {
            'fields': ('order', 'auto_update_from', 'is_active')
        }),
    )

    def icon_preview(self, obj):
        """عرض معاينة الأيقونة"""
        return format_html(
            '<i class="{}" style="color: {}; font-size: 24px;"></i>',
            obj.icon, obj.color
        )

    icon_preview.short_description = _('الأيقونة')


@admin.register(AboutPage)
class AboutPageAdmin(admin.ModelAdmin):
    """إدارة صفحة من نحن"""

    list_display = ['title_ar', 'is_active', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (_('المحتوى'), {
            'fields': ('title_ar', 'title_en', 'content_ar', 'content_en', 'image')
        }),
        (_('SEO'), {
            'fields': ('meta_description_ar', 'meta_description_en'),
            'classes': ('collapse',)
        }),
        (_('الإعدادات'), {
            'fields': ('is_active',)
        }),
    )

    def has_add_permission(self, request):
        # السماح بإنشاء صفحة واحدة فقط
        return not AboutPage.objects.exists()


@admin.register(VisionPage)
class VisionPageAdmin(admin.ModelAdmin):
    """إدارة صفحة الرؤية والرسالة"""

    list_display = ['vision_title_ar', 'mission_title_ar', 'values_title_ar', 'is_active', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (_('الرؤية'), {
            'fields': ('vision_title_ar', 'vision_title_en',
                       'vision_content_ar', 'vision_content_en', 'vision_image')
        }),
        (_('الرسالة'), {
            'fields': ('mission_title_ar', 'mission_title_en',
                       'mission_content_ar', 'mission_content_en', 'mission_image')
        }),
        (_('القيم'), {
            'fields': ('values_title_ar', 'values_title_en',
                       'values_content_ar', 'values_content_en', 'values_image')
        }),
        (_('SEO'), {
            'fields': ('meta_description_ar', 'meta_description_en'),
            'classes': ('collapse',)
        }),
        (_('الإعدادات'), {
            'fields': ('is_active',)
        }),
    )

    def has_add_permission(self, request):
        return not VisionPage.objects.exists()


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    """إدارة الأهداف"""

    list_display = ['title_ar', 'icon_preview', 'order', 'is_active', 'created_at']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title_ar', 'title_en', 'description_ar', 'description_en']
    ordering = ['order', '-created_at']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (_('المحتوى'), {
            'fields': ('title_ar', 'title_en', 'description_ar', 'description_en')
        }),
        (_('التصميم'), {
            'fields': ('icon',)
        }),
        (_('الإعدادات'), {
            'fields': ('order', 'is_active')
        }),
    )

    def icon_preview(self, obj):
        """عرض معاينة الأيقونة"""
        return format_html(
            '<i class="{}" style="font-size: 24px; color: #6B8E23;"></i>',
            obj.icon
        )

    icon_preview.short_description = _('الأيقونة')


from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import BoardMember


@admin.register(BoardMember)
class BoardMemberAdmin(admin.ModelAdmin):
    """إدارة أعضاء مجلس الإدارة"""

    list_display = [
        'name_ar',
        'position_type_ar',  # ✅ تغيير من position_ar
        'position_type',
        'is_custom_position',  # ✅ جديد
        'photo_preview',
        'order',
        'is_active'
    ]

    list_editable = ['order', 'is_active']

    list_filter = [
        'position_type',
        'is_custom_position',  # ✅ جديد
        'is_active',
        'created_at'
    ]

    search_fields = [
        'name_ar',
        'name_en',
        'position_type_ar',  # ✅ تغيير من position_ar
        'position_type_en',  # ✅ تغيير من position_en
        'bio_ar',
        'bio_en',  # ✅ جديد
        'email'
    ]

    ordering = ['order', '-created_at']

    readonly_fields = ['created_at', 'updated_at', 'photo_preview_large']

    fieldsets = (
        (_('المعلومات الأساسية'), {
            'fields': ('name_ar', 'name_en')
        }),
        (_('المنصب'), {
            'fields': (
                'is_custom_position',  # ✅ جديد
                'position_type',
                'position_type_ar',  # ✅ تغيير من position_ar
                'position_type_en'  # ✅ تغيير من position_en
            ),
            'description': 'فعّل "منصب مخصص" لكتابة منصب غير موجود في القائمة'
        }),
        (_('الصورة الشخصية'), {
            'fields': ('photo', 'photo_preview_large')
        }),
        (_('النبذة الشخصية'), {
            'fields': ('bio_ar', 'bio_en'),  # ✅ إضافة bio_en
            'classes': ('collapse',)
        }),
        (_('معلومات الاتصال'), {
            'fields': ('email', 'phone'),
            'classes': ('collapse',)
        }),
        (_('وسائل التواصل الاجتماعي'), {
            'fields': ('facebook_url', 'twitter_url', 'linkedin_url'),
            'classes': ('collapse',)
        }),
        (_('إعدادات العرض'), {
            'fields': ('order', 'is_active')
        }),
        (_('معلومات النظام'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def photo_preview(self, obj):
        """عرض معاينة الصورة الشخصية - صغيرة"""
        if obj.photo:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover;" />',
                obj.photo.url
            )
        return format_html(
            '<div style="width: 50px; height: 50px; border-radius: 50%; background: #e9ecef; '
            'display: flex; align-items: center; justify-content: center;">'
            '<span style="color: #6c757d;">👤</span></div>'
        )

    photo_preview.short_description = _('الصورة')

    def photo_preview_large(self, obj):
        """عرض معاينة الصورة الشخصية - كبيرة"""
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px; border-radius: 10px; object-fit: cover;" />',
                obj.photo.url
            )
        return format_html(
            '<div style="width: 200px; height: 200px; border-radius: 10px; background: #e9ecef; '
            'display: flex; align-items: center; justify-content: center;">'
            '<span style="font-size: 48px; color: #6c757d;">👤</span></div>'
        )

    photo_preview_large.short_description = _('معاينة الصورة')

    def save_model(self, request, obj, form, change):
        """حفظ مع معالجة المنصب"""
        # إذا كان منصباً مخصصاً، تأكد من وجود القيم
        if obj.is_custom_position:
            if not obj.position_type_ar or not obj.position_type_en:
                from django.contrib import messages
                messages.error(request, 'يجب إدخال المنصب بالعربية والإنجليزية للمناصب المخصصة')
                return
        else:
            # إذا كان من القائمة، املأ الحقول تلقائياً
            if obj.position_type:
                position_arabic = {
                    'president': 'رئيس مجلس الإدارة',
                    'vice_president': 'نائب الرئيس',
                    'secretary': 'السكرتير',
                    'treasurer': 'أمين الصندوق',
                    'member': 'عضو'
                }
                position_english = {
                    'president': 'President of the Board',
                    'vice_president': 'Vice President',
                    'secretary': 'Secretary',
                    'treasurer': 'Treasurer',
                    'member': 'Member'
                }
                obj.position_type_ar = position_arabic.get(obj.position_type, 'عضو')
                obj.position_type_en = position_english.get(obj.position_type, 'Member')

        super().save_model(request, obj, form, change)

    class Media:
        css = {
            'all': ('admin/css/custom_board.css',)
        }




# تخصيص عنوان صفحة الإدارة
admin.site.site_header = "إدارة جمعية نسائم فلسطين"
admin.site.site_title = "لوحة الإدارة"
admin.site.index_title = "إدارة محتوى الموقع"