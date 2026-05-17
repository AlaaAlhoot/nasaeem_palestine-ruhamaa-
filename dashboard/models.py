# dashboard/models.py

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.validators import MinValueValidator, MaxValueValidator
from django_ckeditor_5.fields import CKEditor5Field
import json
import io
import os
from django.core.files.base import ContentFile
from PIL import Image

def compress_image_field(image_field, quality=75, max_width=800):
    if not image_field or not hasattr(image_field, 'file'):
        return
    try:
        img = Image.open(image_field)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        if img.width > max_width:
            ratio = max_width / img.width
            img   = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        name = os.path.splitext(os.path.basename(image_field.name))[0] + '.jpg'
        image_field.save(name, ContentFile(output.read()), save=False)
    except Exception:
        pass


class UserProfile(models.Model):
    """الملفات الشخصية للمستخدمين"""

    ROLE_CHOICES = [
        ('super_admin', _('مدير عام')),
        ('admin',       _('إدارة')),
        ('editor',      _('محرر')),
        ('moderator',   _('مشرف')),
        ('viewer',      _('مشاهد')),
    ]

    THEME_CHOICES = [
        ('light', _('فاتح')),
        ('dark',  _('داكن')),
        ('auto',  _('تلقائي')),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='profile', verbose_name=_('المستخدم'))

    full_name_ar = models.CharField(_('الاسم الكامل بالعربية'),    max_length=100, blank=True)
    full_name_en = models.CharField(_('الاسم الكامل بالإنجليزية'), max_length=100, blank=True)
    avatar       = models.ImageField(_('الصورة الشخصية'), upload_to='profiles/avatars/',
                                     blank=True, null=True)
    phone = models.CharField(_('رقم الهاتف'), max_length=20, blank=True)
    bio   = models.TextField(_('نبذة شخصية'), max_length=500, blank=True)

    role            = models.CharField(_('الدور'),    max_length=20, choices=ROLE_CHOICES, default='viewer')
    department      = models.CharField(_('القسم'),    max_length=100, blank=True)
    is_active_staff = models.BooleanField(_('موظف نشط'), default=True)

    dashboard_theme     = models.CharField(_('سمة اللوحة'), max_length=20,
                                           choices=THEME_CHOICES, default='light')
    language_preference = models.CharField(_('اللغة المفضلة'), max_length=2,
                                           choices=[('ar', _('عربي')), ('en', _('إنجليزي'))],
                                           default='ar')
    items_per_page = models.PositiveIntegerField(_('عدد العناصر بالصفحة'), default=25)

    email_notifications   = models.BooleanField(_('إشعارات البريد الإلكتروني'), default=True)
    browser_notifications = models.BooleanField(_('إشعارات المتصفح'),           default=False)
    sms_notifications     = models.BooleanField(_('إشعارات الرسائل النصية'),    default=False)

    last_login_ip = models.GenericIPAddressField(_('آخر IP دخول'), blank=True, null=True)
    login_count   = models.PositiveIntegerField(_('عدد مرات الدخول'), default=0)
    last_activity = models.DateTimeField(_('آخر نشاط'), blank=True, null=True)

    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name        = _('الملف الشخصي')
        verbose_name_plural = _('الملفات الشخصية')
        ordering            = ['-created_at']

    def save(self, *args, **kwargs):
        # ضغط الصورة الشخصية قبل الحفظ
        if self.avatar and hasattr(self.avatar, 'file'):
            compress_image_field(self.avatar, quality=75, max_width=400)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    def get_display_name(self):
        return self.full_name_ar or self.user.get_full_name() or self.user.username

    def is_admin(self):
        return self.role in ['super_admin', 'admin']

    def can_edit_content(self):
        return self.role in ['super_admin', 'admin', 'editor']

    def update_last_activity(self):
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])

class ActivityLog(models.Model):
    """سجل الأنشطة"""

    ACTION_CHOICES = [
        ('create', _('إنشاء')),
        ('update', _('تحديث')),
        ('delete', _('حذف')),
        ('login', _('دخول')),
        ('logout', _('خروج')),
        ('view', _('مشاهدة')),
        ('export', _('تصدير')),
        ('backup', _('نسخ احتياطي')),
    ]

    LEVEL_CHOICES = [
        ('info', _('معلومات')),
        ('warning', _('تحذير')),
        ('error', _('خطأ')),
        ('success', _('نجح')),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                             null=True, blank=True, verbose_name=_('المستخدم'))
    username = models.CharField(_('اسم المستخدم'), max_length=150)

    action = models.CharField(_('الإجراء'), max_length=20, choices=ACTION_CHOICES)
    title = models.CharField(_('العنوان'), max_length=200)
    description = models.TextField(_('الوصف'))
    level = models.CharField(_('المستوى'), max_length=10, choices=LEVEL_CHOICES, default='info')

    ip_address = models.GenericIPAddressField(_('عنوان IP'), blank=True, null=True)
    user_agent = models.TextField(_('معلومات المتصفح'), blank=True, default='')
    session_key = models.CharField(_('مفتاح الجلسة'), max_length=40, blank=True, default='')

    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL,
                                     null=True, blank=True, verbose_name=_('نوع المحتوى'))
    object_id = models.CharField(_('معرف الكائن'), max_length=255, null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    extra_data = models.JSONField(_('بيانات إضافية'), default=dict, blank=True)
    timestamp = models.DateTimeField(_('وقت الحدث'), auto_now_add=True)

    class Meta:
        verbose_name = _('سجل النشاط')
        verbose_name_plural = _('سجل الأنشطة')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['level', 'timestamp']),
            # ── إضافات جديدة ──
            models.Index(fields=['timestamp']),
            models.Index(fields=['action']),
            models.Index(fields=['level']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.username} - {self.title}"

    @classmethod
    def log_activity(cls, user, action, title, description, content_object=None,
                     level='info', ip_address=None, user_agent=None, session_key=None, extra_data=None):
        return cls.objects.create(
            user=user,
            username=user.username if user else 'System',
            action=action,
            title=title,
            description=description,
            content_object=content_object,
            level=level,
            ip_address=ip_address or '',
            user_agent=user_agent or '',
            session_key=session_key or '',
            extra_data=extra_data or {}
        )


class SystemHealth(models.Model):
    """صحة النظام"""

    STATUS_CHOICES = [
        ('healthy', _('صحي')),
        ('warning', _('تحذير')),
        ('critical', _('حرج')),
        ('down', _('متوقف')),
    ]

    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='healthy')
    response_time = models.FloatField(_('وقت الاستجابة (ثانية)'), default=0)

    memory_usage_percent = models.FloatField(_('استخدام الذاكرة %'), default=0)
    memory_total = models.BigIntegerField(_('إجمالي الذاكرة (بايت)'), default=0)
    memory_used = models.BigIntegerField(_('الذاكرة المستخدمة (بايت)'), default=0)

    disk_usage_percent = models.FloatField(_('استخدام القرص %'), default=0)
    disk_total = models.BigIntegerField(_('إجمالي مساحة القرص (بايت)'), default=0)
    disk_used = models.BigIntegerField(_('المساحة المستخدمة (بايت)'), default=0)

    cpu_usage_percent = models.FloatField(_('استخدام المعالج %'), default=0)

    db_connections = models.PositiveIntegerField(_('اتصالات قاعدة البيانات'), default=0)
    db_query_time = models.FloatField(_('متوسط وقت الاستعلام (ثانية)'), default=0)

    active_users = models.PositiveIntegerField(_('المستخدمون النشطون'), default=0)
    errors_count = models.PositiveIntegerField(_('عدد الأخطاء'), default=0)
    warnings_count = models.PositiveIntegerField(_('عدد التحذيرات'), default=0)

    checked_at = models.DateTimeField(_('وقت الفحص'), auto_now_add=True)

    class Meta:
        verbose_name = _('صحة النظام')
        verbose_name_plural = _('فحوصات صحة النظام')
        ordering = ['-checked_at']

    def __str__(self):
        return f"صحة النظام - {self.get_status_display()} ({self.checked_at.strftime('%Y-%m-%d %H:%M')})"

    def is_healthy(self):
        return self.status == 'healthy'

    def get_status_color(self):
        colors = {
            'healthy': '#28a745',
            'warning': '#ffc107',
            'critical': '#fd7e14',
            'down': '#dc3545',
        }
        return colors.get(self.status, '#6c757d')


class NotificationSettings(models.Model):
    """إعدادات الإشعارات"""

    NOTIFICATION_TYPES = [
        ('new_message', _('رسالة جديدة')),
        ('new_project', _('مشروع جديد')),
        ('user_registration', _('تسجيل مستخدم جديد')),
        ('system_error', _('خطأ في النظام')),
        ('backup_completed', _('اكتمال النسخ الاحتياطي')),
        ('report_ready', _('التقرير جاهز')),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             verbose_name=_('المستخدم'))
    notification_type = models.CharField(_('نوع الإشعار'), max_length=50, choices=NOTIFICATION_TYPES)

    email_enabled = models.BooleanField(_('تفعيل البريد الإلكتروني'), default=True)
    sms_enabled = models.BooleanField(_('تفعيل الرسائل النصية'), default=False)
    browser_enabled = models.BooleanField(_('تفعيل إشعارات المتصفح'), default=True)

    send_immediately = models.BooleanField(_('إرسال فوري'), default=True)
    send_daily_digest = models.BooleanField(_('ملخص يومي'), default=False)
    send_weekly_digest = models.BooleanField(_('ملخص أسبوعي'), default=False)

    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('إعدادات الإشعار')
        verbose_name_plural = _('إعدادات الإشعارات')
        unique_together = ['user', 'notification_type']

    def __str__(self):
        return f"{self.user.username} - {self.get_notification_type_display()}"


class QuickAction(models.Model):
    """الإجراءات السريعة"""

    ACTION_TYPES = [
        ('link', _('رابط')),
        ('modal', _('نافذة منبثقة')),
        ('ajax', _('طلب Ajax')),
    ]

    title_ar = models.CharField(_('العنوان بالعربية'), max_length=100)
    title_en = models.CharField(_('العنوان بالإنجليزية'), max_length=100, blank=True)
    description_ar = models.CharField(_('الوصف بالعربية'), max_length=200, blank=True)
    description_en = models.CharField(_('الوصف بالإنجليزية'), max_length=200, blank=True)

    icon = models.CharField(_('أيقونة FontAwesome'), max_length=50, default='fas fa-cog')
    color = models.CharField(_('اللون'), max_length=7, default='#6B8E23')

    action_type = models.CharField(_('نوع الإجراء'), max_length=10, choices=ACTION_TYPES, default='link')
    action_url = models.CharField(_('رابط الإجراء'), max_length=200)

    required_permission = models.CharField(_('الصلاحية المطلوبة'), max_length=100, blank=True)
    required_role = models.CharField(_('الدور المطلوب'), max_length=20, blank=True)

    is_active = models.BooleanField(_('مفعل'), default=True)
    order = models.PositiveIntegerField(_('الترتيب'), default=0)

    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('إجراء سريع')
        verbose_name_plural = _('الإجراءات السريعة')
        ordering = ['order', 'title_ar']

    def __str__(self):
        return self.title_ar


class ReportLog(models.Model):
    """سجل التقارير المولدة"""

    REPORT_TYPES = [
        ('monthly_summary', _('التقرير الشهري')),
        ('projects_report', _('تقرير المشاريع')),
        ('users_activity', _('نشاط المستخدمين')),
        ('messages_report', _('تقرير الرسائل')),
        ('project_categories', _('فئات المشاريع')),
        ('statistics', _('الإحصائيات')),
        ('goals', _('الأهداف')),
        ('board_members', _('مجلس الإدارة')),
        ('faqs', _('الأسئلة الشائعة')),
        ('partners', _('الشركاء')),
        ('newsletters', _('الاشتراكات البريدية')),
        ('contact_messages', _('رسائل التواصل')),
        ('social_media', _('وسائل التواصل')),
        ('sliders', _('السلايدر')),
    ]

    PERIOD_TYPES = [
        ('monthly', _('شهري')),
        ('yearly', _('سنوي')),
        ('custom', _('مخصص')),
        ('all', _('كامل')),
    ]

    report_type = models.CharField(_('نوع التقرير'), max_length=50, choices=REPORT_TYPES)
    period_type = models.CharField(_('الفترة'), max_length=20, choices=PERIOD_TYPES, default='monthly')

    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, verbose_name=_('تم التوليد بواسطة'))

    date_from = models.DateField(_('من تاريخ'), null=True, blank=True)
    date_to = models.DateField(_('إلى تاريخ'), null=True, blank=True)

    user_filter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='filtered_reports',
                                    verbose_name=_('تصفية حسب المستخدم'))

    file_name = models.CharField(_('اسم الملف'), max_length=255)
    file_path = models.CharField(_('مسار الملف'), max_length=500)
    file_size = models.PositiveIntegerField(_('حجم الملف (بايت)'), default=0)
    records_count = models.PositiveIntegerField(_('عدد السجلات'), default=0)

    created_at = models.DateTimeField(_('تاريخ التوليد'), auto_now_add=True)

    class Meta:
        verbose_name = _('سجل تقرير')
        verbose_name_plural = _('سجل التقارير')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.created_at.strftime('%Y-%m-%d')}"

    def get_file_size_display(self):
        size = self.file_size
        if size < 1024:
            return f"{size} بايت"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size / (1024 * 1024):.2f} MB"


class SiteSetting(models.Model):
    """إعدادات الموقع"""

    site_name_ar = models.CharField('اسم الموقع بالعربية', max_length=200, default='جمعية نسائم فلسطين')
    site_name_en = models.CharField('اسم الموقع بالإنجليزية', max_length=200, default='Nasaeem Palestine')
    site_description = models.TextField('وصف الموقع', blank=True)
    site_email = models.EmailField('البريد الإلكتروني', default='info@nasaeem-palestine.org')
    site_phone = models.CharField('رقم الهاتف', max_length=20, blank=True)

    maintenance_mode = models.BooleanField('وضع الصيانة', default=False)
    maintenance_message_ar = models.TextField('رسالة الصيانة بالعربية', blank=True)
    maintenance_message_en = models.TextField('رسالة الصيانة بالإنجليزية', blank=True)

    enable_two_factor = models.BooleanField('المصادقة الثنائية', default=False)
    session_timeout = models.IntegerField('مهلة الجلسة (دقيقة)', default=30)
    max_login_attempts = models.IntegerField('محاولات الدخول القصوى', default=5)
    force_https = models.BooleanField('إجبار HTTPS', default=False)
    enable_ip_blocking = models.BooleanField('حظر IP تلقائي', default=False)

    cache_timeout = models.IntegerField('مهلة الكاش (ثانية)', default=3600)
    enable_compression = models.BooleanField('ضغط الملفات', default=True)
    enable_lazy_loading = models.BooleanField('التحميل الكسول', default=True)
    enable_minification = models.BooleanField('تصغير CSS/JS', default=False)

    auto_backup_enabled = models.BooleanField('تفعيل النسخ الاحتياطي التلقائي', default=True)
    backup_frequency_days = models.PositiveIntegerField('تكرار النسخ الاحتياطي (أيام)', default=7)
    keep_backups_count = models.PositiveIntegerField('عدد النسخ المحفوظة', default=30)

    daily_report_enabled = models.BooleanField('تفعيل التقرير اليومي', default=True)
    weekly_report_enabled = models.BooleanField('تفعيل التقرير الأسبوعي', default=True)
    admin_email_alerts = models.BooleanField('تنبيهات البريد للإدارة', default=True)

    updated_at = models.DateTimeField('آخر تحديث', auto_now=True)

    class Meta:
        verbose_name = 'إعدادات الموقع'
        verbose_name_plural = 'إعدادات الموقع'

    def __str__(self):
        return f"إعدادات {self.site_name_ar}"