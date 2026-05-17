from django import forms

from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, Field, HTML
from crispy_forms.bootstrap import PrependedText, AppendedText
from contact.models import ContactMessage, Newsletter,ContactInfo
from .models import UserProfile, SiteSetting, NotificationSettings, QuickAction
from main.models import SiteSettings, HomeSlider, Statistic
from projects.models import Project, ProjectCategory
from django.contrib.auth import get_user_model
User = get_user_model()

class UserProfileForm(forms.ModelForm):
    """نموذج تحرير الملف الشخصي"""

    class Meta:
        model = UserProfile
        fields = [
            'full_name_ar', 'full_name_en', 'avatar', 'phone', 'bio',
            'role', 'department', 'dashboard_theme', 'language_preference',
            'items_per_page', 'email_notifications', 'browser_notifications',
            'sms_notifications'
        ]
        widgets = {
            'full_name_ar': forms.TextInput(attrs={'class': 'form-control', 'dir': 'rtl'}),
            'full_name_en': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'dir': 'rtl'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'dir': 'rtl'}),
            'dashboard_theme': forms.Select(attrs={'class': 'form-select'}),
            'language_preference': forms.Select(attrs={'class': 'form-select'}),
            'items_per_page': forms.NumberInput(attrs={'class': 'form-control', 'min': '10', 'max': '100'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # إخفاء حقل الدور لغير الإداريين
        if self.user and not self.user.profile.is_admin():
            self.fields['role'].widget = forms.HiddenInput()

        # إعداد Crispy Forms
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'needs-validation'
        self.helper.layout = Layout(
            Div(
                Div('full_name_ar', css_class='col-md-6'),
                Div('full_name_en', css_class='col-md-6'),
                css_class='row'
            ),
            Div(
                Div('phone', css_class='col-md-6'),
                Div('department', css_class='col-md-6'),
                css_class='row'
            ),
            'bio',
            'avatar',
            HTML('<hr>'),
            HTML('<h5>إعدادات اللوحة</h5>'),
            Div(
                Div('dashboard_theme', css_class='col-md-4'),
                Div('language_preference', css_class='col-md-4'),
                Div('items_per_page', css_class='col-md-4'),
                css_class='row'
            ),
            HTML('<h5>إعدادات الإشعارات</h5>'),
            Div(
                Field('email_notifications', css_class='form-check-input'),
                Field('browser_notifications', css_class='form-check-input'),
                Field('sms_notifications', css_class='form-check-input'),
                css_class='row'
            ),
            'role',
            Submit('submit', 'حفظ التغييرات', css_class='btn btn-primary')
        )
class UserCreateForm(UserCreationForm):
    """نموذج إنشاء مستخدم جديد"""

    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=30, required=True,
                                 widget=forms.TextInput(attrs={'class': 'form-control', 'dir': 'rtl'}))
    last_name = forms.CharField(max_length=30, required=True,
                                widget=forms.TextInput(attrs={'class': 'form-control', 'dir': 'rtl'}))

    # حقول إضافية من UserProfile
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, required=True,
                             widget=forms.Select(attrs={'class': 'form-select'}))
    department = forms.CharField(max_length=100, required=False,
                                 widget=forms.TextInput(attrs={'class': 'form-control', 'dir': 'rtl'}))

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # تخصيص widgets كلمات المرور
        self.fields['password1'].widget = forms.PasswordInput(attrs={'class': 'form-control'})
        self.fields['password2'].widget = forms.PasswordInput(attrs={'class': 'form-control'})

        # إعداد Crispy Forms
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            HTML('<h4>المعلومات الأساسية</h4>'),
            Div(
                Div('username', css_class='col-md-6'),
                Div('email', css_class='col-md-6'),
                css_class='row'
            ),
            Div(
                Div('first_name', css_class='col-md-6'),
                Div('last_name', css_class='col-md-6'),
                css_class='row'
            ),
            HTML('<h4>كلمة المرور</h4>'),
            Div(
                Div('password1', css_class='col-md-6'),
                Div('password2', css_class='col-md-6'),
                css_class='row'
            ),
            HTML('<h4>معلومات الوظيفة</h4>'),
            Div(
                Div('role', css_class='col-md-6'),
                Div('department', css_class='col-md-6'),
                css_class='row'
            ),
            Submit('submit', 'إنشاء المستخدم', css_class='btn btn-primary')
        )

    def clean_email(self):
        """التحقق من عدم تكرار البريد الإلكتروني"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('هذا البريد الإلكتروني مستخدم بالفعل')
        return email

    def save(self, commit=True):
        """حفظ المستخدم مع إنشاء الملف الشخصي"""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']

        if commit:
            user.save()

            # إنشاء الملف الشخصي
            UserProfile.objects.create(
                user=user,
                role=self.cleaned_data['role'],
                department=self.cleaned_data['department'],
                full_name_ar=f"{self.cleaned_data['first_name']} {self.cleaned_data['last_name']}"
            )

        return user
class QuickActionForm(forms.ModelForm):
    """نموذج الإجراءات السريعة"""

    class Meta:
        model = QuickAction
        fields = [
            'title_ar', 'title_en', 'description_ar', 'description_en',
            'icon', 'color', 'action_type', 'action_url',
            'required_permission', 'required_role', 'is_active', 'order'
        ]
        widgets = {
            'title_ar': forms.TextInput(attrs={'class': 'form-control', 'dir': 'rtl'}),
            'title_en': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'description_ar': forms.TextInput(attrs={'class': 'form-control', 'dir': 'rtl'}),
            'description_en': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'fas fa-icon-name'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'action_type': forms.Select(attrs={'class': 'form-select'}),
            'action_url': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'required_permission': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'required_role': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # إضافة خيارات الأدوار
        self.fields['required_role'].choices = [('', '-- بدون قيود --')] + UserProfile.ROLE_CHOICES
class SiteContentForm(forms.ModelForm):
    """نموذج تحرير محتوى الموقع"""

    class Meta:
        model = SiteSettings
        fields = [
            'site_name_ar', 'site_name_en', 'logo', 'favicon',
            'phone', 'whatsapp_number', 'email', 'address_ar', 'address_en',
            'latitude', 'longitude', 'facebook_url', 'twitter_url',
            'instagram_url', 'tiktok_url', 'youtube_url',
            'about_summary_ar', 'about_summary_en', 'established_year'
        ]
        widgets = {
            'site_name_ar': forms.TextInput(attrs={'class': 'form-control', 'dir': 'rtl'}),
            'site_name_en': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'whatsapp_number': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'address_ar': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'dir': 'rtl'}),
            'address_en': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'dir': 'ltr'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'established_year': forms.NumberInput(attrs={'class': 'form-control', 'min': '1900'}),
            'logo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'favicon': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
class SliderItemForm(forms.ModelForm):
    """نموذج عناصر السلايدر"""

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
            'button_url': forms.URLInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
class SearchForm(forms.Form):
    """نموذج البحث العام"""

    query = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ابحث في لوحة التحكم...',
            'dir': 'rtl'
        })
    )

    category = forms.ChoiceField(
        choices=[
            ('', 'جميع الأقسام'),
            ('users', 'المستخدمين'),
            ('projects', 'المشاريع'),
            ('messages', 'الرسائل'),
            ('content', 'المحتوى'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
class ReportForm(forms.Form):
    """نموذج توليد التقارير"""

    REPORT_TYPES = [
        ('monthly_summary', 'التقرير الشهري'),
        ('projects_report', 'تقرير المشاريع'),
        ('users_activity', 'نشاط المستخدمين'),
        ('messages_report', 'تقرير الرسائل'),
        ('analytics_report', 'تقرير التحليلات'),
    ]

    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
    ]

    report_type = forms.ChoiceField(
        choices=REPORT_TYPES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    format_type = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        initial='pdf',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # إعداد Crispy Forms
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Div(
                Div('report_type', css_class='col-md-6'),
                Div('format_type', css_class='col-md-6'),
                css_class='row'
            ),
            HTML('<hr>'),
            HTML('<h6>فترة التقرير (اختياري)</h6>'),
            Div(
                Div('date_from', css_class='col-md-6'),
                Div('date_to', css_class='col-md-6'),
                css_class='row'
            ),
            Submit('submit', 'توليد التقرير', css_class='btn btn-primary')
        )
class SiteSettingForm(forms.ModelForm):
    """نموذج إعدادات الموقع - محدث"""

    class Meta:
        model = SiteSetting
        fields = [
            # عام
            'site_name_ar',
            'site_name_en',
            'site_description',
            'site_email',
            'site_phone',

            # الصيانة
            'maintenance_mode',
            'maintenance_message_ar',
            'maintenance_message_en',

            # الأمان
            'enable_two_factor',
            'session_timeout',
            'max_login_attempts',
            'force_https',
            'enable_ip_blocking',

            # الأداء
            'cache_timeout',
            'enable_compression',
            'enable_lazy_loading',
            'enable_minification',
        ]

        widgets = {
            # عام
            'site_name_ar': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم الموقع بالعربية',
                'dir': 'rtl'
            }),
            'site_name_en': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Site Name in English',
                'dir': 'ltr'
            }),
            'site_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'وصف مختصر عن الموقع',
                'dir': 'rtl'
            }),
            'site_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'info@example.com'
            }),
            'site_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+970'
            }),

            # الصيانة
            'maintenance_message_ar': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'dir': 'rtl',
                'placeholder': 'رسالة الصيانة بالعربية'
            }),
            'maintenance_message_en': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'dir': 'ltr',
                'placeholder': 'Maintenance message in English'
            }),

            # الأمان
            'session_timeout': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '5',
                'max': '1440'
            }),
            'max_login_attempts': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '3',
                'max': '10'
            }),

            # الأداء
            'cache_timeout': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '60',
                'max': '86400'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # إعداد Crispy Forms
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            # الإعدادات العامة
            HTML(
                '<div class="card mb-4"><div class="card-header bg-primary text-white"><h5><i class="fas fa-globe"></i> الإعدادات العامة</h5></div><div class="card-body">'),
            Div(
                Div('site_name_ar', css_class='col-md-6'),
                Div('site_name_en', css_class='col-md-6'),
                css_class='row'
            ),
            'site_description',
            Div(
                Div('site_email', css_class='col-md-6'),
                Div('site_phone', css_class='col-md-6'),
                css_class='row'
            ),
            HTML('</div></div>'),

            # وضع الصيانة
            HTML(
                '<div class="card mb-4"><div class="card-header bg-warning text-dark"><h5><i class="fas fa-tools"></i> وضع الصيانة</h5></div><div class="card-body">'),
            Field('maintenance_mode', css_class='form-check-input'),
            'maintenance_message_ar',
            'maintenance_message_en',
            HTML('</div></div>'),

            # إعدادات الأمان
            HTML(
                '<div class="card mb-4"><div class="card-header bg-danger text-white"><h5><i class="fas fa-shield-alt"></i> إعدادات الأمان</h5></div><div class="card-body">'),
            Div(
                Div(Field('enable_two_factor', css_class='form-check-input'), css_class='col-md-4'),
                Div(Field('force_https', css_class='form-check-input'), css_class='col-md-4'),
                Div(Field('enable_ip_blocking', css_class='form-check-input'), css_class='col-md-4'),
                css_class='row mb-3'
            ),
            Div(
                Div(PrependedText('session_timeout', '<i class="fas fa-clock"></i>'), css_class='col-md-6'),
                Div(PrependedText('max_login_attempts', '<i class="fas fa-key"></i>'), css_class='col-md-6'),
                css_class='row'
            ),
            HTML('</div></div>'),

            # إعدادات الأداء
            HTML(
                '<div class="card mb-4"><div class="card-header bg-success text-white"><h5><i class="fas fa-rocket"></i> إعدادات الأداء</h5></div><div class="card-body">'),
            Div(
                Div(AppendedText('cache_timeout', 'ثانية'), css_class='col-md-6'),
                Div(Field('enable_compression', css_class='form-check-input'), css_class='col-md-6'),
                css_class='row mb-3'
            ),
            Div(
                Div(Field('enable_lazy_loading', css_class='form-check-input'), css_class='col-md-6'),
                Div(Field('enable_minification', css_class='form-check-input'), css_class='col-md-6'),
                css_class='row'
            ),
            HTML('</div></div>'),

            # أزرار الحفظ
            HTML('<div class="d-flex justify-content-end gap-2">'),
            HTML(
                '<button type="button" class="btn btn-secondary" onclick="window.location.reload()"><i class="fas fa-undo"></i> إلغاء</button>'),
            Submit('submit', 'حفظ الإعدادات', css_class='btn btn-primary btn-lg'),
            HTML('</div>')
        )

        # تخصيص labels
        self.fields['site_name_ar'].label = 'اسم الموقع (عربي)'
        self.fields['site_name_en'].label = 'اسم الموقع (English)'
        self.fields['site_description'].label = 'وصف الموقع'
        self.fields['site_email'].label = 'البريد الإلكتروني'
        self.fields['site_phone'].label = 'رقم الهاتف'

        self.fields['maintenance_mode'].label = 'تفعيل وضع الصيانة'
        self.fields['maintenance_message_ar'].label = 'رسالة الصيانة (عربي)'
        self.fields['maintenance_message_en'].label = 'رسالة الصيانة (English)'

        self.fields['enable_two_factor'].label = 'المصادقة الثنائية'
        self.fields['session_timeout'].label = 'انتهاء الجلسة (دقيقة)'
        self.fields['max_login_attempts'].label = 'محاولات الدخول القصوى'
        self.fields['force_https'].label = 'إجبار HTTPS'
        self.fields['enable_ip_blocking'].label = 'حظر IP تلقائي'

        self.fields['cache_timeout'].label = 'مهلة الكاش (ثانية)'
        self.fields['enable_compression'].label = 'ضغط الملفات'
        self.fields['enable_lazy_loading'].label = 'التحميل الكسول للصور'
        self.fields['enable_minification'].label = 'تصغير CSS/JS'


class ContactInfoForm(forms.ModelForm):
    """نموذج إضافة وتعديل معلومات الاتصال"""

    # قائمة الأيقونات المقترحة حسب نوع المعلومة
    ICON_CHOICES = [
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

    icon_class = forms.ChoiceField(
        choices=ICON_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'icon-radio'}),
        label='اختر الأيقونة',
        required=False
    )

    class Meta:
        model = ContactInfo
        # الحقول المحدثة حسب الموديل: value_ar, value_en بدلاً من value
        fields = ['type', 'value_ar', 'value_en', 'icon_class', 'order', 'show_in_footer', 'is_active']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-select'}),
            'value_ar': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'القيمة بالعربية'
            }),
            'value_en': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'القيمة بالإنجليزية'
            }),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'show_in_footer': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'type': 'النوع',
            'value_ar': 'القيمة بالعربية',
            'value_en': 'القيمة بالإنجليزية',
            'icon_class': 'الأيقونة',
            'order': 'الترتيب',
            'show_in_footer': 'عرض في التذييل',
            'is_active': 'مفعل',
        }
        help_texts = {
            'type': 'اختر نوع معلومات الاتصال',
            'value_ar': 'أدخل القيمة بالعربية (مثال: رقم الهاتف، البريد الإلكتروني، العنوان)',
            'value_en': 'أدخل القيمة بالإنجليزية (اختياري)',
            'icon_class': 'اختر الأيقونة المناسبة',
            'order': 'ترتيب العرض (الأقل رقماً يظهر أولاً)',
            'show_in_footer': 'هل تريد عرض هذه المعلومة في تذييل الموقع؟',
        }

    def __init__(self, *args, **kwargs):
        self.used_types = kwargs.pop('used_types', [])
        self.used_icons = kwargs.pop('used_icons', [])
        self.info_instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)

        # تصفية الأنواع المستخدمة (لأن type هو unique)
        if self.used_types and not self.instance.pk:
            available_choices = [
                choice for choice in ContactInfo.INFO_TYPES
                if choice[0] not in self.used_types
            ]
            self.fields['type'].choices = available_choices

        # إذا كان هناك instance موجود، قم بتعيين الأيقونة الحالية
        if self.instance.pk and self.instance.icon_class:
            # تأكد من أن الأيقونة الحالية موجودة في القائمة
            current_icon = self.instance.icon_class
            if current_icon not in [choice[0] for choice in self.ICON_CHOICES]:
                # إضافة الأيقونة الحالية إلى القائمة إذا لم تكن موجودة
                self.fields['icon_class'].choices = [(current_icon, current_icon)] + list(self.ICON_CHOICES)

    def clean_type(self):
        """التحقق من عدم تكرار النوع"""
        type_value = self.cleaned_data.get('type')

        # إذا كان هذا تعديل على سجل موجود، تجاهل التحقق
        if self.instance.pk:
            return type_value

        # التحقق من عدم وجود نوع مماثل
        if ContactInfo.objects.filter(type=type_value).exists():
            raise forms.ValidationError(
                f'معلومة من نوع "{dict(ContactInfo.INFO_TYPES).get(type_value)}" موجودة بالفعل.')

        return type_value

    def clean_value_ar(self):
        """التحقق من صحة القيمة بالعربية"""
        value_ar = self.cleaned_data.get('value_ar')

        if not value_ar or not value_ar.strip():
            raise forms.ValidationError('يجب إدخال القيمة بالعربية.')

        return value_ar.strip()

    def clean_value_en(self):
        """تنظيف القيمة بالإنجليزية"""
        value_en = self.cleaned_data.get('value_en')

        if value_en:
            return value_en.strip()
        return value_en

    def clean(self):
        """التحقق من صحة البيانات بشكل عام"""
        cleaned_data = super().clean()
        type_value = cleaned_data.get('type')
        value_ar = cleaned_data.get('value_ar')
        icon_class = cleaned_data.get('icon_class')

        # التحقق من صحة البريد الإلكتروني
        if type_value == 'email' and value_ar:
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError as DjangoValidationError
            try:
                validate_email(value_ar)
            except DjangoValidationError:
                self.add_error('value_ar', 'يرجى إدخال عنوان بريد إلكتروني صحيح.')

        # التحقق من صحة رقم الهاتف (تحقق بسيط)
        if type_value == 'phone' and value_ar:
            import re
            # نمط بسيط للتحقق من أرقام الهاتف
            phone_pattern = r'^[\d\s\+\-\(\)]+$'
            if not re.match(phone_pattern, value_ar):
                self.add_error('value_ar', 'يرجى إدخال رقم هاتف صحيح.')

        # التحقق من صحة الموقع الإلكتروني
        if type_value == 'website' and value_ar:
            from django.core.validators import URLValidator
            from django.core.exceptions import ValidationError as DjangoValidationError
            validator = URLValidator()
            try:
                validator(value_ar)
            except DjangoValidationError:
                self.add_error('value_ar', 'يرجى إدخال رابط موقع إلكتروني صحيح.')

        # تعيين أيقونة افتراضية إذا لم يتم اختيار أيقونة
        if not icon_class and type_value:
            # البحث عن الأيقونة الافتراضية من FULL_INFO_TYPES
            type_data = next(
                (item for item in ContactInfo.FULL_INFO_TYPES if item[0] == type_value),
                None
            )
            if type_data and len(type_data) > 3:
                cleaned_data['icon_class'] = type_data[3]

        return cleaned_data

    def save(self, commit=True):
        """حفظ النموذج مع معالجة خاصة"""
        instance = super().save(commit=False)

        # التأكد من تعيين الأيقونة
        if not instance.icon_class and instance.type:
            type_data = next(
                (item for item in ContactInfo.FULL_INFO_TYPES if item[0] == instance.type),
                None
            )
            if type_data and len(type_data) > 3:
                instance.icon_class = type_data[3]

        if commit:
            instance.save()

        return instance

