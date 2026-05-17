from django import forms
from django.utils.translation import gettext_lazy as _
from .models import ProjectCategory, Project
from django_ckeditor_5.widgets import CKEditor5Widget


class ProjectCategoryForm(forms.ModelForm):
    """نموذج إضافة وتعديل فئة مشروع"""

    ICON_CHOICES = [
        ('fas fa-heart', _('قلب - Heart')),
        ('fas fa-hand-holding-heart', _('يد تحمل قلب - Hand Heart')),
        ('fas fa-hands-helping', _('أيادي متعاونة - Helping Hands')),
        ('fas fa-donate', _('تبرع - Donate')),
        ('fas fa-gift', _('هدية - Gift')),
        ('fas fa-charity', _('خيرية - Charity')),
        ('fas fa-hand-holding-usd', _('يد تحمل مال - Hand Money')),
        ('fas fa-people-carry', _('أشخاص يحملون - People Carry')),
        ('fas fa-hospital', _('مستشفى - Hospital')),
        ('fas fa-medkit', _('حقيبة طبية - Medkit')),
        ('fas fa-clinic-medical', _('عيادة - Clinic')),
        ('fas fa-stethoscope', _('سماعة طبية - Stethoscope')),
        ('fas fa-pills', _('أدوية - Pills')),
        ('fas fa-syringe', _('حقنة - Syringe')),
        ('fas fa-heartbeat', _('نبضات - Heartbeat')),
        ('fas fa-user-md', _('طبيب - Doctor')),
        ('fas fa-school', _('مدرسة - School')),
        ('fas fa-graduation-cap', _('قبعة تخرج - Graduation')),
        ('fas fa-book', _('كتاب - Book')),
        ('fas fa-book-reader', _('قارئ - Reader')),
        ('fas fa-pencil-alt', _('قلم رصاص - Pencil')),
        ('fas fa-chalkboard-teacher', _('معلم - Teacher')),
        ('fas fa-university', _('جامعة - University')),
        ('fas fa-child', _('طفل - Child')),
        ('fas fa-baby', _('رضيع - Baby')),
        ('fas fa-users', _('مجموعة - Users')),
        ('fas fa-user-friends', _('أصدقاء - Friends')),
        ('fas fa-user-shield', _('حماية - Protection')),
        ('fas fa-home', _('منزل - Home')),
        ('fas fa-house-user', _('منزل عائلي - Family Home')),
        ('fas fa-mosque', _('مسجد - Mosque')),
        ('fas fa-praying-hands', _('أيادي داعية - Praying')),
        ('fas fa-hands', _('أيادي - Hands')),
        ('fas fa-hand-peace', _('سلام - Peace')),
        ('fas fa-dove', _('حمامة - Dove')),
        ('fas fa-water', _('ماء - Water')),
        ('fas fa-tint', _('قطرة ماء - Water Drop')),
        ('fas fa-faucet', _('صنبور - Faucet')),
        ('fas fa-shower', _('دش - Shower')),
        ('fas fa-bread-slice', _('خبز - Bread')),
        ('fas fa-utensils', _('أدوات طعام - Utensils')),
        ('fas fa-apple-alt', _('تفاحة - Apple')),
        ('fas fa-carrot', _('جزر - Carrot')),
        ('fas fa-seedling', _('بذرة - Seedling')),
        ('fas fa-tree', _('شجرة - Tree')),
        ('fas fa-leaf', _('ورقة شجر - Leaf')),
        ('fas fa-solar-panel', _('طاقة شمسية - Solar')),
        ('fas fa-recycle', _('إعادة تدوير - Recycle')),
        ('fas fa-globe', _('كرة أرضية - Globe')),
        ('fas fa-globe-africa', _('إفريقيا - Africa')),
        ('fas fa-map-marked-alt', _('خريطة - Map')),
        ('fas fa-building', _('مبنى - Building')),
        ('fas fa-city', _('مدينة - City')),
        ('fas fa-warehouse', _('مستودع - Warehouse')),
        ('fas fa-tools', _('أدوات - Tools')),
        ('fas fa-hammer', _('مطرقة - Hammer')),
        ('fas fa-wrench', _('مفتاح ربط - Wrench')),
        ('fas fa-hard-hat', _('خوذة - Hard Hat')),
        ('fas fa-briefcase', _('حقيبة - Briefcase')),
        ('fas fa-handshake', _('مصافحة - Handshake')),
        ('fas fa-clipboard-list', _('قائمة - List')),
        ('fas fa-tasks', _('مهام - Tasks')),
        ('fas fa-project-diagram', _('مخطط - Diagram')),
        ('fas fa-lightbulb', _('مصباح - Lightbulb')),
        ('fas fa-shopping-cart', _('عربة - Cart')),
        ('fas fa-truck', _('شاحنة - Truck')),
        ('fas fa-box', _('صندوق - Box')),
        ('fas fa-boxes', _('صناديق - Boxes')),
        ('fas fa-pallet', _('منصة - Pallet')),
        ('fas fa-wheelchair', _('كرسي متحرك - Wheelchair')),
        ('fas fa-accessible-icon', _('إمكانية الوصول - Accessible')),
        ('fas fa-blind', _('كفيف - Blind')),
        ('fas fa-deaf', _('أصم - Deaf')),
        ('fas fa-phone', _('هاتف - Phone')),
        ('fas fa-mobile-alt', _('موبايل - Mobile')),
        ('fas fa-envelope', _('بريد - Envelope')),
        ('fas fa-bullhorn', _('مكبر صوت - Bullhorn')),
        ('fas fa-microphone', _('ميكروفون - Microphone')),
        ('fas fa-video', _('فيديو - Video')),
        ('fas fa-camera', _('كاميرا - Camera')),
        ('fas fa-calculator', _('آلة حاسبة - Calculator')),
        ('fas fa-coins', _('نقود - Coins')),
        ('fas fa-dollar-sign', _('دولار - Dollar')),
        ('fas fa-chart-line', _('رسم بياني - Chart')),
        ('fas fa-chart-pie', _('دائرة بيانية - Pie Chart')),
        ('fas fa-percentage', _('نسبة مئوية - Percentage')),
        ('fas fa-award', _('جائزة - Award')),
        ('fas fa-medal', _('ميدالية - Medal')),
        ('fas fa-trophy', _('كأس - Trophy')),
        ('fas fa-star', _('نجمة - Star')),
        ('fas fa-certificate', _('شهادة - Certificate')),
        ('fas fa-thumbs-up', _('إعجاب - Thumbs Up')),
        ('fas fa-flag', _('علم - Flag')),
        ('fas fa-rocket', _('صاروخ - Rocket')),
        ('fas fa-bullseye', _('هدف - Bullseye')),
        ('fas fa-crosshairs', _('تصويب - Crosshairs')),
        ('fas fa-eye', _('عين - Eye')),
        ('fas fa-glasses', _('نظارات - Glasses')),
        ('fas fa-sun', _('شمس - Sun')),
        ('fas fa-moon', _('قمر - Moon')),
        ('fas fa-cloud', _('سحابة - Cloud')),
        ('fas fa-umbrella', _('مظلة - Umbrella')),
    ]

    icon = forms.ChoiceField(
        choices=ICON_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'icon-radio'}),
        label=_('اختر الأيقونة'),
        required=False
    )

    class Meta:
        model = ProjectCategory
        fields = ['name_ar', 'name_en', 'slug', 'description_ar', 'description_en',
                  'icon', 'color', 'image', 'order', 'is_active']
        labels = {
            'name_ar': _('اسم الفئة بالعربية'),
            'name_en': _('اسم الفئة بالإنجليزية'),
            'slug': _('الرابط'),
            'description_ar': _('الوصف بالعربية'),
            'description_en': _('الوصف بالإنجليزية'),
            'color': _('لون الفئة'),
            'image': _('صورة الفئة'),
            'order': _('الترتيب'),
            'is_active': _('مفعل'),
        }
        widgets = {
            'name_ar': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('اسم الفئة بالعربية')}),
            'name_en': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Category Name in English')}),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('سيتم التعبئة تلقائياً'),
                'readonly': True,
                'style': 'background-color: #e9ecef; cursor: not-allowed;'
            }),
            'description_ar': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'description_en': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.used_icons = kwargs.pop('used_icons', [])
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.icon:
            current_icon = self.instance.icon
            if current_icon in self.used_icons:
                self.used_icons.remove(current_icon)


class ProjectForm(forms.ModelForm):
    """نموذج إضافة وتعديل مشروع"""

    class Meta:
        model = Project
        fields = [
            'title_ar', 'title_en', 'slug', 'category',
            'summary_ar', 'summary_en',
            'description_ar', 'description_en',
            'main_image',
            'status', 'priority',
            'start_date', 'end_date',
            'target_amount', 'raised_amount',
            'beneficiaries_count', 'target_beneficiaries',
            'location_ar', 'location_en',
            'keywords_ar', 'keywords_en',
            'is_featured', 'is_active', 'allow_comments',
            'meta_description_ar', 'meta_description_en'
        ]

        labels = {
            'title_ar': _('عنوان المشروع بالعربية'),
            'title_en': _('عنوان المشروع بالإنجليزية'),
            'slug': _('الرابط'),
            'category': _('الفئة'),
            'summary_ar': _('ملخص المشروع بالعربية'),
            'summary_en': _('ملخص المشروع بالإنجليزية'),
            'description_ar': _('وصف المشروع بالعربية'),
            'description_en': _('وصف المشروع بالإنجليزية'),
            'main_image': _('الصورة الرئيسية'),
            'status': _('حالة المشروع'),
            'priority': _('الأولوية'),
            'start_date': _('تاريخ البداية'),
            'end_date': _('تاريخ النهاية'),
            'target_amount': _('المبلغ المستهدف'),
            'raised_amount': _('المبلغ المجمع'),
            'beneficiaries_count': _('عدد المستفيدين'),
            'target_beneficiaries': _('المستفيدين المستهدفين'),
            'location_ar': _('الموقع بالعربية'),
            'location_en': _('الموقع بالإنجليزية'),
            'keywords_ar': _('كلمات مفتاحية بالعربية'),
            'keywords_en': _('كلمات مفتاحية بالإنجليزية'),
            'is_featured': _('مشروع مميز'),
            'is_active': _('مفعل'),
            'allow_comments': _('السماح بالتعليقات'),
            'meta_description_ar': _('وصف SEO بالعربية'),
            'meta_description_en': _('وصف SEO بالإنجليزية'),
        }

        widgets = {
            'title_ar': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('عنوان المشروع')
            }),
            'title_en': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Project Title')
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'project-slug'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'summary_ar': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'summary_en': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'description_ar': CKEditor5Widget(attrs={
                'class': 'django_ckeditor_5'
            }),
            'description_en': CKEditor5Widget(attrs={
                'class': 'django_ckeditor_5'
            }),
            'main_image': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'target_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'raised_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'beneficiaries_count': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'target_beneficiaries': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'location_ar': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('غزة، فلسطين')
            }),
            'location_en': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Gaza, Palestine')
            }),
            'keywords_ar': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('خيري, تنمية, تعليم')
            }),
            'keywords_en': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('charity, development, education')
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'allow_comments': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'meta_description_ar': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'maxlength': 160
            }),
            'meta_description_en': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'maxlength': 160
            }),
        }

    def clean_slug(self):
        """التحقق من صحة الـ slug"""
        slug = self.cleaned_data.get('slug')
        if slug:
            slug = slug.lower().strip()
            if self.instance.pk:
                if Project.objects.exclude(pk=self.instance.pk).filter(slug=slug).exists():
                    raise forms.ValidationError(_('هذا الرابط مستخدم بالفعل'))
            else:
                if Project.objects.filter(slug=slug).exists():
                    raise forms.ValidationError(_('هذا الرابط مستخدم بالفعل'))
        return slug

    def clean(self):
        """التحقق من صحة البيانات"""
        cleaned_data = super().clean()

        # ✅ التحقق من التواريخ — فقط إذا كان الاثنان موجودَين
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError(_('تاريخ النهاية يجب أن يكون بعد تاريخ البداية'))

        # ✅ التحقق من المبالغ — فقط إذا كان الاثنان موجودَين
        target_amount = cleaned_data.get('target_amount')
        raised_amount = cleaned_data.get('raised_amount')

        if target_amount is not None and raised_amount is not None:
            if raised_amount > target_amount:
                self.add_error('raised_amount', _('المبلغ المجمع لا يمكن أن يكون أكبر من المبلغ المستهدف'))

        # ✅ التحقق من المستفيدين — فقط إذا كان الاثنان موجودَين
        target_beneficiaries = cleaned_data.get('target_beneficiaries')
        beneficiaries_count = cleaned_data.get('beneficiaries_count')

        if target_beneficiaries is not None and beneficiaries_count is not None:
            if beneficiaries_count > target_beneficiaries:
                self.add_error('beneficiaries_count', _('عدد المستفيدين لا يمكن أن يكون أكبر من المستفيدين المستهدفين'))

        return cleaned_data