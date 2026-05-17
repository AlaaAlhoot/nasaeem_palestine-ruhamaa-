from django import forms
from django.utils.translation import gettext_lazy as _
from django.db import models

from contact.models import ContactMessage, SocialMediaContact
from main.models import *


# ==================== نموذج شرائح السلايدر ====================
class HomeSliderForm(forms.ModelForm):
    """نموذج شرائح السلايدر"""

    class Meta:
        model = HomeSlider
        fields = [
            'title_ar', 'title_en', 'subtitle_ar', 'subtitle_en',
            'description_ar', 'description_en', 'image',
            'button_text_ar', 'button_text_en', 'button_url',
            'order', 'is_active'
        ]
        widgets = {
            'title_ar': forms.TextInput(attrs={'class': 'form-control', 'dir': 'rtl'}),
            'title_en': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'subtitle_ar': forms.TextInput(attrs={'class': 'form-control', 'dir': 'rtl'}),
            'subtitle_en': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'description_ar': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'dir': 'rtl'}),
            'description_en': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'dir': 'ltr'}),
            'button_text_ar': forms.TextInput(attrs={'class': 'form-control', 'dir': 'rtl'}),
            'button_text_en': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'button_url': forms.URLInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }


# ==================== نموذج صفحة من نحن ====================
class AboutPageForm(forms.ModelForm):
    """نموذج صفحة من نحن"""

    class Meta:
        model = AboutPage
        fields = [
            'title_ar', 'title_en', 'content_ar', 'content_en',
            'image', 'meta_description_ar', 'meta_description_en', 'is_active'
        ]
        widgets = {
            'title_ar': forms.TextInput(attrs={
                'class': 'form-control',
                'dir': 'rtl',
                'placeholder': _('أدخل العنوان بالعربية')
            }),
            'title_en': forms.TextInput(attrs={
                'class': 'form-control',
                'dir': 'ltr',
                'placeholder': _('أدخل العنوان بالإنجليزية')
            }),
            'content_ar': forms.Textarea(attrs={
                'class': 'form-control w-100',
                'rows': 8,
                'dir': 'rtl',
                'placeholder': _('أدخل المحتوى بالعربية')
            }),
            'content_en': forms.Textarea(attrs={
                'class': 'form-control w-100',
                'rows': 8,
                'dir': 'ltr',
                'placeholder': _('أدخل المحتوى بالإنجليزية')
            }),
            'meta_description_ar': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'dir': 'rtl',
                'placeholder': _('وصف SEO بالعربية')
            }),
            'meta_description_en': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'dir': 'ltr',
                'placeholder': _('وصف SEO بالإنجليزية')
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }


# ==================== نموذج صفحة الرؤية والرسالة ====================
class VisionPageForm(forms.ModelForm):
    """نموذج صفحة الرؤية والرسالة"""

    class Meta:
        model = VisionPage
        fields = [
            'vision_title_ar', 'vision_title_en', 'vision_content_ar', 'vision_content_en',
            'mission_title_ar', 'mission_title_en', 'mission_content_ar', 'mission_content_en',
            'values_title_ar', 'values_title_en',
            'vision_image', 'mission_image', 'values_image',
            'meta_description_ar', 'meta_description_en', 'is_active'
        ]
        widgets = {
            'vision_title_ar': forms.TextInput(attrs={
                'class': 'form-control',
                'dir': 'rtl',
                'placeholder': _('عنوان الرؤية بالعربية')
            }),
            'vision_title_en': forms.TextInput(attrs={
                'class': 'form-control',
                'dir': 'ltr',
                'placeholder': _('عنوان الرؤية بالإنجليزية')
            }),
            'vision_content_ar': forms.Textarea(attrs={
                'class': 'form-control w-100',
                'rows': 8,
                'dir': 'rtl',
                'placeholder': _('محتوى الرؤية بالعربية')
            }),
            'vision_content_en': forms.Textarea(attrs={
                'class': 'form-control w-100',
                'rows': 8,
                'dir': 'ltr',
                'placeholder': _('محتوى الرؤية بالإنجليزية')
            }),
            'mission_title_ar': forms.TextInput(attrs={
                'class': 'form-control',
                'dir': 'rtl',
                'placeholder': _('عنوان الرسالة بالعربية')
            }),
            'mission_title_en': forms.TextInput(attrs={
                'class': 'form-control',
                'dir': 'ltr',
                'placeholder': _('عنوان الرسالة بالإنجليزية')
            }),
            'mission_content_ar': forms.Textarea(attrs={
                'class': 'form-control w-100',
                'rows': 8,
                'dir': 'rtl',
                'placeholder': _('محتوى الرسالة بالعربية')
            }),
            'mission_content_en': forms.Textarea(attrs={
                'class': 'form-control w-100',
                'rows': 8,
                'dir': 'ltr',
                'placeholder': _('محتوى الرسالة بالإنجليزية')
            }),
            'values_title_ar': forms.TextInput(attrs={
                'class': 'form-control',
                'dir': 'rtl',
                'placeholder': _('عنوان القيم بالعربية')
            }),
            'values_title_en': forms.TextInput(attrs={
                'class': 'form-control',
                'dir': 'ltr',
                'placeholder': _('عنوان القيم بالإنجليزية')
            }),


            'meta_description_ar': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'dir': 'rtl',
                'placeholder': _('وصف SEO بالعربية')
            }),
            'meta_description_en': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'dir': 'ltr',
                'placeholder': _('وصف SEO بالإنجليزية')
            }),
            'vision_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'mission_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'values_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }


# ==================== نموذج الأهداف ====================
class GoalForm(forms.ModelForm):
    """نموذج إضافة وتعديل الأهداف"""

    # قائمة 50 أيقونة مقترحة مع أسمائها
    ICON_CHOICES = [
        # أيقونات دينية وإسلامية
        ('fas fa-mosque', _('مسجد - Mosque')),
        ('fas fa-quran', _('قرآن كريم - Quran')),
        ('fas fa-kaaba', _('كعبة - Kaaba')),
        ('fas fa-praying-hands', _('دعاء - Praying Hands')),
        ('fas fa-moon', _('هلال - Moon')),
        ('fas fa-star-and-crescent', _('هلال ونجمة - Star and Crescent')),

        # أيقونات الأهداف والإنجاز
        ('fas fa-bullseye', _('هدف - Bullseye')),
        ('fas fa-target', _('هدف محدد - Target')),
        ('fas fa-trophy', _('كأس - Trophy')),
        ('fas fa-medal', _('ميدالية - Medal')),
        ('fas fa-award', _('جائزة - Award')),
        ('fas fa-flag-checkered', _('علم إنجاز - Checkered Flag')),

        # أيقونات المساعدة والعطاء
        ('fas fa-hands-helping', _('المساعدة - Helping Hands')),
        ('fas fa-hand-holding-heart', _('عطاء - Hand Holding Heart')),
        ('fas fa-handshake', _('تعاون - Handshake')),
        ('fas fa-donate', _('تبرع - Donate')),
        ('fas fa-gift', _('هدية - Gift')),
        ('fas fa-hand-holding-usd', _('دعم مالي - Hand Holding Money')),

        # أيقونات التعليم والمعرفة
        ('fas fa-graduation-cap', _('تخرج - Graduation Cap')),
        ('fas fa-book', _('كتاب - Book')),
        ('fas fa-book-open', _('كتاب مفتوح - Open Book')),
        ('fas fa-book-reader', _('قارئ - Book Reader')),
        ('fas fa-user-graduate', _('خريج - Graduate')),
        ('fas fa-chalkboard-teacher', _('معلم - Teacher')),
        ('fas fa-pencil-alt', _('قلم - Pencil')),

        # أيقونات الصحة والرعاية
        ('fas fa-heart', _('قلب - Heart')),
        ('fas fa-heartbeat', _('نبض - Heartbeat')),
        ('fas fa-medkit', _('طبي - Medical Kit')),
        ('fas fa-hospital', _('مستشفى - Hospital')),
        ('fas fa-first-aid', _('إسعافات أولية - First Aid')),
        ('fas fa-stethoscope', _('سماعة طبية - Stethoscope')),

        # أيقونات العائلة والمجتمع
        ('fas fa-users', _('مجموعة - Users')),
        ('fas fa-user-friends', _('أصدقاء - Friends')),
        ('fas fa-child', _('طفل - Child')),
        ('fas fa-baby', _('رضيع - Baby')),
        ('fas fa-female', _('امرأة - Female')),
        ('fas fa-male', _('رجل - Male')),
        ('fas fa-home', _('منزل - Home')),
        ('fas fa-home-heart', _('منزل مع قلب - Home Heart')),

        # أيقونات العمل والبناء
        ('fas fa-hammer', _('عامل - Hammer')),
        ('fas fa-tools', _('أدوات - Tools')),
        ('fas fa-hard-hat', _('خوذة عامل - Hard Hat')),
        ('fas fa-building', _('بناء - Building')),
        ('fas fa-city', _('مدينة - City')),

        # أيقونات النمو والتطوير
        ('fas fa-seedling', _('نمو - Seedling')),
        ('fas fa-tree', _('شجرة - Tree')),
        ('fas fa-leaf', _('ورقة شجر - Leaf')),
        ('fas fa-chart-line', _('نمو متصاعد - Chart Line')),
        ('fas fa-arrow-up', _('تصاعد - Arrow Up')),
        ('fas fa-lightbulb', _('فكرة - Lightbulb')),
        ('fas fa-brain', _('عقل - Brain')),
        ('fas fa-star', _('نجمة - Star')),
    ]

    icon = forms.ChoiceField(
        choices=ICON_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'icon-radio'}),
        label=_('اختر الأيقونة')
    )

    class Meta:
        model = Goal
        fields = ['title_ar', 'title_en', 'description_ar', 'description_en', 'icon', 'order', 'is_active']
        widgets = {
            'title_ar': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('أدخل عنوان الهدف بالعربية'),
                'required': True
            }),
            'title_en': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('أدخل عنوان الهدف بالإنجليزية')
            }),
            'description_ar': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('أدخل وصف الهدف بالعربية')
            }),
            'description_en': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('أدخل وصف الهدف بالإنجليزية')
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': _('اتركه فارغاً للإضافة في النهاية')
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'checked': True
            })
        }
        labels = {
            'title_ar': _('العنوان بالعربية'),
            'title_en': _('العنوان بالإنجليزية'),
            'description_ar': _('الوصف بالعربية'),
            'description_en': _('الوصف بالإنجليزية'),
            'order': _('الترتيب'),
            'is_active': _('مفعّل')
        }

    def __init__(self, *args, **kwargs):
        self.goal_instance = kwargs.get('instance')
        self.used_icons = kwargs.pop('used_icons', [])
        super().__init__(*args, **kwargs)

        self.fields['order'].required = False

        if self.used_icons:
            available_choices = []
            for choice in self.ICON_CHOICES:
                icon_value = choice[0]
                if icon_value in self.used_icons and (not self.goal_instance or self.goal_instance.icon != icon_value):
                    available_choices.append((icon_value, f"{choice[1]} ✓ ({_('مستخدمة')})", {'disabled': True}))
                else:
                    available_choices.append(choice)

    def clean_order(self):
        """إضافة الترتيب التلقائي في النهاية إذا لم يتم إدخاله"""
        order = self.cleaned_data.get('order')

        if order is None or order == '':
            max_order = Goal.objects.aggregate(models.Max('order'))['order__max']
            order = (max_order or 0) + 1

        return order

    def clean_icon(self):
        """التحقق من أن الأيقونة غير مستخدمة"""
        icon = self.cleaned_data.get('icon')

        if self.goal_instance and self.goal_instance.icon == icon:
            return icon

        if Goal.objects.filter(icon=icon).exists():
            raise forms.ValidationError(_('هذه الأيقونة مستخدمة بالفعل. الرجاء اختيار أيقونة أخرى.'))

        return icon


# ==================== نموذج أعضاء مجلس الإدارة ====================
class BoardMemberForm(forms.ModelForm):
    """نموذج إضافة وتعديل أعضاء مجلس الإدارة"""

    class Meta:
        model = BoardMember
        fields = [
            'name_ar', 'name_en',
            'position_type_ar', 'position_type_en', 'position_type', 'is_custom_position',
            'bio_ar', 'bio_en',
            'photo',
            'email', 'phone',
            'facebook_url', 'twitter_url', 'linkedin_url',
            'order', 'is_active'
        ]

        labels = {
            'name_ar': _('الاسم بالعربية'),
            'name_en': _('الاسم بالإنجليزية'),
            'position_type_ar': _('نوع المنصب بالعربية'),
            'position_type_en': _('نوع المنصب بالإنجليزية'),
            'position_type': _('المنصب من القائمة'),
            'is_custom_position': _('منصب مخصص'),
            'bio_ar': _('نبذة شخصية بالعربية'),
            'bio_en': _('نبذة شخصية بالإنجليزية'),
            'photo': _('الصورة الشخصية'),
            'email': _('البريد الإلكتروني'),
            'phone': _('رقم الهاتف'),
            'facebook_url': _('رابط الفيسبوك'),
            'twitter_url': _('رابط تويتر'),
            'linkedin_url': _('رابط لينكدإن'),
            'order': _('الترتيب'),
            'is_active': _('مفعل'),
        }

        widgets = {
            'name_ar': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('أدخل الاسم بالعربية')
            }),
            'name_en': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter name in English')
            }),

            # ✅ حقل المنصب - يتحول بين select و input
            'position_type_ar': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('اختر من القائمة أو اكتب منصباً مخصصاً'),
                'id': 'id_position_type_ar'
            }),

            # ✅ الترجمة الإنجليزية - معطل افتراضياً
            'position_type_en': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('English translation (auto-filled)'),
                'readonly': 'readonly',
                'style': 'background-color: #e9ecef;',
                'id': 'id_position_type_en'
            }),

            # ✅ القائمة المنسدلة (مخفية افتراضياً)
            'position_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_position_type'
            }),

            # ✅ Checkbox للمنصب المخصص
            'is_custom_position': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_is_custom_position'
            }),

            'bio_ar': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('أدخل نبذة شخصية بالعربية')
            }),
            'bio_en': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Enter bio in English')
            }),
            'photo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '05XXXXXXXX'
            }),
            'facebook_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://facebook.com/...'
            }),
            'twitter_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://twitter.com/...'
            }),
            'linkedin_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://linkedin.com/...'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'value': 0
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean(self):
        """التحقق من صحة البيانات"""
        cleaned_data = super().clean()
        is_custom = cleaned_data.get('is_custom_position', False)
        position_type_ar = cleaned_data.get('position_type_ar', '').strip()
        position_type_en = cleaned_data.get('position_type_en', '').strip()
        position_type = cleaned_data.get('position_type')

        # ✅ إذا كان منصباً مخصصاً
        if is_custom:
            if not position_type_ar:
                self.add_error('position_type_ar', _('يجب إدخال نوع المنصب بالعربية'))
            if not position_type_en:
                self.add_error('position_type_en', _('يجب إدخال نوع المنصب بالإنجليزية'))
            # إفراغ position_type للمناصب المخصصة
            cleaned_data['position_type'] = None
        else:
            # ✅ إذا كان من القائمة
            if not position_type:
                self.add_error('position_type', _('يجب اختيار نوع المنصب'))

            # تعيين الترجمة التلقائية
            if position_type:
                position_dict = dict(BoardMember.POSITION_CHOICES)
                cleaned_data['position_type_ar'] = position_dict.get(position_type, '')
                cleaned_data['position_type_en'] = BoardMember.POSITION_TRANSLATIONS.get(
                    position_type,
                    ''
                )

        return cleaned_data

# ==================== نموذج الرد على رسائل التواصل ====================
class ContactMessageReplyForm(forms.ModelForm):
    """نموذج الرد على رسائل التواصل"""

    class Meta:
        model = ContactMessage
        fields = ['reply_message', 'status']
        widgets = {
            'reply_message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': _('اكتب الرد هنا...'),
                'required': True
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            })
        }
        labels = {
            'reply_message': _('الرد'),
            'status': _('حالة الرسالة')
        }


# ==================== نموذج روابط التواصل الاجتماعي ====================
class SocialMediaContactForm(forms.ModelForm):
    """نموذج إضافة وتعديل روابط التواصل الاجتماعي"""

    class Meta:
        model = SocialMediaContact
        fields = ['platform', 'username', 'url', 'order', 'is_active']
        widgets = {
            'platform': forms.Select(attrs={
                'class': 'form-select',
                'id': 'add_social_platform'
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('اسم المستخدم')
            }),
            'url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://...'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'value': 0
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            available_platforms = SocialMediaContact.get_available_platforms()
            self.fields['platform'].choices = [('', _('-- اختر المنصة --'))] + available_platforms

            if not available_platforms:
                self.fields['platform'].choices = [('', _('جميع المنصات مضافة'))]
                self.fields['platform'].disabled = True
        else:
            self.fields['platform'].widget = forms.HiddenInput()


# ==================== نموذج الإحصائيات ====================
class StatisticForm(forms.ModelForm):
    class Meta:
        model = Statistic
        fields = [
            'title_ar', 'title_en', 'number', 'suffix_ar', 'suffix_en',
            'icon', 'color', 'order', 'auto_update_from', 'is_active'
        ]
        widgets = {
            'title_ar': forms.TextInput(attrs={'class': 'form-control', 'dir': 'rtl'}),
            'title_en': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'number': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'required': False  # ✅ ليس مطلوباً دائماً
            }),
            'suffix_ar': forms.TextInput(attrs={'class': 'form-control', 'dir': 'rtl'}),
            'suffix_en': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'icon': forms.TextInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'auto_update_from': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ✅ جعل حقل الرقم غير مطلوب في التحقق
        self.fields['number'].required = False

    def clean(self):
        cleaned_data = super().clean()
        auto_update = cleaned_data.get('auto_update_from')
        number = cleaned_data.get('number')

        # ✅ إذا اختار تحديث تلقائي، اجعل الرقم 0
        if auto_update:
            cleaned_data['number'] = 0
        # ✅ إذا لم يختر تحديث تلقائي والرقم فارغ، خطأ
        elif number is None or number == '':
            self.add_error('number', 'الرقم مطلوب عند عدم اختيار التحديث التلقائي')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # ✅ إذا كان هناك تحديث تلقائي، احسب الرقم الآن
        if instance.auto_update_from:
            # تأكد من وجود update_number في Model
            if hasattr(instance, 'update_number'):
                instance.number = 0  # مؤقت قبل الحفظ
                if commit:
                    instance.save()
                    instance.update_number()  # التحديث بعد الحفظ
            else:
                instance.number = 0
                if commit:
                    instance.save()
        else:
            if commit:
                instance.save()

        return instance



# ==================== نموذج الشركاء ====================
class PartnerForm(forms.ModelForm):
    """نموذج إضافة وتعديل الشركاء"""

    class Meta:
        model = Partner
        fields = ['name_ar', 'name_en', 'logo', 'description_ar', 'description_en',
                  'partnership_date', 'projects_count', 'website', 'email', 'phone',
                  'order', 'is_active']
        widgets = {
            'name_ar': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('اسم الشريك بالعربية')
            }),
            'name_en': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('اسم الشريك بالإنجليزية')
            }),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'description_ar': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'maxlength': 500,
                'placeholder': _('وصف مختصر بالعربية')
            }),
            'description_en': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'maxlength': 500,
                'placeholder': _('وصف مختصر بالإنجليزية')
            }),
            'partnership_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'projects_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': _('عدد المشاريع المنفذة')
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://...'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+970...'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': _('الترتيب')
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


