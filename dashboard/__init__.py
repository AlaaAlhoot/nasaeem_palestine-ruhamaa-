"""
تطبيق لوحة التحكم - جمعية نسائم فلسطين الخيرية

هذا التطبيق يوفر واجهة إدارية شاملة لإدارة الموقع والمحتوى
والمستخدمين والمشاريع والإحصائيات.

الميزات الرئيسية:
- إدارة المستخدمين والصلاحيات
- لوحة تحكم تفاعلية مع إحصائيات حية
- نظام تسجيل الأنشطة
- مراقبة صحة النظام
- إدارة المحتوى والمشاريع
- تقارير وتحليلات متقدمة
- نظام النسخ الاحتياطي التلقائي
"""

default_app_config = 'dashboard.apps.DashboardConfig'

# معلومات الإصدار
__version__ = '1.0.0'
__author__ = 'فريق تطوير جمعية نسائم فلسطين'
__email__ = 'dev@nasaeem-palestine.org'

# إعدادات التطبيق
APP_NAME = 'dashboard'
APP_VERBOSE_NAME = 'لوحة التحكم'

# ثوابت التطبيق
DEFAULT_ITEMS_PER_PAGE = 25
CACHE_TIMEOUT = 300  # 5 دقائق
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB

# أدوار المستخدمين
USER_ROLES = {
    'super_admin': 'مدير عام',
    'admin': 'إدارة',
    'editor': 'محرر',
    'moderator': 'مشرف',
    'viewer': 'مشاهد'
}

# مستويات النشاط
ACTIVITY_LEVELS = {
    'info': 'معلومات',
    'success': 'نجح',
    'warning': 'تحذير',
    'error': 'خطأ'
}

# حالات صحة النظام
SYSTEM_STATUS = {
    'healthy': 'صحي',
    'warning': 'تحذير',
    'critical': 'حرج',
    'down': 'متوقف'
}