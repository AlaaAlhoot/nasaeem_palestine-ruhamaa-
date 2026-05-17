# contact/models.py
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import EmailValidator
from django.conf import settings
from phonenumber_field.modelfields import PhoneNumberField

class ContactMessage(models.Model):
    """نموذج رسائل التواصل"""
    STATUS_CHOICES = [
        ('new', _('جديدة')),
        ('reading', _('قيد القراءة')),
        ('replied', _('تم الرد')),
        ('closed', _('مغلقة')),
    ]

    PRIORITY_CHOICES = [
        ('low', _('منخفضة')),
        ('normal', _('عادية')),
        ('high', _('عالية')),
        ('urgent', _('عاجلة')),
    ]

    # بيانات المرسل
    name = models.CharField(_('الاسم'), max_length=100)
    email = models.EmailField(_('البريد الإلكتروني'), validators=[EmailValidator()])
    phone = PhoneNumberField(_('رقم الهاتف'), blank=True, null=True)

    # محتوى الرسالة
    subject = models.CharField(_('الموضوع'), max_length=200)
    message = models.TextField(_('الرسالة'))
    attachment = models.FileField(_('مرفق'), upload_to='contact_attachments/', blank=True, null=True)

    # معلومات إدارية
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='new')
    priority = models.CharField(_('الأولوية'), max_length=20, choices=PRIORITY_CHOICES, default='normal')

    # بيانات تقنية
    ip_address = models.GenericIPAddressField(_('عنوان IP'), blank=True, null=True)
    user_agent = models.TextField(_('متصفح المستخدم'), blank=True, null=True)

    # الرد
    reply_message = models.TextField(_('الرد'), blank=True, null=True)
    replied_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name=_('تم الرد بواسطة'))
    replied_at = models.DateTimeField(_('تاريخ الرد'), blank=True, null=True)

    # التوقيتات
    created_at = models.DateTimeField(_('تاريخ الإرسال'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('رسالة تواصل')
        verbose_name_plural = _('رسائل التواصل')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['email']),
            # ── إضافات جديدة ──
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.name} - {self.subject}"

    def mark_as_read(self):
        """تحديد الرسالة كمقروءة"""
        if self.status == 'new':
            self.status = 'reading'
            self.save(update_fields=['status', 'updated_at'])

    def mark_as_replied(self, user, reply_text):
        """تحديد الرسالة كتم الرد عليها"""
        self.status = 'replied'
        self.reply_message = reply_text
        self.replied_by = user
        self.replied_at = timezone.now()
        self.save(update_fields=['status', 'reply_message', 'replied_by', 'replied_at', 'updated_at'])

    @property
    def is_new(self):
        return self.status == 'new'

    @property
    def is_urgent(self):
        return self.priority == 'urgent'
class SocialMediaContact(models.Model):
    """نموذج روابط التواصل الاجتماعي"""

    PLATFORM_CHOICES = [
        ('facebook', _('فيسبوك')),
        ('twitter', _('تويتر / X')),
        ('instagram', _('انستقرام')),
        ('linkedin', _('لينكد إن')),
        ('youtube', _('يوتيوب')),
        ('tiktok', _('تيك توك')),
        ('snapchat', _('سناب شات')),
        ('whatsapp', _('واتساب')),
        ('telegram', _('تليجرام')),
        ('pinterest', _('بينترست')),
        ('github', _('جيت هاب')),
        ('discord', _('ديسكورد')),
    ]

    # قاموس ربط المنصات بأيقوناتها
    PLATFORM_ICONS = {
        'facebook': 'fab fa-facebook',
        'twitter': 'fa-brands fa-x-twitter',
        'instagram': 'fab fa-instagram',
        'linkedin': 'fab fa-linkedin',
        'youtube': 'fab fa-youtube',
        'tiktok': 'fab fa-tiktok',
        'snapchat': 'fab fa-snapchat',
        'whatsapp': 'fab fa-whatsapp',
        'telegram': 'fab fa-telegram',
        'pinterest': 'fab fa-pinterest',
        'github': 'fab fa-github',
        'discord': 'fab fa-discord',
    }

    platform = models.CharField(_('المنصة'), max_length=50, choices=PLATFORM_CHOICES, unique=True)
    username = models.CharField(_('اسم المستخدم'), max_length=200)
    url = models.URLField(_('رابط الحساب'), max_length=500)
    icon_class = models.CharField(_('أيقونة'), max_length=100, blank=True)
    order = models.PositiveIntegerField(_('الترتيب'), default=0)
    is_active = models.BooleanField(_('مفعّل'), default=True)
    clicks_count = models.PositiveIntegerField(_('عدد النقرات'), default=0)
    created_at = models.DateTimeField(_('تاريخ الإضافة'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('رابط تواصل اجتماعي')
        verbose_name_plural = _('روابط التواصل الاجتماعي')
        ordering = ['order', 'platform']

    def __str__(self):
        return f"{self.get_platform_display()} - {self.username}"

    def save(self, *args, **kwargs):
        # تعيين الأيقونة تلقائياً بناءً على المنصة إذا لم تكن محددة
        if not self.icon_class:
            self.icon_class = self.PLATFORM_ICONS.get(self.platform, 'fas fa-link')
        super().save(*args, **kwargs)

    def get_icon_class(self):
        """الحصول على أيقونة المنصة"""
        return self.icon_class or self.PLATFORM_ICONS.get(self.platform, 'fas fa-link')

    @classmethod
    def get_available_platforms(cls):
        """الحصول على المنصات المتاحة التي لم يتم إضافتها"""
        used_platforms = cls.objects.values_list('platform', flat=True)
        available = [(p, label) for p, label in cls.PLATFORM_CHOICES if p not in used_platforms]
        return available
class Category(models.Model):
    category_ar = models.CharField(_('الاسم بالعربية'), max_length=100)
    category_en = models.CharField(_('الاسم بالإنجليزية'), max_length=100, blank=True)

    def __str__(self):
        return self.category_ar
class FAQ(models.Model):
    """الأسئلة الشائعة"""

    # السؤال
    question_ar = models.TextField(_('السؤال (عربي)'))
    question_en = models.TextField(_('السؤال (إنجليزي)'), blank=True)

    # الإجابة
    answer_ar = models.TextField(_('الإجابة (عربي)'))
    answer_en = models.TextField(_('الإجابة (إنجليزي)'), blank=True)

    # التصنيف من جدول مستقل
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('التصنيف'))

    # العلامات بلغتين
    tags_ar = models.CharField(_('العلامات (عربي)'), max_length=200, blank=True, help_text=_('افصل العلامات بفاصلة'))
    tags_en = models.CharField(_('العلامات (إنجليزي)'), max_length=200, blank=True, help_text=_('Separate tags with commas'))

    # إعدادات العرض
    is_active = models.BooleanField(_('مفعل'), default=True)
    order = models.PositiveIntegerField(_('الترتيب'), default=0)

    # الإحصائيات
    views_count = models.PositiveIntegerField(_('عدد المشاهدات'), default=0)
    helpful_votes = models.PositiveIntegerField(_('تصويتات مفيد'), default=0)

    # التوقيتات
    created_at = models.DateTimeField(_('تاريخ الإضافة'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('سؤال شائع')
        verbose_name_plural = _('الأسئلة الشائعة')
        ordering = ['order', '-views_count']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['is_active', 'order']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['-views_count']),
        ]

    def __str__(self):
        return self.question_ar[:100]
from django.db import models
from django.utils.translation import gettext_lazy as _
class ContactInfo(models.Model):
    """معلومات التواصل الرئيسية"""

    FULL_INFO_TYPES = [
        ('phone', _('هاتف'), 'Phone', 'fas fa-phone'),
        ('email', _('بريد إلكتروني'), 'Email', 'fas fa-envelope'),
        ('address', _('عنوان'), 'Address', 'fas fa-map-marker-alt'),
        ('fax', _('فاكس'), 'Fax', 'fas fa-fax'),
        ('po_box', _('صندوق بريد'), 'PO Box', 'fas fa-mailbox'),
        ('website', _('موقع إلكتروني'), 'Website', 'fas fa-globe'),
    ]

    # قائمة choices لحقل type (تستخدم القيمة الداخلية والتسمية العربية)
    INFO_TYPES = [(item[0], item[1]) for item in FULL_INFO_TYPES]

    type = models.CharField(_('النوع'), max_length=20, choices=INFO_TYPES, unique=True)

    # الحقول الجديدة للتسمية العربية والإنجليزية (تعبأ تلقائياً)
    type_ar = models.CharField(_('التسمية العربية'), max_length=100, blank=True)
    type_en = models.CharField(_('التسمية الإنجليزية'), max_length=100, blank=True)

    value_ar = models.TextField(_('القيمة بالعربية'))
    value_en= models.TextField(_('القيمة بالانجليزية'))

    # إعدادات العرض
    is_active = models.BooleanField(_('مفعل'), default=True)
    # show_in_header تم حذفه
    show_in_footer = models.BooleanField(_('عرض في التذييل'), default=True)
    icon_class = models.CharField(_('كلاس الأيقونة'), max_length=50, blank=True)
    order = models.PositiveIntegerField(_('الترتيب'), default=0)

    # التوقيتات
    created_at = models.DateTimeField(_('تاريخ الإضافة'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('معلومات التواصل')
        verbose_name_plural = _('معلومات التواصل')
        ordering = ['order', 'type']

    def __str__(self):
        # استخدام التسمية العربية الجديدة
        return f"{self.type_ar or self.type} - {self.value}"

    def save(self, *args, **kwargs):
        """تعبئة type_ar و type_en تلقائياً عند الحفظ"""
        # البحث عن التسميات بناءً على النوع المختار
        type_data = next((item for item in self.FULL_INFO_TYPES if item[0] == self.type), None)

        if type_data:
            self.type_ar = str(type_data[1])  # التسمية العربية
            self.type_en = type_data[2]  # التسمية الإنجليزية
            # تعبئة icon_class افتراضياً إذا كان فارغاً عند الإضافة
            if not self.icon_class and not self.pk:
                self.icon_class = type_data[3]

        super().save(*args, **kwargs)

    def get_icon_class(self):
        """الحصول على كلاس الأيقونة (يعتمد الآن على الحقل icon_class الذي أصبح مطلوباً تعبئته)"""
        if self.icon_class:
            return self.icon_class
        # fallback - (يمكن حذفه إذا كان icon_class دائماً معبأً في save)
        return 'fas fa-info-circle'
class Newsletter(models.Model):
    """نموذج الاشتراك في النشرة البريدية"""

    email = models.EmailField(_('البريد الإلكتروني'), unique=True, validators=[EmailValidator()])
    name  = models.CharField(_('الاسم'), max_length=100, blank=True)

    # تفضيلات الاشتراك
    is_active = models.BooleanField(_('مفعل'), default=True)
    topics    = models.JSONField(_('المواضيع المفضلة'), default=list, blank=True)
    frequency = models.CharField(_('تكرار الإرسال'), max_length=20,
                                 choices=[
                                     ('daily',   _('يومي')),
                                     ('weekly',  _('أسبوعي')),
                                     ('monthly', _('شهري')),
                                 ], default='weekly')

    # بيانات تقنية
    ip_address         = models.GenericIPAddressField(_('عنوان IP'), blank=True, null=True)
    confirmation_token = models.CharField(_('رمز التأكيد'), max_length=100, blank=True)
    confirmed_at       = models.DateTimeField(_('تاريخ التأكيد'), blank=True, null=True)

    # إحصائيات الإرسال
    emails_sent        = models.PositiveIntegerField(_('إجمالي الرسائل المرسلة'), default=0)
    daily_sent         = models.PositiveIntegerField(_('رسائل يومية مرسلة'),     default=0)
    weekly_sent        = models.PositiveIntegerField(_('رسائل أسبوعية مرسلة'),   default=0)
    monthly_sent       = models.PositiveIntegerField(_('رسائل شهرية مرسلة'),     default=0)
    last_email_sent    = models.DateTimeField(_('آخر رسالة'), blank=True, null=True)

    # تتبع إلغاء الاشتراك
    unsubscribed_at    = models.DateTimeField(_('تاريخ إلغاء الاشتراك'), blank=True, null=True)
    unsubscribe_reason = models.CharField(_('سبب الإلغاء'), max_length=200, blank=True)

    # التوقيتات
    subscribed_at = models.DateTimeField(_('تاريخ الاشتراك'), auto_now_add=True)
    updated_at    = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name        = _('اشتراك في النشرة')
        verbose_name_plural = _('اشتراكات النشرة البريدية')
        ordering            = ['-subscribed_at']
        indexes             = [
            models.Index(fields=['email', 'is_active']),
            models.Index(fields=['is_active', 'frequency']),
            models.Index(fields=['is_active']),
            models.Index(fields=['confirmed_at']),
            models.Index(fields=['subscribed_at']),
            models.Index(fields=['frequency']),
        ]

    def __str__(self):
        return f"{self.email} ({self.get_frequency_display()})"

    @property
    def is_confirmed(self):
        return self.confirmed_at is not None

    def confirm_subscription(self):
        """تأكيد الاشتراك"""
        self.confirmed_at = timezone.now()
        self.save(update_fields=['confirmed_at', 'updated_at'])

    def unsubscribe(self, reason=''):
        """إلغاء الاشتراك مع تسجيل التوقيت"""
        self.is_active        = False
        self.unsubscribed_at  = timezone.now()
        self.unsubscribe_reason = reason
        self.save(update_fields=['is_active', 'unsubscribed_at', 'unsubscribe_reason', 'updated_at'])

    def increment_sent(self, frequency_type):
        """زيادة عداد الإرسال حسب النوع"""
        self.emails_sent += 1
        self.last_email_sent = timezone.now()
        if frequency_type == 'daily':
            self.daily_sent += 1
        elif frequency_type == 'weekly':
            self.weekly_sent += 1
        elif frequency_type == 'monthly':
            self.monthly_sent += 1
        elif frequency_type in ('manual', 'project'):
            # الإرسال اليدوي يزيد كل العدادات
            self.daily_sent += 1
            self.weekly_sent += 1
            self.monthly_sent += 1
        self.save(update_fields=[
            'emails_sent', 'last_email_sent',
            'daily_sent', 'weekly_sent', 'monthly_sent', 'updated_at'
        ])


# ==================== سجل النشرة ====================

class NewsletterLog(models.Model):
    """سجل عمليات إرسال النشرة البريدية"""

    TYPE_CHOICES = [
        ('daily',   _('يومي')),
        ('weekly',  _('أسبوعي')),
        ('monthly', _('شهري')),
        ('manual',  _('يدوي')),
        ('project', _('مشروع جديد')),
    ]

    STATUS_CHOICES = [
        ('success', _('نجح')),
        ('failed',  _('فشل')),
        ('partial', _('جزئي')),
    ]

    send_type     = models.CharField(_('نوع الإرسال'), max_length=10, choices=TYPE_CHOICES)
    status        = models.CharField(_('الحالة'),      max_length=10, choices=STATUS_CHOICES)
    sent_by       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                      null=True, blank=True, verbose_name=_('بواسطة'))
    is_auto       = models.BooleanField(_('تلقائي'), default=True)
    total_sent    = models.PositiveIntegerField(_('عدد المرسل لهم'), default=0)
    total_failed  = models.PositiveIntegerField(_('عدد الفاشلة'),    default=0)
    unsubscribed  = models.PositiveIntegerField(_('إلغاء الاشتراك'), default=0)
    error_message = models.TextField(_('رسالة الخطأ'), blank=True)
    period_from   = models.DateTimeField(_('من'), null=True, blank=True)
    period_to     = models.DateTimeField(_('إلى'), null=True, blank=True)
    created_at    = models.DateTimeField(_('وقت الإرسال'), auto_now_add=True)

    class Meta:
        verbose_name        = _('سجل نشرة')
        verbose_name_plural = _('سجلات النشرة')
        ordering            = ['-created_at']
        indexes             = [
            models.Index(fields=['send_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'{self.get_send_type_display()} — {self.created_at:%Y-%m-%d %H:%M}'


# ==================== إعدادات النشرة ====================

class NewsletterSettings(models.Model):
    """إعدادات النشرة البريدية"""

    is_enabled      = models.BooleanField(_('تفعيل الإرسال التلقائي'), default=True)
    daily_enabled   = models.BooleanField(_('يومي مفعل'),   default=True)
    weekly_enabled  = models.BooleanField(_('أسبوعي مفعل'), default=True)
    monthly_enabled = models.BooleanField(_('شهري مفعل'),   default=True)
    updated_by      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                        null=True, blank=True, verbose_name=_('عُدِّل بواسطة'))
    updated_at      = models.DateTimeField(_('آخر تحديث'), auto_now=True)

    class Meta:
        verbose_name        = _('إعدادات النشرة')
        verbose_name_plural = _('إعدادات النشرة')

    def __str__(self):
        return f'إعدادات النشرة — {"مفعل" if self.is_enabled else "موقوف"}'

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class NewsletterLogRecipient(models.Model):
    """المرسل إليهم في كل عملية إرسال"""
    log     = models.ForeignKey(NewsletterLog, on_delete=models.CASCADE,
                                related_name='recipients', verbose_name=_('السجل'))
    email   = models.EmailField(_('البريد الإلكتروني'))
    name    = models.CharField(_('الاسم'), max_length=100, blank=True)
    success = models.BooleanField(_('نجح'), default=True)
    sent_at = models.DateTimeField(_('وقت الإرسال'), auto_now_add=True)

    class Meta:
        verbose_name        = _('مستلم')
        verbose_name_plural = _('المستلمون')
        ordering            = ['email']
        indexes             = [
            models.Index(fields=['log']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f'{self.email} — {self.log}'