import io
import os
import re

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.core.files.base import ContentFile
from django_ckeditor_5.fields import CKEditor5Field
from PIL import Image


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


# ==================== فئات المشاريع ====================

class ProjectCategory(models.Model):
    """فئات المشاريع"""

    name_ar        = models.CharField(_('اسم الفئة بالعربية'),    max_length=100)
    name_en        = models.CharField(_('اسم الفئة بالإنجليزية'), max_length=100, blank=True, null=True)
    slug           = models.SlugField(_('الرابط'), max_length=120, unique=True, blank=True)
    description_ar = models.TextField(_('الوصف بالعربية'),    blank=True, null=True)
    description_en = models.TextField(_('الوصف بالإنجليزية'), blank=True, null=True)
    icon           = models.CharField(_('أيقونة FontAwesome'), max_length=50, default='fas fa-folder')
    color          = models.CharField(_('لون الفئة'), max_length=7, default='#6B8E23')
    image          = models.ImageField(_('صورة الفئة'), upload_to='categories/', blank=True, null=True)
    order          = models.PositiveIntegerField(_('الترتيب'), default=0)
    is_active      = models.BooleanField(_('مفعل'), default=True)
    created_at     = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at     = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name        = _('فئة المشاريع')
        verbose_name_plural = _('فئات المشاريع')
        ordering            = ['order', 'created_at']

    def __str__(self):
        return self.name_ar

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name_ar, allow_unicode=True)
        if self.image and hasattr(self.image, 'file'):
            compress_image_field(self.image, quality=80, max_width=800)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('projects:category_projects', kwargs={'slug': self.slug})

    def get_projects_count(self):
        return self.projects.filter(is_active=True).count()


# ==================== المشاريع ====================

class Project(models.Model):
    """المشاريع"""

    STATUS_CHOICES = [
        ('planning',  _('في التخطيط')),
        ('active',    _('نشط')),
        ('completed', _('مكتمل')),
        ('suspended', _('معلق')),
        ('cancelled', _('ملغى')),
    ]

    PRIORITY_CHOICES = [
        ('low',    _('منخفضة')),
        ('medium', _('متوسطة')),
        ('high',   _('عالية')),
        ('urgent', _('عاجلة')),
    ]

    title_ar = models.CharField(_('عنوان المشروع بالعربية'),    max_length=200)
    title_en = models.CharField(_('عنوان المشروع بالإنجليزية'), max_length=200, blank=True, null=True)
    slug     = models.SlugField(_('الرابط'), max_length=220, unique=True, blank=True)

    category = models.ForeignKey(ProjectCategory, on_delete=models.CASCADE,
                                 related_name='projects', verbose_name=_('الفئة'))

    summary_ar     = models.TextField(_('ملخص المشروع بالعربية'),    max_length=500)
    summary_en     = models.TextField(_('ملخص المشروع بالإنجليزية'), max_length=500, blank=True, null=True)
    description_ar = CKEditor5Field(_('وصف المشروع بالعربية'))
    description_en = CKEditor5Field(_('وصف المشروع بالإنجليزية'), blank=True, null=True)

    main_image = models.ImageField(_('الصورة الرئيسية'), upload_to='projects/main/', blank=True, null=True)

    status   = models.CharField(_('حالة المشروع'), max_length=20, choices=STATUS_CHOICES,  default='planning')
    priority = models.CharField(_('الأولوية'),     max_length=20, choices=PRIORITY_CHOICES, default='medium')

    start_date = models.DateField(_('تاريخ البداية'), blank=True, null=True)
    end_date   = models.DateField(_('تاريخ النهاية'), blank=True, null=True)

    target_amount = models.DecimalField(_('المبلغ المستهدف'), max_digits=12, decimal_places=2,
                                        default=0, validators=[MinValueValidator(0)])
    raised_amount = models.DecimalField(_('المبلغ المجمع'),   max_digits=12, decimal_places=2,
                                        default=0, validators=[MinValueValidator(0)])

    beneficiaries_count   = models.PositiveIntegerField(_('عدد المستفيدين'),          default=0)
    target_beneficiaries  = models.PositiveIntegerField(_('المستفيدين المستهدفين'),   default=0)

    location_ar = models.CharField(_('الموقع بالعربية'),    max_length=200, blank=True, null=True)
    location_en = models.CharField(_('الموقع بالإنجليزية'), max_length=200, blank=True, null=True)

    keywords_ar = models.CharField(_('كلمات مفتاحية'),               max_length=300, blank=True, null=True)
    keywords_en = models.CharField(_('كلمات مفتاحية بالإنجليزية'),   max_length=300, blank=True, null=True)

    is_featured    = models.BooleanField(_('مشروع مميز'),         default=False)
    is_active      = models.BooleanField(_('مفعل'),                default=True)
    allow_comments = models.BooleanField(_('السماح بالتعليقات'),  default=True)

    views_count  = models.PositiveIntegerField(_('عدد المشاهدات'),  default=0)
    likes_count  = models.PositiveIntegerField(_('عدد الإعجابات'),  default=0)
    shares_count = models.PositiveIntegerField(_('عدد المشاركات'), default=0)

    meta_description_ar = models.TextField(_('وصف SEO بالعربية'),    max_length=160, blank=True, null=True)
    meta_description_en = models.TextField(_('وصف SEO بالإنجليزية'), max_length=160, blank=True, null=True)

    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('مشروع')
        verbose_name_plural = _('المشاريع')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['slug']),
            models.Index(fields=['status']),
            # ── إضافات جديدة ──
            models.Index(fields=['is_active']),
            models.Index(fields=['is_active', 'status']),
            models.Index(fields=['is_active', 'is_featured']),
            models.Index(fields=['is_active', '-views_count']),
            models.Index(fields=['category', 'is_active']),
        ]

    def __str__(self):
        return self.title_ar

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title_ar, allow_unicode=True)
            original_slug = self.slug
            counter = 1
            while Project.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        # ضغط الصورة الرئيسية
        if self.main_image and hasattr(self.main_image, 'file'):
            compress_image_field(self.main_image, quality=82, max_width=1200)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('projects:project_detail', kwargs={'slug': self.slug})

    # ==================== Properties ====================

    @property
    def remaining_amount(self):
        if self.target_amount and self.raised_amount:
            return max(0, self.target_amount - self.raised_amount)
        return 0

    @property
    def remaining_beneficiaries(self):
        if self.target_beneficiaries and self.beneficiaries_count:
            return max(0, self.target_beneficiaries - self.beneficiaries_count)
        return 0

    # ==================== Methods ====================

    def get_progress_percentage(self):
        try:
            if self.target_amount and float(self.target_amount) > 0:
                return min(round((float(self.raised_amount) / float(self.target_amount)) * 100, 2), 100.0)
            return 0.0
        except Exception:
            return 0.0

    def get_beneficiaries_percentage(self):
        try:
            if self.target_beneficiaries and int(self.target_beneficiaries) > 0:
                return min(round((float(self.beneficiaries_count) / float(self.target_beneficiaries)) * 100, 2), 100.0)
            return 0.0
        except Exception:
            return 0.0

    def get_overall_percentage(self):
        try:
            fp = float(self.get_progress_percentage())
            if self.target_beneficiaries and int(self.target_beneficiaries) > 0:
                bp = float(self.get_beneficiaries_percentage())
                return round((fp + bp) / 2.0, 2)
            return fp
        except Exception:
            return 0.0

    def increment_views(self):
        self.views_count += 1
        self.save(update_fields=['views_count'])

    def increment_likes(self):
        self.likes_count += 1
        self.save(update_fields=['likes_count'])

    def decrement_likes(self):
        if self.likes_count > 0:
            self.likes_count -= 1
            self.save(update_fields=['likes_count'])

    def increment_shares(self):
        self.shares_count += 1
        self.save(update_fields=['shares_count'])

    def get_keywords_list(self):
        if self.keywords_ar:
            return [kw.strip() for kw in self.keywords_ar.split(',') if kw.strip()]
        return []

    def is_funding_complete(self):
        return bool(self.target_amount and self.target_amount > 0 and self.raised_amount >= self.target_amount)

    def is_beneficiaries_complete(self):
        return bool(self.target_beneficiaries and self.target_beneficiaries > 0
                    and self.beneficiaries_count >= self.target_beneficiaries)

    def is_project_complete(self):
        if self.target_beneficiaries and self.target_beneficiaries > 0:
            return self.is_funding_complete() and self.is_beneficiaries_complete()
        return self.is_funding_complete()

    def get_days_remaining(self):
        if self.end_date:
            today = timezone.now().date()
            return max(0, (self.end_date - today).days) if self.end_date > today else 0
        return None

    def is_expired(self):
        return bool(self.end_date and self.end_date < timezone.now().date())

    def get_status_class(self):
        return {
            'active': 'status-active', 'completed': 'status-completed',
            'planning': 'status-planning', 'suspended': 'status-suspended',
            'cancelled': 'status-cancelled',
        }.get(self.status, 'status-default')

    def get_priority_class(self):
        return {
            'low': 'priority-low', 'medium': 'priority-medium',
            'high': 'priority-high', 'urgent': 'priority-urgent',
        }.get(self.priority, 'priority-default')

    def get_priority_icon(self):
        return {
            'low': 'fas fa-arrow-down', 'medium': 'fas fa-minus',
            'high': 'fas fa-arrow-up',  'urgent': 'fas fa-exclamation-triangle',
        }.get(self.priority, 'fas fa-star')


# ==================== صور المشاريع ====================

class ProjectImage(models.Model):
    """صور المشاريع"""

    project        = models.ForeignKey(Project, on_delete=models.CASCADE,
                                       related_name='images', verbose_name=_('المشروع'))
    image          = models.ImageField(_('الصورة'), upload_to='projects/images/')
    title_ar       = models.CharField(_('عنوان الصورة بالعربية'),    max_length=200, blank=True, null=True)
    title_en       = models.CharField(_('عنوان الصورة بالإنجليزية'), max_length=200, blank=True, null=True)
    description_ar = models.TextField(_('وصف الصورة بالعربية'),    blank=True, null=True)
    description_en = models.TextField(_('وصف الصورة بالإنجليزية'), blank=True, null=True)
    order          = models.PositiveIntegerField(_('الترتيب'), default=0)
    is_active      = models.BooleanField(_('مفعل'), default=True)
    created_at     = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name        = _('صورة المشروع')
        verbose_name_plural = _('صور المشاريع')
        ordering            = ['order', 'created_at']

    def __str__(self):
        return f'{self.project.title_ar} - صورة {self.id}'

    def save(self, *args, **kwargs):
        if self.image and hasattr(self.image, 'file'):
            compress_image_field(self.image, quality=80, max_width=1200)
        super().save(*args, **kwargs)


# ==================== فيديوهات المشاريع ====================

class ProjectVideo(models.Model):
    """فيديوهات المشاريع"""

    project        = models.ForeignKey(Project, on_delete=models.CASCADE,
                                       related_name='videos', verbose_name=_('المشروع'))
    title_ar       = models.CharField(_('عنوان الفيديو بالعربية'),    max_length=200)
    title_en       = models.CharField(_('عنوان الفيديو بالإنجليزية'), max_length=200, blank=True, null=True)
    youtube_url    = models.URLField(_('رابط اليوتيوب'), blank=True, null=True)
    description_ar = models.TextField(_('وصف الفيديو بالعربية'),    blank=True, null=True)
    description_en = models.TextField(_('وصف الفيديو بالإنجليزية'), blank=True, null=True)
    thumbnail      = models.ImageField(_('صورة مصغرة'), upload_to='projects/videos/thumbnails/',
                                       blank=True, null=True)
    duration   = models.PositiveIntegerField(_('مدة الفيديو (بالثواني)'), blank=True, null=True)
    order      = models.PositiveIntegerField(_('الترتيب'), default=0)
    is_active  = models.BooleanField(_('مفعل'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name        = _('فيديو المشروع')
        verbose_name_plural = _('فيديوهات المشاريع')
        ordering            = ['order', 'created_at']

    def __str__(self):
        return self.title_ar

    def save(self, *args, **kwargs):
        if self.thumbnail and hasattr(self.thumbnail, 'file'):
            compress_image_field(self.thumbnail, quality=80, max_width=800)
        super().save(*args, **kwargs)

    def get_youtube_id(self):
        if self.youtube_url:
            match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', self.youtube_url)
            if match:
                return match.group(1)
        return None

    def get_embed_url(self):
        youtube_id = self.get_youtube_id()
        return f'https://www.youtube.com/embed/{youtube_id}' if youtube_id else None


# ==================== مستندات المشاريع ====================

class ProjectDocument(models.Model):
    """مستندات المشاريع"""

    DOCUMENT_TYPES = [
        ('report',       _('تقرير')),
        ('presentation', _('عرض تقديمي')),
        ('brochure',     _('كتيب')),
        ('certificate',  _('شهادة')),
        ('other',        _('أخرى')),
    ]

    project        = models.ForeignKey(Project, on_delete=models.CASCADE,
                                       related_name='documents', verbose_name=_('المشروع'))
    title_ar       = models.CharField(_('عنوان المستند بالعربية'),    max_length=200)
    title_en       = models.CharField(_('عنوان المستند بالإنجليزية'), max_length=200, blank=True, null=True)
    document_type  = models.CharField(_('نوع المستند'), max_length=20, choices=DOCUMENT_TYPES, default='other')
    file           = models.FileField(_('الملف'), upload_to='projects/documents/')
    description_ar = models.TextField(_('وصف المستند بالعربية'),    blank=True, null=True)
    description_en = models.TextField(_('وصف المستند بالإنجليزية'), blank=True, null=True)
    file_size      = models.PositiveIntegerField(_('حجم الملف (بايت)'), blank=True, null=True)
    download_count = models.PositiveIntegerField(_('عدد التحميلات'), default=0)
    is_public      = models.BooleanField(_('متاح للجمهور'), default=True)
    is_active      = models.BooleanField(_('مفعل'), default=True)
    created_at     = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name        = _('مستند المشروع')
        verbose_name_plural = _('مستندات المشاريع')
        ordering            = ['-created_at']

    def __str__(self):
        return self.title_ar

    def get_file_extension(self):
        return self.file.name.split('.')[-1].upper() if self.file else ''

    def get_formatted_file_size(self):
        if self.file_size:
            if self.file_size < 1024:
                return f'{self.file_size} بايت'
            elif self.file_size < 1024 * 1024:
                return f'{self.file_size / 1024:.1f} KB'
            return f'{self.file_size / (1024 * 1024):.1f} MB'
        return 'غير محدد'

    def increment_download(self):
        self.download_count += 1
        self.save(update_fields=['download_count'])


# ==================== إعجابات المشاريع ====================

class ProjectLike(models.Model):
    """إعجابات المشاريع"""

    project    = models.ForeignKey(Project, on_delete=models.CASCADE,
                                   related_name='project_likes', verbose_name=_('المشروع'))
    ip_address = models.GenericIPAddressField(_('عنوان IP'))
    user_agent = models.TextField(_('معلومات المتصفح'), blank=True, null=True)
    created_at = models.DateTimeField(_('تاريخ الإعجاب'), auto_now_add=True)

    class Meta:
        verbose_name        = _('إعجاب المشروع')
        verbose_name_plural = _('إعجابات المشاريع')
        unique_together     = ['project', 'ip_address']

    def __str__(self):
        return f'{self.project.title_ar} - {self.ip_address}'