import io
import os
from datetime import date

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from django_ckeditor_5.fields import CKEditor5Field
from PIL import Image

User = get_user_model()


# ==================== دالة ضغط الصور ====================

def compress_image_field(image_field, quality=80, max_width=1200):
    """يضغط الصورة قبل الحفظ — يُستدعى في save()"""
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


# ==================== إعدادات الموقع ====================

class SiteSettings(models.Model):
    """إعدادات الموقع العامة"""

    site_name_ar = models.CharField(_('اسم الموقع بالعربية'),    max_length=200, default='جمعية نسائم فلسطين الخيرية')
    site_name_en = models.CharField(_('اسم الموقع بالإنجليزية'), max_length=200, default='Nasaeem Palestine Charity')

    logo          = models.ImageField(_('الشعار'),           upload_to='site/logo/',    blank=True, null=True)
    favicon       = models.ImageField(_('أيقونة الموقع'),   upload_to='site/favicon/', blank=True, null=True)
    default_image = models.ImageField(_('الصورة الافتراضية'), upload_to='site/default/', blank=True, null=True)

    phone_validator = RegexValidator(
        regex=r'^\+?[0-9]{10,15}$',
        message=_('رقم الهاتف يجب أن يكون بصيغة صحيحة')
    )
    phone            = models.CharField(_('رقم الهاتف'),      max_length=20, validators=[phone_validator])
    whatsapp_number  = models.CharField(_('رقم الواتساب'),    max_length=20, blank=True, null=True)
    email            = models.EmailField(_('البريد الإلكتروني'))
    address_ar       = models.TextField(_('العنوان بالعربية'))
    address_en       = models.TextField(_('العنوان بالإنجليزية'), blank=True, null=True)

    latitude  = models.DecimalField(_('خط العرض'), max_digits=10, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(_('خط الطول'), max_digits=11, decimal_places=8, blank=True, null=True)

    facebook_url  = models.URLField(_('رابط الفيسبوك'),  blank=True, null=True)
    twitter_url   = models.URLField(_('رابط تويتر'),     blank=True, null=True)
    instagram_url = models.URLField(_('رابط انستغرام'),  blank=True, null=True)
    tiktok_url    = models.URLField(_('رابط تيك توك'),   blank=True, null=True)
    youtube_url   = models.URLField(_('رابط يوتيوب'),    blank=True, null=True)

    about_summary_ar = CKEditor5Field(_('نبذة مختصرة بالعربية'),    config_name='default')
    about_summary_en = CKEditor5Field(_('نبذة مختصرة بالإنجليزية'), config_name='default', blank=True, null=True)

    established_year     = models.PositiveIntegerField(_('سنة التأسيس'),       default=2013)
    total_projects       = models.PositiveIntegerField(_('عدد المشاريع'),       default=0)
    total_beneficiaries  = models.PositiveIntegerField(_('عدد المستفيدين'),     default=0)
    total_donations      = models.DecimalField(_('إجمالي التبرعات'), max_digits=15, decimal_places=2, default=0)

    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name        = _('إعدادات الموقع')
        verbose_name_plural = _('إعدادات الموقع')

    def __str__(self):
        return self.site_name_ar

    def save(self, *args, **kwargs):
        if not self.pk and SiteSettings.objects.exists():
            raise ValueError(_('يمكن إنشاء إعدادات موقع واحدة فقط'))
        # ضغط الصور
        for field in (self.logo, self.favicon, self.default_image):
            if field and hasattr(field, 'file'):
                compress_image_field(field, quality=85, max_width=800)
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        settings_obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                'site_name_ar':      'جمعية نسائم فلسطين الخيرية',
                'site_name_en':      'Nasaeem Palestine Charity',
                'phone':             '056751504',
                'email':             'nasaempalstin2013@gmail.com',
                'address_ar':        'غزة - السامر - مقابل مدرسة الإمام الشافعي',
                'about_summary_ar':  'مؤسسة خيرية تنموية إنسانية، تعمل على تنفيذ البرامج والمشاريع.',
            }
        )
        return settings_obj


# ==================== صفحة من نحن ====================

class AboutPage(models.Model):
    """صفحة من نحن"""

    title_ar   = models.CharField(_('العنوان بالعربية'),    max_length=200, default='من نحن')
    title_en   = models.CharField(_('العنوان بالإنجليزية'), max_length=200, default='About Us')
    content_ar = CKEditor5Field(_('المحتوى بالعربية'))
    content_en = CKEditor5Field(_('المحتوى بالإنجليزية'), blank=True, null=True)
    image      = models.ImageField(_('الصورة'), upload_to='pages/about/', blank=True, null=True)

    meta_description_ar = models.TextField(_('وصف SEO بالعربية'),    max_length=160, blank=True, null=True)
    meta_description_en = models.TextField(_('وصف SEO بالإنجليزية'), max_length=160, blank=True, null=True)

    is_active  = models.BooleanField(_('مفعل'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name        = _('صفحة من نحن')
        verbose_name_plural = _('صفحة من نحن')

    def __str__(self):
        return self.title_ar

    def save(self, *args, **kwargs):
        if self.image and hasattr(self.image, 'file'):
            compress_image_field(self.image, quality=80, max_width=1200)
        super().save(*args, **kwargs)


# ==================== صفحة الرؤية والرسالة ====================

class VisionPage(models.Model):
    """صفحة الرؤية والرسالة"""

    vision_title_ar   = models.CharField(_('عنوان الرؤية بالعربية'),    max_length=200, default='رؤيتنا')
    vision_title_en   = models.CharField(_('عنوان الرؤية بالإنجليزية'), max_length=200, default='Our Vision')
    vision_content_ar = CKEditor5Field(_('محتوى الرؤية بالعربية'))
    vision_content_en = CKEditor5Field(_('محتوى الرؤية بالإنجليزية'), blank=True, null=True)

    mission_title_ar   = models.CharField(_('عنوان الرسالة بالعربية'),    max_length=200, default='رسالتنا')
    mission_title_en   = models.CharField(_('عنوان الرسالة بالإنجليزية'), max_length=200, default='Our Mission')
    mission_content_ar = CKEditor5Field(_('محتوى الرسالة بالعربية'))
    mission_content_en = CKEditor5Field(_('محتوى الرسالة بالإنجليزية'), blank=True, null=True)

    values_title_ar   = models.CharField(_('عنوان القيم بالعربية'),    max_length=200, default='قيمنا')
    values_title_en   = models.CharField(_('عنوان القيم بالإنجليزية'), max_length=200, default='Our Values')
    values_content_ar = CKEditor5Field(_('محتوى القيم بالعربية'))
    values_content_en = CKEditor5Field(_('محتوى القيم بالإنجليزية'), blank=True, null=True)

    vision_image  = models.ImageField(_('صورة الرؤية'),   upload_to='pages/vision/',  blank=True, null=True)
    mission_image = models.ImageField(_('صورة الرسالة'),  upload_to='pages/mission/', blank=True, null=True)
    values_image  = models.ImageField(_('صورة القيم'),    upload_to='pages/values/',  blank=True, null=True)

    meta_description_ar = models.TextField(_('وصف SEO بالعربية'),    max_length=160, blank=True, null=True)
    meta_description_en = models.TextField(_('وصف SEO بالإنجليزية'), max_length=160, blank=True, null=True)

    is_active  = models.BooleanField(_('مفعل'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name        = _('صفحة الرؤية والرسالة')
        verbose_name_plural = _('صفحة الرؤية والرسالة')

    def __str__(self):
        return f'{self.vision_title_ar} - {self.mission_title_ar}'

    def save(self, *args, **kwargs):
        for field in (self.vision_image, self.mission_image, self.values_image):
            if field and hasattr(field, 'file'):
                compress_image_field(field, quality=80, max_width=1200)
        super().save(*args, **kwargs)


# ==================== نقاط القيم ====================

class ValuePoint(models.Model):
    """نقاط القيم"""

    vision_page = models.ForeignKey(VisionPage, on_delete=models.CASCADE,
                                    related_name='value_points', verbose_name=_('الصفحة'))
    content_ar  = models.CharField(_('المحتوى بالعربية'),    max_length=500)
    content_en  = models.CharField(_('المحتوى بالإنجليزية'), max_length=500, blank=True, null=True)
    order       = models.IntegerField(_('الترتيب'), default=0)
    is_active   = models.BooleanField(_('مفعل'), default=True)
    created_at  = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at  = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name        = _('نقطة قيمة')
        verbose_name_plural = _('نقاط القيم')
        ordering            = ['order', 'id']

    def __str__(self):
        return self.content_ar[:50]

    def save(self, *args, **kwargs):
        if not self.order:
            max_order = ValuePoint.objects.filter(
                vision_page=self.vision_page
            ).aggregate(models.Max('order'))['order__max']
            self.order = (max_order or 0) + 1
        super().save(*args, **kwargs)


# ==================== الأهداف ====================

class Goal(models.Model):
    """أهداف الجمعية"""

    title_ar       = models.CharField(_('الهدف بالعربية'),    max_length=300)
    title_en       = models.CharField(_('الهدف بالإنجليزية'), max_length=300, blank=True, null=True)
    description_ar = models.TextField(_('الوصف بالعربية'),    blank=True, null=True)
    description_en = models.TextField(_('الوصف بالإنجليزية'), blank=True, null=True)
    icon           = models.CharField(_('أيقونة FontAwesome'), max_length=50, default='fas fa-bullseye')
    order          = models.PositiveIntegerField(_('الترتيب'), default=0)
    is_active      = models.BooleanField(_('مفعل'), default=True)
    created_at     = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at     = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name        = _('هدف')
        verbose_name_plural = _('الأهداف')
        ordering            = ['order', 'created_at']

    def __str__(self):
        return self.title_ar


# ==================== مجلس الإدارة ====================

class BoardMember(models.Model):
    """أعضاء مجلس الإدارة"""

    POSITION_CHOICES = [
        ('president',      _('رئيس مجلس الإدارة')),
        ('vice_president', _('نائب الرئيس')),
        ('secretary',      _('السكرتير')),
        ('treasurer',      _('أمين الصندوق')),
        ('member',         _('عضو')),
    ]

    POSITION_TRANSLATIONS = {
        'president':      'President of the Board',
        'vice_president': 'Vice President',
        'secretary':      'Secretary',
        'treasurer':      'Treasurer',
        'member':         'Member',
    }

    name_ar = models.CharField(_('الاسم بالعربية'),    max_length=100)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=100, blank=True, null=True)

    position_type_ar  = models.CharField(_('نوع المنصب بالعربية'),    max_length=100)
    position_type_en  = models.CharField(_('نوع المنصب بالإنجليزية'), max_length=100, blank=True, null=True)
    is_custom_position = models.BooleanField(_('منصب مخصص'), default=False)
    position_type     = models.CharField(_('نوع المنصب'), max_length=20, choices=POSITION_CHOICES,
                                         default='member', blank=True, null=True)

    bio_ar = models.TextField(_('نبذة شخصية بالعربية'),    blank=True, null=True)
    bio_en = models.TextField(_('نبذة شخصية بالإنجليزية'), blank=True, null=True)
    photo  = models.ImageField(_('الصورة الشخصية'), upload_to='board_members/', blank=True, null=True)

    email        = models.EmailField(_('البريد الإلكتروني'), blank=True, null=True)
    phone        = models.CharField(_('رقم الهاتف'), max_length=20, blank=True, null=True)
    facebook_url = models.URLField(_('رابط الفيسبوك'), blank=True, null=True)
    twitter_url  = models.URLField(_('رابط تويتر'),    blank=True, null=True)
    linkedin_url = models.URLField(_('رابط لينكدإن'),  blank=True, null=True)

    order      = models.PositiveIntegerField(_('الترتيب'), default=0)
    is_active  = models.BooleanField(_('مفعل'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('عضو مجلس الإدارة')
        verbose_name_plural = _('أعضاء مجلس الإدارة')
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['is_active', 'order']),
            models.Index(fields=['is_custom_position']),
            # ── إضافات جديدة ──
            models.Index(fields=['is_active']),
            models.Index(fields=['position_type']),
            models.Index(fields=['is_active', 'position_type']),
        ]

    def __str__(self):
        return f'{self.name_ar} - {self.position_type_ar}'

    def save(self, *args, **kwargs):
        if not self.is_custom_position and self.position_type:
            self.position_type_en = self.POSITION_TRANSLATIONS.get(
                self.position_type, self.position_type_ar
            )
        # ضغط الصورة
        if self.photo and hasattr(self.photo, 'file'):
            compress_image_field(self.photo, quality=80, max_width=600)
        super().save(*args, **kwargs)

    def get_position_display_ar(self):
        if self.is_custom_position:
            return self.position_type_ar
        return dict(self.POSITION_CHOICES).get(self.position_type, self.position_type_ar)

    def get_position_display_en(self):
        if self.is_custom_position:
            return self.position_type_en or self.position_type_ar
        return self.POSITION_TRANSLATIONS.get(self.position_type, self.position_type_ar)

    def get_social_links(self):
        links = []
        if self.facebook_url:
            links.append({'name': 'Facebook', 'url': self.facebook_url, 'icon': 'fab fa-facebook'})
        if self.twitter_url:
            links.append({'name': 'Twitter',  'url': self.twitter_url,  'icon': 'fab fa-twitter'})
        if self.linkedin_url:
            links.append({'name': 'LinkedIn', 'url': self.linkedin_url, 'icon': 'fab fa-linkedin'})
        return links


# ==================== السلايدر ====================

class HomeSlider(models.Model):
    """سلايدر الصفحة الرئيسية"""

    title_ar    = models.CharField(_('العنوان بالعربية'),         max_length=200)
    title_en    = models.CharField(_('العنوان بالإنجليزية'),      max_length=200, blank=True, null=True)
    subtitle_ar = models.CharField(_('العنوان الفرعي بالعربية'),  max_length=300, blank=True, null=True)
    subtitle_en = models.CharField(_('العنوان الفرعي بالإنجليزية'), max_length=300, blank=True, null=True)
    description_ar = models.TextField(_('الوصف بالعربية'),    blank=True, null=True)
    description_en = models.TextField(_('الوصف بالإنجليزية'), blank=True, null=True)

    image = models.ImageField(_('الصورة'), upload_to='slider/')

    button_text_ar = models.CharField(_('نص الزر بالعربية'),    max_length=50, blank=True, null=True)
    button_text_en = models.CharField(_('نص الزر بالإنجليزية'), max_length=50, blank=True, null=True)
    button_url     = models.URLField(_('رابط الزر'), blank=True, null=True)

    order      = models.PositiveIntegerField(_('الترتيب'), default=0)
    is_active  = models.BooleanField(_('مفعل'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name        = _('شريحة في السلايدر')
        verbose_name_plural = _('شرائح السلايدر')
        ordering            = ['order', 'created_at']

    def __str__(self):
        return self.title_ar

    def save(self, *args, **kwargs):
        # السلايدر يحتاج عرض أكبر — 1920px
        if self.image and hasattr(self.image, 'file'):
            compress_image_field(self.image, quality=85, max_width=1920)
        super().save(*args, **kwargs)


# ==================== الشركاء ====================

class Partner(models.Model):
    """شركاء الجمعية"""

    name_ar        = models.CharField(_('الاسم'),         max_length=200)
    name_en        = models.CharField(_('Name'),           max_length=200, blank=True)
    logo           = models.ImageField(_('اللوجو'),        upload_to='partners/')
    description_ar = models.CharField(_('وصف مختصر'),     max_length=500, blank=True)
    description_en = models.CharField(_('Short Description'), max_length=500, blank=True)

    partnership_date = models.DateField(_('تاريخ الشراكة'), default=date.today)
    projects_count   = models.PositiveIntegerField(_('عدد المشاريع المنفذة'), default=0)

    website    = models.URLField(_('الموقع الإلكتروني'), blank=True)
    email      = models.EmailField(_('البريد الإلكتروني'), blank=True)
    phone      = models.CharField(_('الهاتف'), max_length=20, blank=True)
    order      = models.PositiveIntegerField(_('الترتيب'), default=0)
    is_active  = models.BooleanField(_('مفعل'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإضافة'), auto_now_add=True)

    class Meta:
        verbose_name        = _('شريك')
        verbose_name_plural = _('الشركاء')
        ordering            = ['order', '-partnership_date']

    def __str__(self):
        return self.name_ar

    def save(self, *args, **kwargs):
        if self.logo and hasattr(self.logo, 'file'):
            compress_image_field(self.logo, quality=80, max_width=400)
        super().save(*args, **kwargs)


# ==================== الإحصائيات ====================

class Statistic(models.Model):
    """إحصائيات الموقع"""

    title_ar  = models.CharField(_('العنوان بالعربية'),    max_length=100)
    title_en  = models.CharField(_('العنوان بالإنجليزية'), max_length=100, blank=True, null=True)
    number    = models.PositiveIntegerField(_('الرقم'), default=0)
    suffix_ar = models.CharField(_('اللاحقة بالعربية'),    max_length=20, blank=True, null=True)
    suffix_en = models.CharField(_('اللاحقة بالإنجليزية'), max_length=20, blank=True, null=True)
    icon      = models.CharField(_('أيقونة FontAwesome'), max_length=50, default='fas fa-chart-bar')
    color     = models.CharField(_('اللون'), max_length=7, default='#6B8E23')
    order     = models.PositiveIntegerField(_('الترتيب'), default=0)
    is_active = models.BooleanField(_('مفعل'), default=True)

    auto_update_from = models.CharField(_('تحديث تلقائي من'), max_length=50, blank=True, null=True,
        choices=[
            ('projects_count',     _('عدد المشاريع')),
            ('users_count',        _('عدد المستخدمين')),
            ('beneficiaries_count', _('عدد المستفيدين')),
        ]
    )

    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name        = _('إحصائية')
        verbose_name_plural = _('الإحصائيات')
        ordering            = ['order', 'created_at']

    def __str__(self):
        return f'{self.title_ar}: {self.number}'

    def get_formatted_number(self):
        return f'{self.number:,}'

    def update_number(self):
        from django.db.models import Sum
        from projects.models import Project

        if self.auto_update_from == 'projects_count':
            self.number = Project.objects.filter(is_active=True).count()
        elif self.auto_update_from == 'users_count':
            self.number = User.objects.filter(is_active=True).count()
        elif self.auto_update_from == 'beneficiaries_count':
            total = Project.objects.filter(is_active=True).aggregate(
                total=Sum('beneficiaries_count')
            )['total']
            self.number = total or 0

        self.save(update_fields=['number', 'updated_at'])