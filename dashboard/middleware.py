from django.shortcuts import render, redirect
from django.conf import settings
from dashboard.models import SiteSetting
import os


class MaintenanceModeMiddleware:
    """Middleware لوضع الصيانة"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # التحقق من وضع الصيانة
        try:
            site_settings = SiteSetting.objects.first()
            maintenance_enabled = site_settings and site_settings.maintenance_mode
        except:
            maintenance_enabled = False

        if not maintenance_enabled:
            return self.get_response(request)

        # المسارات المسموحة
        current_path = request.path
        clean_path = current_path

        if current_path.startswith('/ar/'):
            clean_path = current_path[3:]
        elif current_path.startswith('/en/'):
            clean_path = current_path[3:]

        allowed_paths = [
            '/admin/', '/dashboard/', '/static/', '/media/',
            '/accounts/login/', '/accounts/logout/', '/ckeditor5/', '/i18n/'
        ]

        is_allowed_path = any(
            current_path.startswith(path) or clean_path.startswith(path)
            for path in allowed_paths
        )

        if is_allowed_path:
            if any(current_path.startswith(path) or clean_path.startswith(path)
                   for path in ['/accounts/login/', '/accounts/logout/']):
                return self.get_response(request)

            if any(current_path.startswith(path) or clean_path.startswith(path)
                   for path in ['/static/', '/media/', '/i18n/', '/ckeditor5/']):
                return self.get_response(request)

            if any(current_path.startswith(path) or clean_path.startswith(path)
                   for path in ['/admin/', '/dashboard/']):
                if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
                    return self.get_response(request)
                else:
                    return redirect('/accounts/login/?next=' + request.path)

        return self._render_maintenance_page(request, site_settings)

    def _render_maintenance_page(self, request, site_settings):
        """عرض صفحة الصيانة"""

        logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
        logo_exists = os.path.exists(logo_path)

        contact_info = []
        social_media = []

        try:
            from contact.models import ContactInfo, SocialMediaContact

            # قاموس الترجمة للحقول
            type_translations = {
                'phone': {'ar': 'الهاتف', 'en': 'Phone'},
                'email': {'ar': 'البريد الإلكتروني', 'en': 'Email'},
                'address': {'ar': 'العنوان', 'en': 'Address'},
                'fax': {'ar': 'الفاكس', 'en': 'Fax'},
                'po_box': {'ar': 'صندوق البريد', 'en': 'P.O. Box'},
                'website': {'ar': 'الموقع الإلكتروني', 'en': 'Website'},
            }

            # جلب معلومات التواصل النشطة
            contacts = ContactInfo.objects.filter(
                is_active=True,
                show_in_footer=True
            ).order_by('order', 'id')

            for contact in contacts:
                trans = type_translations.get(contact.type, {'ar': contact.label, 'en': contact.label})
                label_bilingual = f"{trans['ar']} | {trans['en']}"

                contact_info.append({
                    'icon': contact.get_icon_class(),
                    'value': contact.value,
                    'label': label_bilingual,
                })

            # جلب روابط السوشيال ميديا النشطة فقط
            socials = SocialMediaContact.objects.filter(
                is_active=True
            ).order_by('order', 'id')[:5]

            for social in socials:
                icon = SocialMediaContact.PLATFORM_ICONS.get(social.platform, 'fas fa-link')

                social_media.append({
                    'platform': social.platform,
                    'url': social.url,
                    'icon': icon,
                    'name': social.get_platform_display(),
                })

        except Exception as e:
            # استخدام بيانات افتراضية
            if site_settings.site_email:
                contact_info.append({
                    'icon': 'fas fa-envelope',
                    'value': site_settings.site_email,
                    'label': 'البريد الإلكتروني | Email',
                })
            if site_settings.site_phone:
                contact_info.append({
                    'icon': 'fas fa-phone',
                    'value': site_settings.site_phone,
                    'label': 'الهاتف | Phone',
                })

        context = {
            'logo_exists': logo_exists,
            'message_ar': site_settings.maintenance_message_ar or 'الموقع تحت الصيانة، سنعود قريباً',
            'message_en': site_settings.maintenance_message_en or 'Site under maintenance, we will be back soon',
            'site_name_ar': site_settings.site_name_ar or 'جمعية نسائم فلسطين',
            'site_name_en': site_settings.site_name_en or 'Nasaeem Palestine',
            'contact_info': contact_info,
            'social_media': social_media,
        }
        return render(request, 'maintenance.html', context, status=503)