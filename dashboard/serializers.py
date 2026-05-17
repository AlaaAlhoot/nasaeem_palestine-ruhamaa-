from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from .models import UserProfile, ActivityLog, SystemHealth, QuickAction, NotificationSettings, DashboardSettings
from projects.models import Project, ProjectCategory
from contact.models import ContactMessage, Newsletter
from main.models import SiteSettings, Statistic


class UserProfileSerializer(serializers.ModelSerializer):
    """مسلسل الملف الشخصي للمستخدم"""
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    is_online = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'id', 'username', 'email', 'full_name', 'full_name_ar', 'full_name_en',
            'avatar', 'avatar_url', 'phone', 'bio', 'role', 'role_display',
            'department', 'dashboard_theme', 'language_preference',
            'is_active_staff', 'is_online', 'last_activity', 'login_count',
            'email_notifications', 'browser_notifications', 'sms_notifications',
            'created_at', 'updated_at'
        ]

    def get_is_online(self, obj):
        """فحص ما إذا كان المستخدم متصلاً الآن"""
        if not obj.last_activity:
            return False
        return obj.last_activity >= timezone.now() - timedelta(minutes=15)

    def get_avatar_url(self, obj):
        """الحصول على رابط الصورة الشخصية"""
        if obj.avatar:
            return obj.avatar.url
        return None


class DashboardStatsSerializer(serializers.Serializer):
    """مسلسل إحصائيات لوحة التحكم"""
    users_total = serializers.IntegerField()
    users_active = serializers.IntegerField()
    users_online = serializers.IntegerField()
    users_staff = serializers.IntegerField()

    projects_total = serializers.IntegerField()
    projects_active = serializers.IntegerField()
    projects_completed = serializers.IntegerField()
    projects_featured = serializers.IntegerField()

    messages_total = serializers.IntegerField()
    messages_new = serializers.IntegerField()
    messages_replied = serializers.IntegerField()

    newsletter_total = serializers.IntegerField()
    newsletter_active = serializers.IntegerField()
    newsletter_confirmed = serializers.IntegerField()

    last_updated = serializers.DateTimeField()


class ActivityLogSerializer(serializers.ModelSerializer):
    """مسلسل سجل الأنشطة"""
    username = serializers.CharField(read_only=True)
    user_display_name = serializers.SerializerMethodField()
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    time_since = serializers.SerializerMethodField()
    level_color = serializers.SerializerMethodField()
    action_icon = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = [
            'id', 'username', 'user_display_name', 'action', 'action_display',
            'action_icon', 'title', 'description', 'level', 'level_display',
            'level_color', 'timestamp', 'time_since', 'ip_address', 'extra_data'
        ]

    def get_user_display_name(self, obj):
        """الحصول على الاسم المعروض للمستخدم"""
        if obj.user and hasattr(obj.user, 'profile'):
            return obj.user.profile.get_display_name()
        return obj.username

    def get_time_since(self, obj):
        """حساب الوقت منذ النشاط"""
        diff = timezone.now() - obj.timestamp
        if diff.days > 0:
            return f'{diff.days} يوم'
        elif diff.seconds > 3600:
            return f'{diff.seconds // 3600} ساعة'
        elif diff.seconds > 60:
            return f'{diff.seconds // 60} دقيقة'
        else:
            return 'الآن'

    def get_level_color(self, obj):
        """الحصول على لون المستوى"""
        colors = {
            'info': '#17a2b8',
            'success': '#28a745',
            'warning': '#ffc107',
            'error': '#dc3545'
        }
        return colors.get(obj.level, '#6c757d')

    def get_action_icon(self, obj):
        """الحصول على أيقونة الإجراء"""
        icons = {
            'create': 'fas fa-plus',
            'update': 'fas fa-edit',
            'delete': 'fas fa-trash',
            'login': 'fas fa-sign-in-alt',
            'logout': 'fas fa-sign-out-alt',
            'view': 'fas fa-eye',
            'export': 'fas fa-download',
            'backup': 'fas fa-database'
        }
        return icons.get(obj.action, 'fas fa-info')


class SystemHealthSerializer(serializers.ModelSerializer):
    """مسلسل صحة النظام"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    status_color = serializers.CharField(source='get_status_color', read_only=True)
    memory_usage_gb = serializers.SerializerMethodField()
    disk_usage_gb = serializers.SerializerMethodField()
    memory_usage_formatted = serializers.SerializerMethodField()
    disk_usage_formatted = serializers.SerializerMethodField()
    time_since_check = serializers.SerializerMethodField()

    class Meta:
        model = SystemHealth
        fields = [
            'id', 'status', 'status_display', 'status_color',
            'response_time', 'memory_usage_percent', 'memory_usage_gb', 'memory_usage_formatted',
            'cpu_usage_percent', 'disk_usage_percent', 'disk_usage_gb', 'disk_usage_formatted',
            'active_users', 'errors_count', 'warnings_count', 'checked_at', 'time_since_check'
        ]

    def get_memory_usage_gb(self, obj):
        """تحويل استخدام الذاكرة إلى جيجابايت"""
        return round(obj.memory_used / (1024 ** 3), 2) if obj.memory_used else 0

    def get_disk_usage_gb(self, obj):
        """تحويل استخدام القرص إلى جيجابايت"""
        return round(obj.disk_used / (1024 ** 3), 2) if obj.disk_used else 0

    def get_memory_usage_formatted(self, obj):
        """تنسيق استخدام الذاكرة"""
        if obj.memory_used and obj.memory_total:
            used_gb = obj.memory_used / (1024 ** 3)
            total_gb = obj.memory_total / (1024 ** 3)
            return f"{used_gb:.1f} / {total_gb:.1f} GB"
        return "غير متاح"

    def get_disk_usage_formatted(self, obj):
        """تنسيق استخدام القرص"""
        if obj.disk_used and obj.disk_total:
            used_gb = obj.disk_used / (1024 ** 3)
            total_gb = obj.disk_total / (1024 ** 3)
            return f"{used_gb:.1f} / {total_gb:.1f} GB"
        return "غير متاح"

    def get_time_since_check(self, obj):
        """الوقت منذ آخر فحص"""
        diff = timezone.now() - obj.checked_at
        if diff.seconds < 60:
            return "منذ لحظات"
        elif diff.seconds < 3600:
            return f"{diff.seconds // 60} دقيقة"
        else:
            return f"{diff.seconds // 3600} ساعة"


class ProjectStatsSerializer(serializers.ModelSerializer):
    """مسلسل إحصائيات المشاريع"""
    category_name = serializers.CharField(source='category.name_ar', read_only=True)
    progress_percentage = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    status_color = serializers.SerializerMethodField()
    created_since = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'title_ar', 'title_en', 'category_name', 'status', 'status_display',
            'status_color', 'progress_percentage', 'views_count', 'likes_count',
            'created_at', 'created_since', 'is_featured', 'is_active'
        ]

    def get_progress_percentage(self, obj):
        """حساب نسبة التقدم"""
        if hasattr(obj, 'get_progress_percentage'):
            return obj.get_progress_percentage()
        # حساب افتراضي بناء على الحالة
        progress_map = {
            'planning': 10,
            'active': 50,
            'paused': 30,
            'completed': 100,
            'cancelled': 0
        }
        return progress_map.get(obj.status, 0)

    def get_status_color(self, obj):
        """لون الحالة"""
        colors = {
            'planning': '#ffc107',
            'active': '#17a2b8',
            'paused': '#fd7e14',
            'completed': '#28a745',
            'cancelled': '#dc3545'
        }
        return colors.get(obj.status, '#6c757d')

    def get_created_since(self, obj):
        """الوقت منذ الإنشاء"""
        diff = timezone.now() - obj.created_at
        if diff.days > 0:
            return f'{diff.days} يوم'
        elif diff.seconds > 3600:
            return f'{diff.seconds // 3600} ساعة'
        else:
            return 'اليوم'


class ContactMessageSerializer(serializers.ModelSerializer):
    """مسلسل رسائل التواصل"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    time_since = serializers.SerializerMethodField()
    status_color = serializers.SerializerMethodField()
    priority_color = serializers.SerializerMethodField()

    class Meta:
        model = ContactMessage
        fields = [
            'id', 'name', 'email', 'phone', 'subject', 'message',
            'status', 'status_display', 'status_color',
            'priority', 'priority_display', 'priority_color',
            'created_at', 'time_since', 'updated_at'
        ]

    def get_time_since(self, obj):
        """الوقت منذ الإرسال"""
        diff = timezone.now() - obj.created_at
        if diff.days > 0:
            return f'{diff.days} يوم'
        elif diff.seconds > 3600:
            return f'{diff.seconds // 3600} ساعة'
        elif diff.seconds > 60:
            return f'{diff.seconds // 60} دقيقة'
        else:
            return 'الآن'

    def get_status_color(self, obj):
        """لون الحالة"""
        colors = {
            'new': '#17a2b8',
            'read': '#ffc107',
            'replied': '#28a745',
            'closed': '#6c757d'
        }
        return colors.get(obj.status, '#6c757d')

    def get_priority_color(self, obj):
        """لون الأولوية"""
        colors = {
            'low': '#28a745',
            'normal': '#17a2b8',
            'high': '#ffc107',
            'urgent': '#dc3545'
        }
        return colors.get(obj.priority, '#17a2b8')


class QuickActionSerializer(serializers.ModelSerializer):
    """مسلسل الإجراءات السريعة"""
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    required_role_display = serializers.SerializerMethodField()

    class Meta:
        model = QuickAction
        fields = [
            'id', 'title_ar', 'title_en', 'description_ar', 'description_en',
            'icon', 'color', 'action_type', 'action_type_display', 'action_url',
            'required_permission', 'required_role', 'required_role_display',
            'is_active', 'order'
        ]

    def get_required_role_display(self, obj):
        """عرض الدور المطلوب"""
        if not obj.required_role:
            return 'الجميع'

        role_names = dict(UserProfile.ROLE_CHOICES)
        return role_names.get(obj.required_role, obj.required_role)


class ChartDataSerializer(serializers.Serializer):
    """مسلسل بيانات المخططات"""
    labels = serializers.ListField(child=serializers.CharField())
    datasets = serializers.ListField(child=serializers.DictField())
    total_count = serializers.IntegerField()
    period = serializers.CharField()
    chart_type = serializers.CharField()


class UserActivityChartSerializer(serializers.Serializer):
    """مسلسل مخطط نشاط المستخدمين"""
    date = serializers.DateField()
    logins = serializers.IntegerField()
    registrations = serializers.IntegerField()
    activities = serializers.IntegerField()


class ProjectsTimelineSerializer(serializers.Serializer):
    """مسلسل جدول المشاريع الزمني"""
    date = serializers.DateField()
    projects_created = serializers.IntegerField()
    projects_completed = serializers.IntegerField()


class MessagesStatsSerializer(serializers.Serializer):
    """مسلسل إحصائيات الرسائل"""
    date = serializers.DateField()
    messages_received = serializers.IntegerField()
    messages_replied = serializers.IntegerField()


class SystemStatsSerializer(serializers.Serializer):
    """مسلسل إحصائيات النظام العامة"""
    cpu_usage = serializers.ListField(child=serializers.FloatField())
    memory_usage = serializers.ListField(child=serializers.FloatField())
    disk_usage = serializers.ListField(child=serializers.FloatField())
    timestamps = serializers.ListField(child=serializers.DateTimeField())
    labels = serializers.ListField(child=serializers.CharField())


class NotificationSerializer(serializers.Serializer):
    """مسلسل الإشعارات"""
    id = serializers.IntegerField()
    title = serializers.CharField()
    message = serializers.CharField()
    type = serializers.CharField()  # success, info, warning, danger
    icon = serializers.CharField()
    url = serializers.URLField(required=False, allow_blank=True)
    count = serializers.IntegerField(required=False)
    created_at = serializers.DateTimeField()
    is_read = serializers.BooleanField(default=False)


class ReportSerializer(serializers.Serializer):
    """مسلسل التقارير"""
    report_type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    format_type = serializers.CharField()
    file_size = serializers.IntegerField(required=False)
    download_url = serializers.URLField()
    created_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField(required=False)


class SearchResultSerializer(serializers.Serializer):
    """مسلسل نتائج البحث"""
    id = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField()
    url = serializers.URLField()
    type = serializers.CharField()  # user, project, message, etc.
    icon = serializers.CharField()
    relevance_score = serializers.FloatField()


class BackupSerializer(serializers.Serializer):
    """مسلسل النسخ الاحتياطية"""
    id = serializers.CharField()
    filename = serializers.CharField()
    file_size = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    backup_type = serializers.CharField()
    status = serializers.CharField()
    download_url = serializers.URLField()


class MonthlyReportSerializer(serializers.Serializer):
    """مسلسل التقرير الشهري"""
    month = serializers.CharField()
    year = serializers.IntegerField()
    users_new = serializers.IntegerField()
    projects_new = serializers.IntegerField()
    messages_total = serializers.IntegerField()
    activities_total = serializers.IntegerField()
    top_projects = serializers.ListField(child=serializers.DictField())
    system_health_avg = serializers.FloatField()


class AnalyticsSerializer(serializers.Serializer):
    """مسلسل التحليلات المتقدمة"""
    period = serializers.CharField()
    total_visits = serializers.IntegerField()
    unique_visitors = serializers.IntegerField()
    bounce_rate = serializers.FloatField()
    avg_session_duration = serializers.IntegerField()
    top_pages = serializers.ListField(child=serializers.DictField())
    traffic_sources = serializers.ListField(child=serializers.DictField())


class ExportDataSerializer(serializers.Serializer):
    """مسلسل تصدير البيانات"""
    data_type = serializers.CharField()
    format = serializers.CharField()
    filters = serializers.DictField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    include_deleted = serializers.BooleanField(default=False)


class ImportDataSerializer(serializers.Serializer):
    """مسلسل استيراد البيانات"""
    file = serializers.FileField()
    data_type = serializers.CharField()
    overwrite_existing = serializers.BooleanField(default=False)
    validate_only = serializers.BooleanField(default=False)


class DashboardStatusSerializer(serializers.Serializer):
    """مسلسل حالة لوحة التحكم العامة"""
    system_healthy = serializers.BooleanField()
    maintenance_mode = serializers.BooleanField()
    version = serializers.CharField()
    uptime = serializers.CharField()
    last_backup = serializers.DateTimeField()
    pending_tasks = serializers.IntegerField()
    active_users = serializers.IntegerField()
    disk_space_free = serializers.CharField()
    memory_usage = serializers.CharField()


class DashboardSettingsSerializer(serializers.ModelSerializer):
    """مسلسل إعدادات لوحة التحكم"""

    class Meta:
        model = DashboardSettings
        fields = [
            'site_maintenance_mode', 'maintenance_message_ar', 'maintenance_message_en',
            'enable_two_factor', 'session_timeout', 'max_login_attempts',
            'admin_email_alerts', 'daily_report_enabled', 'weekly_report_enabled',
            'auto_backup_enabled', 'backup_frequency_days', 'keep_backups_count',
            'cache_timeout', 'enable_compression', 'updated_at'
        ]


class NotificationSettingsSerializer(serializers.ModelSerializer):
    """مسلسل إعدادات الإشعارات"""
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)

    class Meta:
        model = NotificationSettings
        fields = [
            'id', 'notification_type', 'notification_type_display',
            'email_enabled', 'sms_enabled', 'browser_enabled',
            'send_immediately', 'send_daily_digest', 'send_weekly_digest'
        ]


class UserCreateSerializer(serializers.ModelSerializer):
    """مسلسل إنشاء مستخدم جديد"""
    password         = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    role             = serializers.ChoiceField(choices=UserProfile.ROLE_CHOICES, write_only=True)

    class Meta:
        model  = User
        fields = [
            'username',
            'email',
            'first_name',
            'father_name',
            'grand_name',
            'family_name',
            'phone',
            'phone_country',
            'user_type',
            'password',
            'confirm_password',
            'role',
        ]

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("كلمات المرور غير متطابقة")
        return data

    def create(self, validated_data):
        role = validated_data.pop('role')
        validated_data.pop('confirm_password')

        # إنشاء المستخدم بالحقول الصحيحة
        user = User.objects.create_user(**validated_data)

        # إنشاء الملف الشخصي
        UserProfile.objects.create(
            user=user,
            role=role,
            full_name_ar=user.get_full_name(),
            is_active_staff=role in ['super_admin', 'admin', 'editor']
        )

        return user


class StatisticSerializer(serializers.ModelSerializer):
    """مسلسل الإحصائيات"""
    formatted_number = serializers.SerializerMethodField()

    class Meta:
        model = Statistic
        fields = [
            'id', 'title_ar', 'title_en', 'number', 'formatted_number',
            'suffix_ar', 'suffix_en', 'icon', 'color', 'order',
            'auto_update_from', 'is_active'
        ]

    def get_formatted_number(self, obj):
        """تنسيق الرقم"""
        if hasattr(obj, 'get_formatted_number'):
            return obj.get_formatted_number()

        # تنسيق افتراضي
        number = obj.number
        if number >= 1000000:
            return f"{number / 1000000:.1f}M"
        elif number >= 1000:
            return f"{number / 1000:.1f}K"
        else:
            return str(number)