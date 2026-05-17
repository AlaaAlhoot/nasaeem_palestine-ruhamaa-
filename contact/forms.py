from django.core.validators import EmailValidator, ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.conf import settings
import re
from .models import *
from django.db import models
from django.utils.translation import gettext_lazy as _
from django import forms

class ContactForm(forms.ModelForm):
    """نموذج التواصل مع الجمعية"""

    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message', 'attachment']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('اكتب اسمك الكامل'),
                'required': True,
                'autocomplete': 'name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter your email') + ' (e.g. example@email.com)',
                'required': True,
                'autocomplete': 'email'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('رقم الهاتف (اختياري)'),
                'autocomplete': 'tel',
                'type': 'tel'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('موضوع الرسالة'),
                'required': True,
                'maxlength': '200'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': _('اكتب رسالتك هنا...'),
                'rows': 6,
                'required': True,
                'maxlength': '2000'
            }),
            'attachment': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.txt'
            })
        }

        labels = {
            'name': _('الاسم الكامل *'),
            'email': _('البريد الإلكتروني *'),
            'phone': _('رقم الهاتف'),
            'subject': _('الموضوع *'),
            'message': _('الرسالة *'),
            'attachment': _('مرفق (اختياري)')
        }

        help_texts = {
            'phone': _('رقم هاتف صحيح للتواصل معك'),
            'message': _('اكتب تفاصيل رسالتك (حد أقصى 2000 حرف)'),
            'attachment': _('يمكنك إرفاق ملف (PDF, DOC, JPG, PNG) - حجم أقصى 5MB')
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # إضافة علامة النجمة للحقول المطلوبة
        for field_name, field in self.fields.items():
            if field.required:
                field.widget.attrs['required'] = True
                if 'placeholder' in field.widget.attrs:
                    field.widget.attrs['placeholder'] += ' *'

    def clean_name(self):
        """التحقق من صحة الاسم"""
        name = self.cleaned_data.get('name', '').strip()

        if len(name) < 2:
            raise ValidationError(_('الاسم يجب أن يكون أطول من حرفين'))

        if len(name) > 100:
            raise ValidationError(_('الاسم طويل جداً'))

        # التحقق من وجود أحرف صالحة فقط
        if not re.match(r'^[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFFa-zA-Z\s\-\'\.]+$', name):
            raise ValidationError(_('الاسم يحتوي على أحرف غير صالحة'))

        return name

    def clean_email(self):
        """التحقق من صحة البريد الإلكتروني"""
        email = self.cleaned_data.get('email', '').strip().lower()

        # استخدام EmailValidator المدمج
        validator = EmailValidator()
        try:
            validator(email)
        except ValidationError:
            raise ValidationError(_('البريد الإلكتروني غير صحيح'))

        # التحقق من النطاقات المحظورة
        blocked_domains = getattr(settings, 'BLOCKED_EMAIL_DOMAINS', [
            '10minutemail.com', 'tempmail.org', 'guerrillamail.com'
        ])

        domain = email.split('@')[1] if '@' in email else ''
        if domain in blocked_domains:
            raise ValidationError(_('هذا النطاق البريدي غير مسموح'))

        return email

    def clean_phone(self):
        """التحقق من رقم الهاتف"""
        phone = self.cleaned_data.get('phone', '')

        if not phone:
            return phone  # الحقل اختياري

        # تحويل PhoneNumber object إلى string
        phone_str = str(phone) if phone else ''

        # إزالة المسافات والرموز
        phone_cleaned = re.sub(r'[^\d+]', '', phone_str)

        # التحقق من طول الرقم
        if len(phone_cleaned) < 8:
            raise ValidationError(_('رقم الهاتف قصير جداً'))

        if len(phone_cleaned) > 15:
            raise ValidationError(_('رقم الهاتف طويل جداً'))

        # التحقق من صيغة الرقم
        if not re.match(r'^[\+]?[1-9]\d{1,14}$', phone_cleaned):
            raise ValidationError(_('صيغة رقم الهاتف غير صحيحة'))

        return phone_cleaned

    def clean_subject(self):
        """التحقق من موضوع الرسالة"""
        subject = self.cleaned_data.get('subject', '').strip()

        if len(subject) < 3:
            raise ValidationError(_('الموضوع قصير جداً'))

        if len(subject) > 200:
            raise ValidationError(_('الموضوع طويل جداً'))

        # منع الكلمات المحظورة
        spam_words = ['spam', 'viagra', 'casino', 'lottery', 'winner']
        if any(word.lower() in subject.lower() for word in spam_words):
            raise ValidationError(_('الموضوع يحتوي على كلمات محظورة'))

        return subject

    def clean_message(self):
        """التحقق من محتوى الرسالة"""
        message = self.cleaned_data.get('message', '').strip()

        if len(message) < 10:
            raise ValidationError(_('الرسالة قصيرة جداً. اكتب على الأقل 10 أحرف'))

        if len(message) > 2000:
            raise ValidationError(_('الرسالة طويلة جداً. الحد الأقصى 2000 حرف'))

        # التحقق من تكرار الأحرف
        if len(set(message.replace(' ', ''))) < 5:
            raise ValidationError(_('الرسالة تحتوي على تكرار مفرط للأحرف'))

        # منع الروابط المشبوهة
        suspicious_patterns = [
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            r'www\.[\w\.-]+\.\w+',
            r'bit\.ly/',
            r't\.co/',
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, message):
                raise ValidationError(_('الرسالة تحتوي على روابط غير مسموحة'))

        return message

    def clean_attachment(self):
        """التحقق من الملف المرفق"""
        attachment = self.cleaned_data.get('attachment')

        if not attachment:
            return attachment

        # التحقق من حجم الملف
        max_size = getattr(settings, 'MAX_ATTACHMENT_SIZE', 5 * 1024 * 1024)  # 5MB
        if attachment.size > max_size:
            raise ValidationError(_('حجم الملف كبير جداً. الحد الأقصى 5MB'))

        # التحقق من نوع الملف
        allowed_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'image/jpeg',
            'image/png',
            'image/gif',
            'text/plain'
        ]

        if attachment.content_type not in allowed_types:
            raise ValidationError(_('نوع الملف غير مدعوم. الملفات المسموحة: PDF, DOC, DOCX, JPG, PNG, GIF, TXT'))

        # التحقق من امتداد الملف
        allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif', '.txt']
        file_extension = attachment.name.lower().split('.')[-1]

        if f'.{file_extension}' not in allowed_extensions:
            raise ValidationError(_('امتداد الملف غير مدعوم'))

        return attachment

    def clean(self):
        """التحقق العام من النموذج"""
        cleaned_data = super().clean()

        name = cleaned_data.get('name', '')
        email = cleaned_data.get('email', '')
        subject = cleaned_data.get('subject', '')
        message = cleaned_data.get('message', '')

        # منع الرسائل المتشابهة
        if name and email and subject and message:
            # التحقق من وجود رسالة مشابهة خلال آخر ساعة
            from django.utils import timezone
            from datetime import timedelta

            recent_messages = ContactMessage.objects.filter(
                email=email,
                subject__iexact=subject,
                created_at__gte=timezone.now() - timedelta(hours=1)
            )

            if recent_messages.exists():
                raise ValidationError(_('لقد أرسلت رسالة مشابهة مؤخراً. يرجى الانتظار قبل الإرسال مرة أخرى.'))

        return cleaned_data
class NewsletterForm(forms.ModelForm):
    """نموذج الاشتراك في النشرة البريدية"""

    class Meta:
        model = Newsletter
        fields = ['email', 'name', 'frequency']

        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter your email') + ' (e.g. example@email.com)',
                'required': True,
                'autocomplete': 'email'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('الاسم (اختياري)'),
                'autocomplete': 'name'
            }),
            'frequency': forms.Select(attrs={
                'class': 'form-select'
            })
        }

        labels = {
            'email': _('البريد الإلكتروني *'),
            'name': _('الاسم'),
            'frequency': _('تكرار الإرسال')
        }

    def clean_email(self):
        """التحقق من البريد الإلكتروني للنشرة"""
        email = self.cleaned_data.get('email', '').strip().lower()

        # التحقق الأساسي
        validator = EmailValidator()
        try:
            validator(email)
        except ValidationError:
            raise ValidationError(_('البريد الإلكتروني غير صحيح'))

        return email

    def clean_name(self):
        """التحقق من الاسم للنشرة"""
        name = self.cleaned_data.get('name', '').strip()

        if name and len(name) < 2:
            raise ValidationError(_('الاسم قصير جداً'))

        if len(name) > 100:
            raise ValidationError(_('الاسم طويل جداً'))

        return name
class ContactMessageReplyForm(forms.Form):
    """نموذج الرد على رسائل التواصل (للإدارة)"""

    reply_message = forms.CharField(
        label=_('الرد'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 8,
            'placeholder': _('اكتب ردك هنا...')
        }),
        min_length=10,
        max_length=2000
    )

    send_copy_to_admin = forms.BooleanField(
        label=_('إرسال نسخة للإدارة'),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    mark_as_resolved = forms.BooleanField(
        label=_('تحديد كمحلولة'),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean_reply_message(self):
        """التحقق من الرد"""
        reply = self.cleaned_data.get('reply_message', '').strip()

        if len(reply) < 10:
            raise ValidationError(_('الرد قصير جداً'))

        if len(reply) > 2000:
            raise ValidationError(_('الرد طويل جداً'))

        return reply
class ContactMessageFilterForm(forms.Form):
    """نموذج فلترة رسائل التواصل (للإدارة)"""

    status = forms.ChoiceField(
        label=_('الحالة'),
        choices=[('', _('جميع الحالات'))] + ContactMessage.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    priority = forms.ChoiceField(
        label=_('الأولوية'),
        choices=[('', _('جميع الأولويات'))] + ContactMessage.PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    date_from = forms.DateField(
        label=_('من تاريخ'),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    date_to = forms.DateField(
        label=_('إلى تاريخ'),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    search = forms.CharField(
        label=_('البحث'),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('ابحث في الاسم، الإيميل، أو الموضوع...')
        })
    )
# Form Mixins للتحسينات المشتركة
class SpamProtectionMixin:
    """Mixin لحماية النماذج من الرسائل المزعجة"""

    def clean(self):
        cleaned_data = super().clean()

        # التحقق من سرعة الإرسال (Honeypot)
        honeypot = self.data.get('website')  # حقل مخفي
        if honeypot:
            raise ValidationError(_('تم اكتشاف نشاط مشبوه'))

        return cleaned_data
class RTLFormMixin:
    """Mixin لدعم النصوص العربية"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # إضافة class للدعم العربي
        for field in self.fields.values():
            if isinstance(field.widget, (forms.TextInput, forms.Textarea, forms.EmailInput)):
                field.widget.attrs.update({
                    'dir': 'rtl',
                    'lang': 'ar'
                })
# نماذج محسنة مع Mixins
class EnhancedContactForm(SpamProtectionMixin, RTLFormMixin, ContactForm):
    """نموذج تواصل محسن مع حماية إضافية"""

    # حقل مخفي لحماية من البوتات
    website = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        label=""
    )

    # checkbox الموافقة على الشروط
    accept_terms = forms.BooleanField(
        label=_('أوافق على شروط الاستخدام وسياسة الخصوصية'),
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'required': True
        })
    )

    def clean_accept_terms(self):
        """التحقق من الموافقة على الشروط"""
        accept = self.cleaned_data.get('accept_terms')
        if not accept:
            raise ValidationError(_('يجب الموافقة على الشروط للمتابعة'))
        return accept
class EnhancedNewsletterForm(SpamProtectionMixin, RTLFormMixin, NewsletterForm):
    """نموذج نشرة محسن"""

    website = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        label=""
    )

    topics = forms.MultipleChoiceField(
        label=_('المواضيع المفضلة'),
        choices=[
            ('projects', _('المشاريع والبرامج')),
            ('news', _('الأخبار والفعاليات')),
            ('volunteer', _('فرص التطوع')),
            ('donations', _('حملات التبرع')),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        })
    )
class CategoryForm(forms.ModelForm):
    """نموذج إضافة أو تعديل التصنيف"""

    class Meta:
        model = Category
        fields = ['category_ar', 'category_en']
        widgets = {
            'category_ar': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'أدخل اسم التصنيف بالعربية',
                'required': True
            }),
            'category_en': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name in English'
            }),
        }
        labels = {
            'category_ar': 'الاسم بالعربية',
            'category_en': 'الاسم بالإنجليزية'
        }
class FAQForm(forms.ModelForm):
    """نموذج إضافة وتعديل الأسئلة الشائعة"""

    class Meta:
        model = FAQ
        fields = [
            'question_ar', 'question_en',
            'answer_ar', 'answer_en',
            'category',
            'tags_ar', 'tags_en',
            'order', 'is_active'
        ]
        widgets = {
            'question_ar': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'أدخل السؤال بالعربية',
                'required': True
            }),
            'question_en': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter question in English'
            }),
            'answer_ar': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'أدخل الإجابة بالعربية',
                'required': True
            }),
            'answer_en': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter answer in English'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': 'اختر التصنيف'
            }),
            'tags_ar': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'افصل العلامات بفاصلة: دعم، تقني، مساعدة'
            }),
            'tags_en': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Separate tags with commas: support, tech, help'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': 'اتركه فارغاً للإضافة في النهاية'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'question_ar': 'السؤال بالعربية',
            'question_en': 'السؤال بالإنجليزية',
            'answer_ar': 'الإجابة بالعربية',
            'answer_en': 'الإجابة بالإنجليزية',
            'category': 'التصنيف',
            'tags_ar': 'العلامات (عربي)',
            'tags_en': 'العلامات (إنجليزي)',
            'order': 'الترتيب',
            'is_active': 'مفعّل'
        }

    def clean_order(self):
        """إضافة الترتيب التلقائي في النهاية إذا لم يتم إدخاله"""
        order = self.cleaned_data.get('order')
        if order is None or order == '':
            max_order = FAQ.objects.aggregate(models.Max('order'))['order__max']
            order = (max_order or 0) + 1
        return order

    def clean_tags_ar(self):
        """تنظيف العلامات العربية"""
        tags = self.cleaned_data.get('tags_ar', '')
        if tags:
            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            return ', '.join(tags_list)
        return ''

    def clean_tags_en(self):
        """تنظيف العلامات الإنجليزية"""
        tags = self.cleaned_data.get('tags_en', '')
        if tags:
            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            return ', '.join(tags_list)
        return ''
class FAQSearchForm(forms.Form):
    """نموذج البحث في الأسئلة الشائعة"""

    q = forms.CharField(
        label=_('كلمة البحث'),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('ابحث في السؤال أو الإجابة أو العلامات...'),
            'autocomplete': 'off'
        })
    )

    category = forms.ChoiceField(
        label=_('التصنيف'),
        required=False,
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # جلب التصنيفات من جدول Category
        categories = Category.objects.all().values_list('id', 'category_ar')
        choices = [('', _('جميع التصنيفات'))]
        choices.extend([(cat_id, cat_name) for cat_id, cat_name in categories])

        self.fields['category'].choices = choices





from django import forms
from django.utils.translation import gettext_lazy as _
# من المفترض أن تقوم باستيراد ContactInfo من مكانها الصحيح
# from .models import ContactInfo

class ContactInfoForm(forms.ModelForm):
    """نموذج إضافة وتعديل معلومات الاتصال"""

    # قائمة الأيقونات الخام
    RAW_ICONS = [
        ('fas fa-phone', 'هاتف - Phone'),
        ('fas fa-phone-alt', 'هاتف بديل - Phone Alt'),
        ('fas fa-mobile-alt', 'موبايل - Mobile'),
        ('fas fa-envelope', 'بريد - Envelope'),
        ('fas fa-envelope-open', 'بريد مفتوح - Envelope Open'),
        ('fas fa-at', 'إيميل @ - At'),
        ('fas fa-map-marker-alt', 'موقع - Map Marker'),
        ('fas fa-map-pin', 'دبوس خريطة - Map Pin'),
        ('fas fa-map-marked-alt', 'خريطة - Map Marked'),
        ('fas fa-home', 'منزل - Home'),
        ('fas fa-building', 'مبنى - Building'),
        ('fas fa-fax', 'فاكس - Fax'),
        ('fas fa-print', 'طابعة - Print'),
        ('fas fa-mailbox', 'صندوق بريد - Mailbox'),
        ('fas fa-inbox', 'بريد وارد - Inbox'),
        ('fas fa-globe', 'موقع إلكتروني - Globe'),
        ('fas fa-globe-africa', 'عالمي - Globe Africa'),
        ('fas fa-link', 'رابط - Link'),
        ('fas fa-external-link-alt', 'رابط خارجي - External Link'),
        ('fas fa-info-circle', 'معلومات - Info Circle'),
        ('fas fa-address-card', 'بطاقة - Address Card'),
        ('fas fa-id-card', 'هوية - ID Card'),
    ]

    ICON_CHOICES = RAW_ICONS

    icon_class = forms.ChoiceField(
        choices=ICON_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'icon-radio'}),
        label=_('اختر الأيقونة'),
        required=False
    )

    class Meta:
        model = ContactInfo
        # ✅ التعديل: استبدال 'value' بـ 'value_ar' و 'value_en'
        fields = ['type', 'value_ar', 'value_en', 'icon_class', 'order', 'show_in_footer', 'is_active']

        widgets = {
            'type': forms.Select(attrs={'class': 'form-select'}),
            # ✅ التعديل: إضافة حقول القيمة الثنائية اللغة
            'value_ar': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('القيمة بالعربية'), 'dir': 'rtl'}),
            'value_en': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('القيمة بالإنجليزية'), 'dir': 'ltr'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'show_in_footer': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.used_types = kwargs.pop('used_types', [])
        self.used_icons = kwargs.pop('used_icons', [])
        self.info_instance = kwargs.get('instance')

        super().__init__(*args, **kwargs)

        # تصفية الأنواع المستخدمة (فقط في حالة الإضافة)
        if not self.instance.pk:
            if self.used_types:
                available_choices = [
                    choice for choice in ContactInfo.INFO_TYPES
                    if choice[0] not in self.used_types
                ]
                self.fields['type'].choices = available_choices

