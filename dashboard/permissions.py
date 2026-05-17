from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

from .models import UserProfile


class DashboardPermissionMixin:
    """خليط الصلاحيات الأساسي للوحة التحكم"""

    def has_dashboard_access(self):
        """فحص الوصول الأساسي للوحة التحكم"""
        if not self.request.user.is_authenticated:
            return False

        if self.request.user.is_superuser:
            return True

        try:
            profile = self.request.user.profile
            return profile.is_active_staff and self.request.user.is_active
        except (UserProfile.DoesNotExist, AttributeError):
            return self.request.user.is_staff


class AdminRequiredMixin(DashboardPermissionMixin, UserPassesTestMixin):
    """خليط يتطلب صلاحيات الإدارة"""

    def test_func(self):
        if not self.has_dashboard_access():
            return False

        if self.request.user.is_superuser:
            return True

        try:
            return self.request.user.profile.is_admin()
        except (UserProfile.DoesNotExist, AttributeError):
            return False


class EditorRequiredMixin(DashboardPermissionMixin, UserPassesTestMixin):
    """خليط يتطلب صلاحيات التحرير أو أعلى"""

    def test_func(self):
        if not self.has_dashboard_access():
            return False

        if self.request.user.is_superuser:
            return True

        try:
            return self.request.user.profile.can_edit_content()
        except (UserProfile.DoesNotExist, AttributeError):
            return self.request.user.is_staff


class ViewerRequiredMixin(DashboardPermissionMixin, UserPassesTestMixin):
    """خليط يتطلب صلاحيات المشاهدة أو أعلى"""

    def test_func(self):
        return self.has_dashboard_access()


def dashboard_required(view_func):
    """مزخرف للوصول الأساسي للوحة التحكم"""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # التحقق من تسجيل الدخول
        if not request.user.is_authenticated:
            # ✅ لا تضف رسالة هنا - فقط حوّل
            return redirect(f'/accounts/login/?next={request.get_full_path()}')

        # السماح للـ superuser دائماً
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        # التحقق من الصلاحيات
        try:
            profile = request.user.profile
            if not (profile.is_active_staff and request.user.is_active):
                messages.error(request, 'ليس لديك صلاحية للوصول للوحة التحكم')
                return redirect('/')
        except (UserProfile.DoesNotExist, AttributeError):
            if not request.user.is_staff:
                messages.error(request, 'ليس لديك صلاحية للوصول للوحة التحكم')
                return redirect('/')

        return view_func(request, *args, **kwargs)

    return wrapper


def admin_required(view_func):
    """مزخرف يتطلب صلاحيات الإدارة"""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # التحقق من تسجيل الدخول
        if not request.user.is_authenticated:
            # ✅ لا تضف رسالة هنا
            return redirect(f'/accounts/login/?next={request.get_full_path()}')

        # السماح للـ superuser دائماً
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        try:
            profile = request.user.profile
            if not (profile.is_active_staff and profile.is_admin()):
                messages.error(request, 'تحتاج صلاحيات إدارة للوصول لهذه الصفحة')
                return redirect('dashboard:home')
        except (UserProfile.DoesNotExist, AttributeError):
            messages.error(request, 'تحتاج صلاحيات إدارة للوصول لهذه الصفحة')
            return redirect('dashboard:home')

        return view_func(request, *args, **kwargs)

    return wrapper



def editor_required(view_func):
    """مزخرف يتطلب صلاحيات التحرير"""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            # ✅ لا تضف رسالة هنا
            return redirect(f'/accounts/login/?next={request.get_full_path()}')

        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        try:
            profile = request.user.profile
            if not (profile.is_active_staff and profile.can_edit_content()):
                messages.error(request, 'تحتاج صلاحيات تحرير للوصول لهذه الصفحة')
                return redirect('dashboard:home')
        except (UserProfile.DoesNotExist, AttributeError):
            if not request.user.is_staff:
                messages.error(request, 'تحتاج صلاحيات تحرير للوصول لهذه الصفحة')
                return redirect('dashboard:home')

        return view_func(request, *args, **kwargs)

    return wrapper


# دوال فحص الصلاحيات
def is_dashboard_user(user) -> bool:
    """فحص صلاحية الوصول للوحة التحكم"""
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    try:
        profile = user.profile
        return profile.is_active_staff and user.is_active
    except (UserProfile.DoesNotExist, AttributeError):
        return user.is_staff


def is_admin_user(user) -> bool:
    """فحص صلاحيات الإدارة"""
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    if not is_dashboard_user(user):
        return False

    try:
        return user.profile.is_admin()
    except (UserProfile.DoesNotExist, AttributeError):
        return False


def is_editor_user(user) -> bool:
    """فحص صلاحيات التحرير"""
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    if not is_dashboard_user(user):
        return False

    try:
        return user.profile.can_edit_content()
    except (UserProfile.DoesNotExist, AttributeError):
        return user.is_staff


def can_edit_content(user) -> bool:
    """فحص صلاحية التحرير"""
    return is_editor_user(user)


def can_access_resource(user, resource_type: str) -> bool:
    """فحص الوصول لمورد معين"""
    if not is_dashboard_user(user):
        return False

    if user.is_superuser:
        return True

    try:
        role = user.profile.role
        permissions_map = {
            'users_management': ['super_admin', 'admin'],
            'system_settings': ['super_admin', 'admin'],
            'content_editing': ['super_admin', 'admin', 'editor'],
            'reports_viewing': ['super_admin', 'admin', 'editor', 'moderator'],
            'statistics_viewing': ['super_admin', 'admin', 'editor', 'moderator', 'viewer'],
        }
        return role in permissions_map.get(resource_type, [])
    except (UserProfile.DoesNotExist, AttributeError):
        return False


def check_user_permissions(user) -> dict:
    """الحصول على جميع صلاحيات المستخدم"""
    if not user.is_authenticated:
        return {'authenticated': False}

    if user.is_superuser:
        return {
            'authenticated': True,
            'is_dashboard_user': True,
            'is_admin': True,
            'can_edit_content': True,
            'role': 'super_admin',
            'resources': {k: True for k in [
                'users_management', 'system_settings', 'content_editing',
                'reports_viewing', 'statistics_viewing', 'projects_management',
                'messages_management', 'newsletter_management', 'backup_restore',
                'system_health', 'activity_logs', 'site_settings', 'user_profiles',
                'quick_actions', 'notifications_settings', 'dashboard_settings',
                'analytics_advanced', 'export_data', 'import_data', 'cache_management',
                'maintenance_mode', 'api_access'
            ]}
        }

    try:
        profile = user.profile
        return {
            'authenticated': True,
            'is_dashboard_user': is_dashboard_user(user),
            'is_admin': profile.is_admin(),
            'can_edit_content': profile.can_edit_content(),
            'role': profile.role,
            'resources': {
                'users_management': can_access_resource(user, 'users_management'),
                'system_settings': can_access_resource(user, 'system_settings'),
                'content_editing': can_access_resource(user, 'content_editing'),
                'reports_viewing': can_access_resource(user, 'reports_viewing'),
                'statistics_viewing': can_access_resource(user, 'statistics_viewing'),
            }
        }
    except (UserProfile.DoesNotExist, AttributeError):
        return {
            'authenticated': True,
            'is_dashboard_user': user.is_staff,
            'is_admin': user.is_superuser,
            'can_edit_content': user.is_staff,
            'role': 'legacy_user',
            'resources': {
                'users_management': user.is_superuser,
                'system_settings': user.is_superuser,
                'content_editing': user.is_staff,
                'reports_viewing': user.is_staff,
                'statistics_viewing': user.is_staff,
            }
        }


# مزخرف Ajax للصلاحيات
def ajax_permission_required(permission_func):
    """مزخرف للتحقق من الصلاحيات في طلبات Ajax"""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not permission_func(request.user):
                from django.http import JsonResponse
                return JsonResponse({'error': 'ليس لديك صلاحية للوصول'}, status=403)
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


# استخدام المزخرفات الجاهزة
dashboard_login_required = user_passes_test(is_dashboard_user, login_url='/accounts/login/')
admin_login_required = user_passes_test(is_admin_user, login_url='/accounts/login/')
editor_login_required = user_passes_test(is_editor_user, login_url='/accounts/login/')







