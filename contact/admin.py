from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.forms import Textarea
from django.utils import timezone
from django.http import HttpResponse
import csv

from .models import ContactMessage, Newsletter, SocialMediaContact, ContactInfo, FAQ


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'name', 'email', 'subject', 'status_badge',
        'priority_badge', 'created_at', 'message_actions'
    ]
    list_filter = [
        'status', 'priority', 'created_at',
        ('replied_at', admin.DateFieldListFilter)
    ]
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'ip_address',
        'user_agent', 'message_preview'
    ]
    list_per_page = 20
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        (_('معلومات المرسل'), {
            'fields': ('name', 'email', 'phone')
        }),
        (_('محتوى الرسالة'), {
            'fields': ('subject', 'message_preview', 'attachment')
        }),
        (_('الإدارة'), {
            'fields': ('status', 'priority', 'reply_message', 'replied_by', 'replied_at'),
            'classes': ('collapse',)
        }),
        (_('معلومات تقنية'), {
            'fields': ('id', 'ip_address', 'user_agent', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 4, 'cols': 60})},
    }

    actions = [
        'mark_as_read', 'mark_as_replied', 'mark_as_closed',
        'set_high_priority', 'export_as_csv'
    ]

    def status_badge(self, obj):
        colors = {
            'new': '#28a745',
            'reading': '#17a2b8',
            'replied': '#6f42c1',
            'closed': '#6c757d'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = _('الحالة')

    def priority_badge(self, obj):
        colors = {
            'low': '#28a745',
            'normal': '#17a2b8',
            'high': '#ffc107',
            'urgent': '#dc3545'
        }
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            colors.get(obj.priority, '#17a2b8'),
            'white' if obj.priority in ['low', 'normal', 'urgent'] else 'black',
            obj.get_priority_display()
        )
    priority_badge.short_description = _('الأولوية')

    def message_preview(self, obj):
        if obj.message:
            preview = obj.message[:200] + '...' if len(obj.message) > 200 else obj.message
            return format_html('<div style="max-width: 400px;">{}</div>', preview)
        return '-'
    message_preview.short_description = _('معاينة الرسالة')

    def message_actions(self, obj):
        return format_html(
            '<a href="mailto:{}?subject=Re: {}" class="button" target="_blank">'
            '<i class="fas fa-reply"></i> رد</a>',
            obj.email, obj.subject
        )
    message_actions.short_description = _('إجراءات')

    # Custom Actions
    def mark_as_read(self, request, queryset):
        updated = queryset.update(status='reading')
        self.message_user(request, f'تم تحديد {updated} رسالة كمقروءة.')
    mark_as_read.short_description = _('تحديد كمقروءة')

    def mark_as_replied(self, request, queryset):
        updated = queryset.update(
            status='replied',
            replied_by=request.user,
            replied_at=timezone.now()
        )
        self.message_user(request, f'تم تحديد {updated} رسالة كتم الرد عليها.')
    mark_as_replied.short_description = _('تحديد كتم الرد عليها')

    def mark_as_closed(self, request, queryset):
        updated = queryset.update(status='closed')
        self.message_user(request, f'تم إغلاق {updated} رسالة.')
    mark_as_closed.short_description = _('إغلاق الرسائل')

    def set_high_priority(self, request, queryset):
        updated = queryset.update(priority='high')
        self.message_user(request, f'تم تعيين {updated} رسالة كأولوية عالية.')
    set_high_priority.short_description = _('أولوية عالية')

    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="contact_messages.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'الاسم', 'البريد الإلكتروني', 'الموضوع',
            'الحالة', 'الأولوية', 'تاريخ الإرسال'
        ])

        for obj in queryset:
            writer.writerow([
                obj.id, obj.name, obj.email, obj.subject,
                obj.get_status_display(), obj.get_priority_display(),
                obj.created_at.strftime('%Y-%m-%d %H:%M')
            ])

        return response
    export_as_csv.short_description = _('تصدير كـ CSV')


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = [
        'email', 'name', 'frequency_badge', 'status_badge',
        'confirmed_badge', 'subscribed_at', 'email_stats'
    ]
    list_filter = [
        'is_active', 'frequency', 'subscribed_at',
        ('confirmed_at', admin.DateFieldListFilter)
    ]
    search_fields = ['email', 'name']
    readonly_fields = [
        'confirmation_token', 'subscribed_at', 'updated_at',
        'ip_address', 'emails_sent', 'last_email_sent'
    ]
    list_per_page = 25
    date_hierarchy = 'subscribed_at'
    ordering = ['-subscribed_at']

    fieldsets = (
        (_('معلومات المشترك'), {
            'fields': ('email', 'name', 'is_active')
        }),
        (_('تفضيلات الاشتراك'), {
            'fields': ('frequency', 'topics', 'confirmed_at')
        }),
        (_('إحصائيات'), {
            'fields': ('emails_sent', 'last_email_sent'),
            'classes': ('collapse',)
        }),
        (_('معلومات تقنية'), {
            'fields': ('confirmation_token', 'ip_address', 'subscribed_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    actions = ['activate_subscriptions', 'deactivate_subscriptions', 'export_emails']

    def frequency_badge(self, obj):
        colors = {
            'daily': '#dc3545',
            'weekly': '#28a745',
            'monthly': '#17a2b8'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            colors.get(obj.frequency, '#6c757d'),
            obj.get_frequency_display()
        )
    frequency_badge.short_description = _('التكرار')

    def status_badge(self, obj):
        color = '#28a745' if obj.is_active else '#dc3545'
        status = 'نشط' if obj.is_active else 'غير نشط'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, status
        )
    status_badge.short_description = _('الحالة')

    def confirmed_badge(self, obj):
        if obj.is_confirmed:
            return format_html(
                '<span style="color: #28a745;"><i class="fas fa-check-circle"></i> مؤكد</span>'
            )
        return format_html(
            '<span style="color: #dc3545;"><i class="fas fa-times-circle"></i> غير مؤكد</span>'
        )
    confirmed_badge.short_description = _('التأكيد')

    def email_stats(self, obj):
        return format_html(
            '<div style="text-align: center;">'
            '<strong>{}</strong><br>'
            '<small style="color: #6c757d;">رسالة مرسلة</small>'
            '</div>',
            obj.emails_sent
        )
    email_stats.short_description = _('الإحصائيات')

    def activate_subscriptions(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'تم تفعيل {updated} اشتراك.')
    activate_subscriptions.short_description = _('تفعيل الاشتراكات')

    def deactivate_subscriptions(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'تم إلغاء تفعيل {updated} اشتراك.')
    deactivate_subscriptions.short_description = _('إلغاء تفعيل الاشتراكات')

    def export_emails(self, request, queryset):
        emails = [obj.email for obj in queryset if obj.is_active]
        response = HttpResponse('\n'.join(emails), content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="newsletter_emails.txt"'
        return response
    export_emails.short_description = _('تصدير البريد الإلكتروني')


@admin.register(SocialMediaContact)
class SocialMediaContactAdmin(admin.ModelAdmin):
    list_display = [
        'platform_badge', 'username', 'url_link', 'status_badge',
        'clicks_stats', 'order'
    ]
    list_filter = ['platform', 'is_active']
    search_fields = ['username', 'platform']
    list_editable = ['order']
    ordering = ['order', 'platform']

    fieldsets = (
        (_('معلومات المنصة'), {
            'fields': ('platform', 'username', 'url')
        }),
        (_('إعدادات العرض'), {
            'fields': ('is_active', 'icon_class', 'order')
        }),
        (_('إحصائيات'), {
            'fields': ('clicks_count',),
            'classes': ('collapse',)
        })
    )

    def platform_badge(self, obj):
        colors = {
            'facebook': '#1877f2',
            'twitter': '#1da1f2',
            'instagram': '#e4405f',
            'youtube': '#ff0000',
            'linkedin': '#0077b5',
            'telegram': '#0088cc',
            'whatsapp': '#25d366',
            'tiktok': '#000000'
        }
        return format_html(
            '<div style="display: flex; align-items: center;">'
            '<i class="{}" style="color: {}; margin-left: 8px; font-size: 16px;"></i>'
            '<span>{}</span>'
            '</div>',
            obj.get_icon_class(),
            colors.get(obj.platform, '#6c757d'),
            obj.get_platform_display()
        )
    platform_badge.short_description = _('المنصة')

    def url_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank" class="button">زيارة الرابط</a>',
            obj.url
        )
    url_link.short_description = _('الرابط')

    def status_badge(self, obj):
        color = '#28a745' if obj.is_active else '#dc3545'
        status = 'نشط' if obj.is_active else 'غير نشط'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, status
        )
    status_badge.short_description = _('الحالة')

    def clicks_stats(self, obj):
        return format_html(
            '<div style="text-align: center;">'
            '<strong style="color: #17a2b8;">{}</strong><br>'
            '<small style="color: #6c757d;">نقرة</small>'
            '</div>',
            obj.clicks_count
        )
    clicks_stats.short_description = _('النقرات')




from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
# من المفترض أن تقوم باستيراد ContactInfo من مكانها الصحيح
# from .models import ContactInfo

@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = [
        'type_ar',
        'type_badge',
        'value_preview', # ✅ تم تعديل الدالة لتعرض value_ar
        'footer_badge',
        'status_badge',
        'order'
    ]

    list_filter = ['type', 'is_active', 'show_in_footer']

    # ✅ التعديل: البحث في الحقول الثنائية اللغة
    search_fields = ['type_ar', 'value_ar', 'value_en']

    list_editable = ['order']
    ordering = ['order', 'type']

    fieldsets = (
        (_('المعلومات الأساسية'), {
            # ✅ التعديل: استبدال 'value' بـ 'value_ar' و 'value_en'
            'fields': ('type', 'value_ar', 'value_en')
        }),
        (_('إعدادات العرض'), {
            'fields': (
                'is_active',
                'show_in_footer',
                'icon_class',
                'order'
            )
        })
    )

    # دالة لعرض النوع كشارة (Badge)
    def type_badge(self, obj):
        colors = {
            'phone': '#28a745', 'email': '#17a2b8', 'address': '#dc3545',
            'fax': '#6f42c1', 'po_box': '#fd7e14', 'website': '#20c997'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            colors.get(obj.type, '#6c757d'),
            obj.type_ar
        )

    type_badge.short_description = _('النوع')

    # ✅ التعديل: استخدام value_ar كمعاينة
    def value_preview(self, obj):
        # استخدام value_ar كقيمة للمعاينة
        value = obj.value_ar
        preview = value[:50] + '...' if len(value) > 50 else value
        return format_html('<div style="max-width: 200px;">{}</div>', preview)

    value_preview.short_description = _('القيمة (عربي)')

    # دالة جديدة لعرض حالة التذييل فقط
    def footer_badge(self, obj):
        if obj.show_in_footer:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 2px 6px; border-radius: 8px; font-size: 10px;">{}</span>',
                _('في التذييل')
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; padding: 2px 6px; border-radius: 8px; font-size: 10px;">{}</span>',
            _('لا يعرض')
        )

    footer_badge.short_description = _('موقع العرض')

    def status_badge(self, obj):
        color = '#28a745' if obj.is_active else '#dc3545'
        status = _('نشط') if obj.is_active else _('غير نشط')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, status
        )

    status_badge.short_description = _('الحالة')


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = [
        'question_preview', 'category_badge', 'status_badge',
        'stats_display', 'order'
    ]
    list_filter = ['is_active', 'category']
    search_fields = ['question_ar', 'question_en', 'answer_ar', 'answer_en', 'tags']
    list_editable = ['order']
    ordering = ['order', '-views_count']

    fieldsets = (
        (_('الأسئلة'), {
            'fields': ('question_ar', 'question_en')
        }),
        (_('الإجابات'), {
            'fields': ('answer_ar', 'answer_en')
        }),
        (_('التصنيف'), {
            'fields': ('category', 'tags')
        }),
        (_('إعدادات'), {
            'fields': ('is_active', 'order')
        }),
        (_('إحصائيات'), {
            'fields': ('views_count', 'helpful_votes'),
            'classes': ('collapse',)
        })
    )

    def question_preview(self, obj):
        preview = obj.question_ar[:100] + '...' if len(obj.question_ar) > 100 else obj.question_ar
        return format_html('<div style="max-width: 300px; font-weight: bold;">{}</div>', preview)
    question_preview.short_description = _('السؤال')

    def category_badge(self, obj):
        if obj.category:
            return format_html(
                '<span style="background-color: #6f42c1; color: white; padding: 3px 8px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
                obj.category
            )
        return '-'
    category_badge.short_description = _('الفئة')

    def status_badge(self, obj):
        color = '#28a745' if obj.is_active else '#dc3545'
        status = 'نشط' if obj.is_active else 'غير نشط'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, status
        )
    status_badge.short_description = _('الحالة')

    def stats_display(self, obj):
        return format_html(
            '<div style="text-align: center;">'
            '<div><strong style="color: #17a2b8;">{}</strong> <small>مشاهدة</small></div>'
            '<div><strong style="color: #28a745;">{}</strong> <small>مفيد</small></div>'
            '</div>',
            obj.views_count, obj.helpful_votes
        )
    stats_display.short_description = _('الإحصائيات')


# تخصيص واجهة الإدارة
admin.site.site_header = "إدارة جمعية نسائم فلسطين الخيرية"
admin.site.site_title = "نسائم فلسطين"
admin.site.index_title = "لوحة التحكم - قسم التواصل"