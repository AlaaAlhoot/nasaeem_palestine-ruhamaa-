# ========================================
# المكتبات القياسية
# ========================================
# ========================================
# المكتبات القياسية
# ========================================
import io
import json
import logging
import os
import re
import shutil
import subprocess
import decimal
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

import psutil

# ========================================
# مكتبات خارجية
# ========================================
import pytz
import hijri_converter
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# ========================================
# استيرادات Django الأساسية
# ========================================
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db import connection
from django.db.models import Avg, Count, F, Max, Min, Q, Sum
from django.db.models.functions import ExtractHour, TruncDate, TruncMonth
from django.http import FileResponse, HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.generic import ListView, TemplateView

# ========================================
# استيرادات من التطبيق الحالي (dashboard)
# ========================================
from .forms import *
from .models import *
from .permissions import (
    admin_required, can_edit_content, dashboard_required,
    editor_required, is_admin_user, is_dashboard_user
)
from .utils import (
    check_user_permissions, generate_report,
    get_client_ip, get_dashboard_statistics, get_user_agent
)

# ========================================
# استيرادات من تطبيقات أخرى
# ========================================
from contact.forms import *
from contact.models import *
from main.forms import *
from main.models import *
from projects.forms import *
from projects.models import *
from projects.models import Project, ProjectCategory, ProjectImage, ProjectVideo
User = get_user_model()
# ========================================
# إعدادات السجل
# ========================================
logger = logging.getLogger(__name__)
@dashboard_required
def dashboard_home(request):
    """الصفحة الرئيسية للوحة التحكم"""
    try:
        now        = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago   = now - timedelta(days=7)

        # ==================== إحصائيات (cache 5 دقائق) ====================
        stats_cache_key = 'dashboard_home_stats'
        statistics = cache.get(stats_cache_key)

        if not statistics:
            # users — aggregate واحد بدل 5 queries
            users_qs   = User.objects
            proj_qs    = Project.objects
            msg_qs     = ContactMessage.objects
            news_qs    = Newsletter.objects
            act_qs     = ActivityLog.objects

            statistics = {
                'users': {
                    'total':     users_qs.count(),
                    'active':    users_qs.filter(is_active=True).count(),
                    'new_today': users_qs.filter(date_joined__gte=today_start).count(),
                    'new_week':  users_qs.filter(date_joined__gte=week_ago).count(),
                    'staff':     users_qs.filter(is_staff=True).count(),
                },
                'projects': {
                    'total':     proj_qs.count(),
                    'active':    proj_qs.filter(status='active').count(),
                    'completed': proj_qs.filter(status='completed').count(),
                    'planning':  proj_qs.filter(status='planning').count(),
                    'new_today': proj_qs.filter(created_at__gte=today_start).count(),
                    'new_week':  proj_qs.filter(created_at__gte=week_ago).count(),
                    'featured':  proj_qs.filter(is_featured=True).count(),
                },
                'messages': {
                    'total':  msg_qs.count(),
                    'new':    msg_qs.filter(status='new').count(),
                    'urgent': msg_qs.filter(priority='urgent').count(),
                    'today':  msg_qs.filter(created_at__gte=today_start).count(),
                    'week':   msg_qs.filter(created_at__gte=week_ago).count(),
                },
                'newsletter': {
                    'total':     news_qs.count(),
                    'active':    news_qs.filter(is_active=True).count(),
                    'confirmed': news_qs.filter(confirmed_at__isnull=False).count(),
                    'new_week':  news_qs.filter(subscribed_at__gte=week_ago).count(),
                },
                'activities': {
                    'total': act_qs.count(),
                    'today': act_qs.filter(timestamp__gte=today_start).count(),
                    'week':  act_qs.filter(timestamp__gte=week_ago).count(),
                },
            }
            cache.set(stats_cache_key, statistics, 60 * 5)

        # ==================== Chart (cache 10 دقائق) ====================
        chart_cache_key = f'dashboard_chart_{now.strftime("%Y-%m-%d-%H")}'
        chart_data = cache.get(chart_cache_key)

        if not chart_data:
            from django.db.models import Count
            from django.db.models.functions import TruncDate

            # projects chart — query واحدة بدل 7
            proj_chart_qs = Project.objects.filter(
                created_at__gte=week_ago
            ).annotate(day=TruncDate('created_at')).values('day').annotate(
                count=Count('id')
            ).order_by('day')

            # messages chart — query واحدة بدل 7
            msg_chart_qs = ContactMessage.objects.filter(
                created_at__gte=week_ago
            ).annotate(day=TruncDate('created_at')).values('day').annotate(
                count=Count('id')
            ).order_by('day')

            # users chart — query واحدة بدل 7
            users_chart_qs = User.objects.filter(
                date_joined__gte=week_ago
            ).annotate(day=TruncDate('date_joined')).values('day').annotate(
                count=Count('id')
            ).order_by('day')

            # تحويل لـ dict للوصول السريع
            proj_dict  = {str(r['day']): r['count'] for r in proj_chart_qs}
            msg_dict   = {str(r['day']): r['count'] for r in msg_chart_qs}
            users_dict = {str(r['day']): r['count'] for r in users_chart_qs}

            last_7_days    = []
            projects_chart = []
            messages_chart = []
            users_chart    = []

            for i in range(6, -1, -1):
                day     = now - timedelta(days=i)
                day_str = day.strftime('%Y-%m-%d')
                last_7_days.append(day.strftime('%a'))
                projects_chart.append(proj_dict.get(day_str, 0))
                messages_chart.append(msg_dict.get(day_str, 0))
                users_chart.append(users_dict.get(day_str, 0))

            chart_data = {
                'labels':   last_7_days,
                'projects': projects_chart,
                'messages': messages_chart,
                'users':    users_chart,
            }
            cache.set(chart_cache_key, chart_data, 60 * 10)

        # ==================== Engagement (cache 10 دقائق) ====================
        engagement_stats = cache.get('dashboard_engagement')
        if not engagement_stats:
            agg = Project.objects.aggregate(
                total_views=Sum('views_count'),
                total_likes=Sum('likes_count'),
                total_shares=Sum('shares_count'),
            )
            engagement_stats = {
                'total_views':  agg['total_views']  or 0,
                'total_likes':  agg['total_likes']  or 0,
                'total_shares': agg['total_shares'] or 0,
            }
            cache.set('dashboard_engagement', engagement_stats, 60 * 10)

        # ==================== بيانات ديناميكية (بدون cache) ====================
        recent_activities = ActivityLog.objects.filter(
            user=request.user
        ).select_related('user').order_by('-timestamp')[:8]

        new_messages = ContactMessage.objects.filter(
            status='new'
        ).order_by('-created_at')[:6]

        recent_projects = Project.objects.filter(
            is_active=True
        ).select_related('category').order_by('-created_at')[:8]

        top_projects = Project.objects.filter(
            is_active=True
        ).select_related('category').order_by('-views_count')[:4]

        active_users = User.objects.filter(
            is_active=True
        ).order_by('-last_login')[:6]

        system_health = get_system_health()

        # ==================== الإجراءات السريعة ====================
        quick_actions = []
        actions_list  = [
            ('مشروع جديد',    'fas fa-plus-circle',  '#28a745', 'dashboard:project_create'),
            ('المحتوى',       'fas fa-file-alt',     '#e83e8c', 'dashboard:content_management'),
            ('التقارير',      'fas fa-file-export',  '#ffc107', 'dashboard:reports'),
            ('التحليلات',     'fas fa-chart-line',   '#6f42c1', 'dashboard:analytics'),
            ('إعدادات الموقع','fas fa-cog',          '#6c757d', 'dashboard:settings'),
            ('سجل النشاط',   'fas fa-history',      '#fd7e14', 'dashboard:activity_logs'),
        ]
        for title, icon, color, url_name in actions_list:
            try:
                quick_actions.append({
                    'title_ar':   title,
                    'icon':       icon,
                    'color':      color,
                    'action_url': reverse(url_name),
                })
            except Exception:
                pass

        # ==================== التاريخ ====================
        gregorian_date = now.strftime('%Y-%m-%d')
        try:
            hijri        = hijri_converter.Gregorian(now.year, now.month, now.day).to_hijri()
            hijri_date_str = f"{hijri.day}/{hijri.month}/{hijri.year}"
        except Exception:
            hijri_date_str = "غير متاح"

        # تسجيل النشاط
        try:
            ActivityLog.log_activity(
                user=request.user,
                action='view',
                title='عرض لوحة التحكم الرئيسية',
                description='دخل المستخدم إلى لوحة التحكم الرئيسية',
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                session_key=request.session.session_key,
            )
        except Exception:
            pass

        context = {
            'statistics':          statistics,
            'recent_activities':   recent_activities,
            'new_messages':        new_messages,
            'recent_projects':     recent_projects,
            'top_projects':        top_projects,
            'active_users':        active_users,
            'system_health':       system_health,
            'quick_actions':       quick_actions,
            'engagement_stats':    engagement_stats,
            'chart_labels':        json.dumps(chart_data['labels']),
            'projects_chart_data': json.dumps(chart_data['projects']),
            'messages_chart_data': json.dumps(chart_data['messages']),
            'users_chart_data':    json.dumps(chart_data['users']),
            'page_title':          'لوحة التحكم الرئيسية',
            'now':                 now,
            'gregorian_date':      gregorian_date,
            'hijri_date':          hijri_date_str,
        }

        return render(request, 'dashboard/dashboard_home.html', context)

    except Exception as e:
        logger.error(f"خطأ في الصفحة الرئيسية: {e}")
        import traceback
        traceback.print_exc()
        messages.error(request, 'حدث خطأ في تحميل لوحة التحكم')
        return redirect('/')



def get_system_health():
    """الحصول على صحة النظام من utils"""
    from .utils import get_system_health as fetch_health

    try:
        health_data = fetch_health()

        class HealthObject:
            def __init__(self, data):
                self.status               = data.get('status', 'unknown')
                self.cpu_usage_percent    = data.get('cpu_usage_percent', 0)
                self.memory_usage_percent = data.get('memory_usage_percent', 0)
                self.disk_usage_percent   = data.get('disk_usage_percent', 0)
                self.memory_total         = data.get('memory_total', 0)
                self.memory_used          = data.get('memory_used', 0)
                self.disk_total           = data.get('disk_total', 0)
                self.disk_used            = data.get('disk_used', 0)
                self.db_connections       = data.get('db_connections', 0)
                self.active_users         = data.get('active_users', 0)

            def get_status_display(self):
                status_map = {
                    'healthy':  'صحي',
                    'warning':  'تحذير',
                    'critical': 'حرج',
                    'down':     'متوقف',
                    'unknown':  'غير معروف',
                    'error':    'خطأ'
                }
                return status_map.get(self.status, 'غير معروف')

            def get_status_color(self):
                colors = {
                    'healthy':  '#28a745',
                    'warning':  '#ffc107',
                    'critical': '#fd7e14',
                    'down':     '#dc3545',
                    'unknown':  '#6c757d',
                    'error':    '#dc3545'
                }
                return colors.get(self.status, '#6c757d')

            def is_healthy(self):
                return self.status == 'healthy'

        return HealthObject(health_data)

    except Exception as e:
        logger.error(f"خطأ في get_system_health: {e}")

        class DummyHealth:
            status               = 'unknown'
            cpu_usage_percent    = 0
            memory_usage_percent = 0
            disk_usage_percent   = 0
            memory_total         = 0
            memory_used          = 0
            disk_total           = 0
            disk_used            = 0
            db_connections       = 0
            active_users         = 0

            def get_status_display(self): return 'غير متاح'
            def get_status_color(self):   return '#6c757d'
            def is_healthy(self):         return False

        return DummyHealth()


import os

import os
import shutil
import zipfile
import json
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import JsonResponse, FileResponse, StreamingHttpResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.conf import settings
from django.core.management import call_command
from django.apps import apps
from django.db import connection






@admin_required
def backup_view(request):
    """صفحة النسخ الاحتياطي"""
    try:
        # الحصول على قائمة النسخ الاحتياطية الموجودة
        backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        backups = []
        if os.path.exists(backup_dir):
            for filename in os.listdir(backup_dir):
                if filename.endswith(('.sql', '.json', '.zip')):
                    file_path = os.path.join(backup_dir, filename)
                    file_size = os.path.getsize(file_path)
                    file_date = datetime.fromtimestamp(os.path.getmtime(file_path))

                    backups.append({
                        'filename': filename,
                        'size': file_size,
                        'size_display': format_file_size(file_size),
                        'date': file_date,
                        'type': get_backup_type(filename)
                    })

        # ترتيب حسب التاريخ (الأحدث أولاً)
        backups.sort(key=lambda x: x['date'], reverse=True)

        # معلومات قاعدة البيانات
        db_settings = settings.DATABASES['default']
        db_size = get_database_size()

        print(f"📊 [DEBUG] معلومات قاعدة البيانات:")
        print(f"   - النوع: {db_settings['ENGINE']}")
        print(f"   - الاسم: {db_settings.get('NAME', 'N/A')}")
        print(f"   - الحجم: {db_size}")

        db_info = {
            'engine': db_settings['ENGINE'].split('.')[-1],
            'name': db_settings.get('NAME', 'N/A'),
            'size': db_size
        }


        # الحصول على قائمة التطبيقات والجداول
        all_apps = []
        for app_config in apps.get_app_configs():
            if app_config.name.startswith('django.contrib'):
                continue  # تجاهل تطبيقات Django الافتراضية

            models = []
            for model in app_config.get_models():
                models.append({
                    'name': model.__name__,
                    'label': model._meta.db_table,
                    'verbose_name': model._meta.verbose_name,
                })

            if models:
                all_apps.append({
                    'name': app_config.name,
                    'label': app_config.verbose_name,
                    'models': models
                })

        context = {
            'backups': backups,
            'db_info': db_info,
            'backup_dir': backup_dir,
            'all_apps': all_apps,
            'page_title': 'النسخ الاحتياطي والاستعادة',
        }

        return render(request, 'dashboard/backup.html', context)

    except Exception as e:
        logger.error(f"خطأ في صفحة النسخ الاحتياطي: {e}")
        messages.error(request, 'حدث خطأ في تحميل صفحة النسخ الاحتياطي')
        return redirect('dashboard:home')


@require_POST
@admin_required
def create_backup_ajax(request):
    """إنشاء نسخة احتياطية مع تقدم"""
    try:
        data = json.loads(request.body)
        print("Received data:", data)
        backup_type = data.get('type', 'database')
        selected_apps = data.get('apps', [])
        selected_models = data.get('models', [])
        include_media = data.get('include_media', False)
        compress = data.get('compress', True)

        backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if backup_type == 'database':
            # نسخة احتياطية لقاعدة البيانات
            if compress:
                filename = f'db_backup_{timestamp}.zip'
                file_path = os.path.join(backup_dir, filename)

                # إنشاء ملف JSON مؤقت
                temp_json = os.path.join(backup_dir, f'temp_{timestamp}.json')

                with open(temp_json, 'w', encoding='utf-8') as f:
                    if selected_apps:
                        # تصدير تطبيقات محددة
                        call_command('dumpdata', *selected_apps, stdout=f, indent=2,
                                     natural_foreign=True, natural_primary=True)
                    elif selected_models:
                        # تصدير نماذج محددة
                        call_command('dumpdata', *selected_models, stdout=f, indent=2,
                                     natural_foreign=True, natural_primary=True)
                    else:
                        # تصدير كامل
                        call_command('dumpdata', stdout=f, indent=2,
                                     natural_foreign=True, natural_primary=True)

                # ضغط الملف
                with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(temp_json, 'database.json')

                # حذف الملف المؤقت
                os.remove(temp_json)
            else:
                filename = f'db_backup_{timestamp}.json'
                file_path = os.path.join(backup_dir, filename)

                with open(file_path, 'w', encoding='utf-8') as f:
                    if selected_apps:
                        call_command('dumpdata', *selected_apps, stdout=f, indent=2,
                                     natural_foreign=True, natural_primary=True)
                    elif selected_models:
                        call_command('dumpdata', *selected_models, stdout=f, indent=2,
                                     natural_foreign=True, natural_primary=True)
                    else:
                        call_command('dumpdata', stdout=f, indent=2,
                                     natural_foreign=True, natural_primary=True)

            backup_message = 'تم إنشاء نسخة احتياطية من قاعدة البيانات'

        elif backup_type == 'media':
            # نسخة احتياطية من ملفات الميديا
            filename = f'media_backup_{timestamp}.zip'
            file_path = os.path.join(backup_dir, filename)

            media_root = settings.MEDIA_ROOT

            # إنشاء ملف مضغوط
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(media_root):
                    # تجاهل مجلد backups نفسه
                    if 'backups' in root:
                        continue
                    for file in files:
                        file_full_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_full_path, media_root)
                        zipf.write(file_full_path, arcname)

            backup_message = 'تم إنشاء نسخة احتياطية من ملفات الميديا'

        elif backup_type == 'custom':
            # نسخة احتياطية مخصصة
            filename = f'custom_backup_{timestamp}.zip'
            file_path = os.path.join(backup_dir, filename)

            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # نسخ قاعدة البيانات
                db_filename = f'database_{timestamp}.json'
                db_path = os.path.join(backup_dir, db_filename)

                with open(db_path, 'w', encoding='utf-8') as f:
                    if selected_apps:
                        call_command('dumpdata', *selected_apps, stdout=f, indent=2,
                                     natural_foreign=True, natural_primary=True)
                    elif selected_models:
                        call_command('dumpdata', *selected_models, stdout=f, indent=2,
                                     natural_foreign=True, natural_primary=True)
                    else:
                        call_command('dumpdata', stdout=f, indent=2,
                                     natural_foreign=True, natural_primary=True)

                zipf.write(db_path, 'database.json')
                os.remove(db_path)

                # إضافة ملفات الميديا إذا طُلب ذلك
                if include_media:
                    media_root = settings.MEDIA_ROOT
                    for root, dirs, files in os.walk(media_root):
                        if 'backups' in root:
                            continue
                        for file in files:
                            file_full_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_full_path, media_root)
                            zipf.write(file_full_path, os.path.join('media', arcname))

            backup_message = 'تم إنشاء نسخة احتياطية مخصصة'

        elif backup_type == 'full':
            # نسخة احتياطية شاملة
            filename = f'full_backup_{timestamp}.zip'
            file_path = os.path.join(backup_dir, filename)

            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # نسخ قاعدة البيانات
                db_filename = f'db_temp_{timestamp}.json'
                db_path = os.path.join(backup_dir, db_filename)

                with open(db_path, 'w', encoding='utf-8') as f:
                    call_command('dumpdata', stdout=f, indent=2,
                                 natural_foreign=True, natural_primary=True)

                zipf.write(db_path, 'database.json')
                os.remove(db_path)

                # إضافة ملفات الميديا
                media_root = settings.MEDIA_ROOT
                for root, dirs, files in os.walk(media_root):
                    if 'backups' in root:
                        continue
                    for file in files:
                        file_full_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_full_path, media_root)
                        zipf.write(file_full_path, os.path.join('media', arcname))

            backup_message = 'تم إنشاء نسخة احتياطية شاملة'

        else:
            return JsonResponse({
                'success': False,
                'error': 'نوع النسخ الاحتياطي غير صحيح'
            }, status=400)

        # الحصول على حجم الملف
        file_size = os.path.getsize(file_path)

        # تسجيل النشاط
        from .utils import get_client_ip, get_user_agent
        ActivityLog.log_activity(
            user=request.user,
            action='create',
            title='إنشاء نسخة احتياطية',
            description=f'{backup_message}: {filename}',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            session_key=request.session.session_key
        )

        return JsonResponse({
            'success': True,
            'message': backup_message,
            'filename': filename,
            'size': format_file_size(file_size),
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    except Exception as e:
        logger.error(f"خطأ في إنشاء النسخة الاحتياطية: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'فشل في إنشاء النسخة الاحتياطية: {str(e)}'
        }, status=500)


@require_POST
@admin_required
def restore_backup_ajax(request):
    """استعادة نسخة احتياطية"""
    try:
        data = json.loads(request.body)
        filename = data.get('filename')

        if not filename:
            return JsonResponse({
                'success': False,
                'error': 'اسم الملف مطلوب'
            }, status=400)

        backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        file_path = os.path.join(backup_dir, filename)

        if not os.path.exists(file_path):
            return JsonResponse({
                'success': False,
                'error': 'الملف غير موجود'
            }, status=404)

        # تحديد نوع النسخة الاحتياطية
        if filename.endswith('.json'):
            # استعادة قاعدة البيانات من JSON
            call_command('loaddata', file_path)
            message = 'تم استعادة قاعدة البيانات بنجاح'

        elif filename.endswith('.zip'):
            # استعادة من ملف مضغوط
            extract_path = os.path.join(backup_dir, 'temp_restore')
            os.makedirs(extract_path, exist_ok=True)

            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)

            # استعادة قاعدة البيانات إذا وجدت
            db_file = os.path.join(extract_path, 'database.json')
            if os.path.exists(db_file):
                call_command('loaddata', db_file)

            # استعادة ملفات الميديا إذا وجدت
            media_folder = os.path.join(extract_path, 'media')
            if os.path.exists(media_folder):
                for root, dirs, files in os.walk(media_folder):
                    for file in files:
                        src = os.path.join(root, file)
                        rel_path = os.path.relpath(src, media_folder)
                        dst = os.path.join(settings.MEDIA_ROOT, rel_path)

                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)

            # حذف المجلد المؤقت
            shutil.rmtree(extract_path)

            message = 'تم استعادة النسخة الاحتياطية بنجاح'

        else:
            return JsonResponse({
                'success': False,
                'error': 'نوع ملف غير مدعوم'
            }, status=400)

        # تسجيل النشاط
        from .utils import get_client_ip, get_user_agent
        ActivityLog.log_activity(
            user=request.user,
            action='update',
            title='استعادة نسخة احتياطية',
            description=f'تم استعادة النسخة الاحتياطية: {filename}',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            session_key=request.session.session_key
        )

        return JsonResponse({
            'success': True,
            'message': message
        })

    except Exception as e:
        logger.error(f"خطأ في استعادة النسخة الاحتياطية: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'فشل في استعادة النسخة الاحتياطية: {str(e)}'
        }, status=500)


@admin_required

def download_backup(request, filename):
    """تحميل نسخة احتياطية"""
    try:
        backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        file_path = os.path.join(backup_dir, filename)

        if not os.path.exists(file_path):
            messages.error(request, 'الملف غير موجود')
            return redirect('dashboard:backup')

        # تسجيل النشاط
        from .utils import get_client_ip, get_user_agent
        ActivityLog.log_activity(
            user=request.user,
            action='view',
            title='تحميل نسخة احتياطية',
            description=f'تم تحميل: {filename}',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            session_key=request.session.session_key
        )

        response = FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename=filename
        )
        return response

    except Exception as e:
        logger.error(f"خطأ في تحميل النسخة الاحتياطية: {e}")
        messages.error(request, 'حدث خطأ في تحميل الملف')
        return redirect('dashboard:backup')


@require_POST
@admin_required
def delete_backup_ajax(request):
    """حذف نسخة احتياطية"""
    try:
        data = json.loads(request.body)
        filename = data.get('filename')

        if not filename:
            return JsonResponse({
                'success': False,
                'error': 'اسم الملف مطلوب'
            }, status=400)

        backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        file_path = os.path.join(backup_dir, filename)

        if not os.path.exists(file_path):
            return JsonResponse({
                'success': False,
                'error': 'الملف غير موجود'
            }, status=404)

        # حذف الملف
        os.remove(file_path)

        # تسجيل النشاط
        from .utils import get_client_ip, get_user_agent
        ActivityLog.log_activity(
            user=request.user,
            action='delete',
            title='حذف نسخة احتياطية',
            description=f'تم حذف: {filename}',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            session_key=request.session.session_key
        )

        return JsonResponse({
            'success': True,
            'message': 'تم حذف النسخة الاحتياطية بنجاح'
        })

    except Exception as e:
        logger.error(f"خطأ في حذف النسخة الاحتياطية: {e}")
        return JsonResponse({
            'success': False,
            'error': f'فشل في حذف النسخة الاحتياطية: {str(e)}'
        }, status=500)


# دوال مساعدة
def format_file_size(size_bytes):
    """تنسيق حجم الملف"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def get_backup_type(filename):
    """تحديد نوع النسخة الاحتياطية"""
    if 'db_backup' in filename:
        return 'قاعدة بيانات'
    elif 'media_backup' in filename:
        return 'ملفات ميديا'
    elif 'full_backup' in filename:
        return 'نسخة شاملة'
    elif 'custom_backup' in filename:
        return 'نسخة مخصصة'
    return 'غير معروف'


def get_database_size():
    """الحصول على حجم قاعدة البيانات - نسخة محسنة"""
    try:
        db_settings = settings.DATABASES['default']
        engine = db_settings['ENGINE']

        print(f"🔍 [DEBUG] نوع قاعدة البيانات: {engine}")

        # MySQL
        if 'mysql' in engine.lower():
            try:
                db_name = db_settings['NAME']
                print(f"🔍 [DEBUG] اسم قاعدة البيانات: {db_name}")

                with connection.cursor() as cursor:
                    # طريقة 1: استعلام مباشر
                    query = """
                        SELECT 
                            ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS size_mb
                        FROM information_schema.TABLES 
                        WHERE table_schema = %s
                    """
                    cursor.execute(query, [db_name])
                    result = cursor.fetchone()

                    print(f"🔍 [DEBUG] نتيجة الاستعلام: {result}")

                    if result and result[0]:
                        size = f"{result[0]} MB"
                        print(f"✅ [DEBUG] الحجم المحسوب: {size}")
                        return size

                    # طريقة 2: حساب من الجداول مباشرة
                    cursor.execute("SHOW TABLE STATUS")
                    total_size = 0
                    tables_count = 0

                    for row in cursor.fetchall():
                        if row[6] and row[8]:  # Data_length and Index_length
                            total_size += (row[6] + row[8])
                            tables_count += 1

                    if total_size > 0:
                        size_mb = total_size / 1024 / 1024
                        size = f"{size_mb:.2f} MB"
                        print(f"✅ [DEBUG] الحجم من الجداول ({tables_count} جدول): {size}")
                        return size

            except Exception as mysql_error:
                print(f"❌ [DEBUG] خطأ MySQL: {mysql_error}")
                import traceback
                traceback.print_exc()

        # PostgreSQL
        elif 'postgresql' in engine.lower():
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
                result = cursor.fetchone()
                if result:
                    size = result[0]
                    print(f"✅ [DEBUG] حجم PostgreSQL: {size}")
                    return size

        # SQLite
        elif 'sqlite' in engine.lower():
            db_path = db_settings['NAME']
            print(f"🔍 [DEBUG] مسار SQLite: {db_path}")

            if os.path.exists(db_path):
                size_bytes = os.path.getsize(db_path)
                size = format_file_size(size_bytes)
                print(f"✅ [DEBUG] حجم SQLite: {size}")
                return size

        # الطريقة البديلة: حساب من عدد السجلات
        print("⚠️ [DEBUG] استخدام الطريقة البديلة - حساب تقريبي")
        from django.apps import apps

        total_records = 0
        tables_count = 0

        for model in apps.get_models():
            try:
                count = model.objects.count()
                total_records += count
                tables_count += 1
            except:
                pass

        if total_records > 0:
            # تقدير: كل سجل = 2KB تقريباً
            estimated_size = total_records * 2048  # بالبايت
            size = format_file_size(estimated_size) + " (تقديري)"
            print(f"✅ [DEBUG] حجم تقديري ({total_records} سجل في {tables_count} جدول): {size}")
            return size

        print("❌ [DEBUG] فشل حساب الحجم")
        return "غير متاح"

    except Exception as e:
        print(f"❌ [DEBUG] خطأ عام: {e}")
        import traceback
        traceback.print_exc()
        return "غير متاح"


# ========================================
# صفحة ادارة المحتوى
# ========================================


@editor_required
def content_management(request):
    """إدارة محتوى الموقع - نسخة مدمجة ومحسّنة"""
    try:
        content_type = request.GET.get('type', 'overview')
        site_settings = SiteSettings.get_settings()

        context = {
            'site_settings': site_settings,
            'content_type': content_type,
            'page_title': 'إدارة المحتوى',
        }

        # معالج موحد للإضافة
        def handle_add_form(FormClass, success_msg, redirect_type, **form_kwargs):
            if request.method == 'POST':
                form = FormClass(request.POST, request.FILES, **form_kwargs)
                if form.is_valid():
                    instance = form.save()
                    ActivityLog.log_activity(
                        user=request.user,
                        action='create',
                        title=success_msg,
                        description=f'تم الإضافة بنجاح',
                        ip_address=get_client_ip(request),
                        user_agent=get_user_agent(request),
                        session_key=request.session.session_key
                    )
                    messages.success(request, success_msg)
                    return redirect(f'{reverse("dashboard:content_management")}?type={redirect_type}')
                else:
                    messages.error(request, 'حدث خطأ في البيانات المدخلة')
            else:
                form = FormClass(**form_kwargs)
            return form

        # ========================================
        # السلايدر
        # ========================================
        if content_type == 'slider':
            context['slider_items'] = HomeSlider.objects.all().order_by('order')
            result = handle_add_form(
                HomeSliderForm, 'تم إضافة الشريحة بنجاح', 'slider'
            )
            if isinstance(result, HttpResponseRedirect):
                return result
            context['form'] = result

        # ========================================
        # الإحصائيات
        # ========================================
        elif content_type == 'statistics':
            context['statistics'] = Statistic.objects.all().order_by('order')

            if request.method == 'POST':
                form = StatisticForm(request.POST)
                if form.is_valid():
                    try:
                        stat = form.save()
                        ActivityLog.log_activity(
                            user=request.user,
                            action='create',
                            title='إضافة إحصائية',
                            description=f'تم إضافة: {stat.title_ar}',
                            ip_address=get_client_ip(request),
                            user_agent=get_user_agent(request),
                            session_key=request.session.session_key
                        )
                        messages.success(request, 'تم إضافة الإحصائية بنجاح')
                        return redirect(f'{reverse("dashboard:content_management")}?type=statistics')
                    except Exception as e:
                        logger.error(f"خطأ في حفظ الإحصائية: {e}")
                        messages.error(request, f'حدث خطأ في حفظ الإحصائية: {str(e)}')
                else:
                    # ✅ عرض الأخطاء بوضوح
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f'{field}: {error}')
            else:
                form = StatisticForm()

            context['form'] = form
        # ========================================
        # فئات المشاريع
        # ========================================
        elif content_type == 'project_categories':
            context['project_categories'] = ProjectCategory.objects.all().order_by('order')
            used_icons = list(ProjectCategory.objects.values_list('icon', flat=True))
            result = handle_add_form(
                ProjectCategoryForm, 'تم إضافة الفئة بنجاح', 'project_categories', used_icons=used_icons
            )
            if isinstance(result, HttpResponseRedirect):
                return result
            context['form'] = result
            context['used_icons'] = used_icons

        # ========================================
        # المشاريع
        # ========================================
        elif content_type == 'projects':
            projects = Project.objects.select_related('category').all().order_by('-created_at')

            # فلترة حسب الحالة
            status_filter = request.GET.get('status', '')
            if status_filter:
                projects = projects.filter(status=status_filter)

            # فلترة حسب الفئة
            category_filter = request.GET.get('category', '')
            if category_filter:
                projects = projects.filter(category_id=category_filter)

            # الترقيم
            paginator = Paginator(projects, 20)
            context['projects_page'] = paginator.get_page(request.GET.get('page'))
            context['status_filter'] = status_filter
            context['category_filter'] = category_filter
            context['categories'] = ProjectCategory.objects.filter(is_active=True)

            # معالجة النموذج
            if request.method == 'POST':
                from projects.forms import ProjectForm
                form = ProjectForm(request.POST, request.FILES)

                # ===== DEBUG مؤقت =====
                print("=" * 60)
                print("🔴 is_valid:", form.is_valid())
                print("🔴 errors:", form.errors)
                print("🔴 POST keys:", list(request.POST.keys()))
                print("=" * 60)
                # ===== نهاية DEBUG =====

                if form.is_valid():
                    project = form.save()

                    # معالجة الصور الإضافية
                    additional_images = request.FILES.getlist('additional_images')
                    for order, image_file in enumerate(additional_images, start=1):
                        ProjectImage.objects.create(
                            project=project,
                            image=image_file,
                            order=order,
                            is_active=True
                        )

                    # معالجة رابط الفيديو
                    video_url = request.POST.get('video_url', '').strip()
                    if video_url:
                        ProjectVideo.objects.create(
                            project=project,
                            title_ar=f'فيديو {project.title_ar}',
                            title_en=f'Video {project.title_en}' if project.title_en else '',
                            youtube_url=video_url,
                            order=1,
                            is_active=True
                        )

                    ActivityLog.log_activity(
                        user=request.user,
                        action='create',
                        title='إضافة مشروع جديد',
                        description=f'تم إضافة المشروع: {project.title_ar}',
                        ip_address=get_client_ip(request),
                        user_agent=get_user_agent(request),
                        session_key=request.session.session_key
                    )
                    messages.success(request, 'تم إضافة المشروع بنجاح')
                    return redirect(f'{reverse("dashboard:content_management")}?type=projects')
                else:
                    error_messages = []
                    for field, errors in form.errors.items():
                        field_label = form.fields[field].label if field in form.fields else field
                        for error in errors:
                            error_messages.append(f"{field_label}: {error}")

                    error_text = "<br>".join(error_messages)
                    messages.error(request, f'حدث خطأ في البيانات المدخلة:<br>{error_text}', extra_tags='safe')
            else:
                from projects.forms import ProjectForm
                form = ProjectForm()

            context['form'] = form

        # ========================================
        # من نحن
        # ========================================
        elif content_type == 'about':
            about_page, _ = AboutPage.objects.get_or_create(pk=1)
            if request.method == 'POST':
                form = AboutPageForm(request.POST, request.FILES, instance=about_page)
                if form.is_valid():
                    form.save()
                    ActivityLog.log_activity(
                        user=request.user, action='update', title='تحديث صفحة من نحن',
                        description='تم التحديث', content_object=about_page,
                        ip_address=get_client_ip(request), user_agent=get_user_agent(request),
                        session_key=request.session.session_key
                    )
                    messages.success(request, 'تم التحديث بنجاح')
                    return redirect(f'{reverse("dashboard:content_management")}?type=about')
            else:
                form = AboutPageForm(instance=about_page)
            context.update({'form': form, 'about_page': about_page})

        # ========================================
        # الرؤية والرسالة
        # ========================================
        elif content_type == 'vision':
            vision_page, _ = VisionPage.objects.get_or_create(pk=1)
            if request.method == 'POST':
                form = VisionPageForm(request.POST, request.FILES, instance=vision_page)
                if form.is_valid():
                    form.save()
                    ActivityLog.log_activity(
                        user=request.user, action='update', title='تحديث الرؤية والرسالة',
                        description='تم التحديث', content_object=vision_page,
                        ip_address=get_client_ip(request), user_agent=get_user_agent(request),
                        session_key=request.session.session_key
                    )
                    messages.success(request, 'تم التحديث بنجاح')
                    return redirect(f'{reverse("dashboard:content_management")}?type=vision')
            else:
                form = VisionPageForm(instance=vision_page)
            context.update({'form': form, 'vision_page': vision_page})

        # ========================================
        # الأهداف
        # ========================================
        elif content_type == 'goals':
            context['goals'] = Goal.objects.all().order_by('order')
            used_icons = list(Goal.objects.values_list('icon', flat=True))
            result = handle_add_form(
                GoalForm, 'تم إضافة الهدف بنجاح', 'goals', used_icons=used_icons
            )
            if isinstance(result, HttpResponseRedirect):
                return result
            context['form'] = result

        # ========================================
        # مجلس الإدارة - نسخة محسنة (من الكود الأول)
        # ========================================
        elif content_type == 'board':
            context['board_members'] = BoardMember.objects.all().order_by('order')

            if request.method == 'POST':
                try:
                    # إنشاء عضو جديد
                    member = BoardMember()

                    # البيانات الأساسية
                    member.name_ar = request.POST.get('name_ar', '').strip()
                    member.name_en = request.POST.get('name_en', '').strip()

                    # التحقق من الاسم العربي
                    if not member.name_ar:
                        messages.error(request, 'يجب إدخال الاسم بالعربية')
                        return redirect(f'{reverse("dashboard:content_management")}?type=board')

                    # معالجة نوع المنصب
                    is_custom = request.POST.get('is_custom_position') == 'on'
                    member.is_custom_position = is_custom

                    if is_custom:
                        # منصب مخصص
                        member.position_type_ar = request.POST.get('position_type_ar', '').strip()
                        member.position_type_en = request.POST.get('position_type_en', '').strip()

                        if not member.position_type_ar or not member.position_type_en:
                            messages.error(request, 'يجب إدخال المنصب بالعربية والإنجليزية')
                            return redirect(f'{reverse("dashboard:content_management")}?type=board')
                    else:
                        # منصب قياسي
                        position_type = request.POST.get('position_type', '')
                        if not position_type:
                            messages.error(request, 'يجب اختيار نوع المنصب')
                            return redirect(f'{reverse("dashboard:content_management")}?type=board')

                        member.position_type = position_type

                        # الترجمة التلقائية
                        position_arabic = {
                            'president': 'رئيس مجلس الإدارة',
                            'vice_president': 'نائب الرئيس',
                            'secretary': 'السكرتير',
                            'treasurer': 'أمين الصندوق',
                            'member': 'عضو'
                        }

                        position_english = {
                            'president': 'President of the Board',
                            'vice_president': 'Vice President',
                            'secretary': 'Secretary',
                            'treasurer': 'Treasurer',
                            'member': 'Member'
                        }

                        member.position_type_ar = position_arabic.get(position_type, 'عضو')
                        member.position_type_en = position_english.get(position_type, 'Member')

                    # باقي البيانات
                    member.bio_ar = request.POST.get('bio_ar', '').strip()
                    member.bio_en = request.POST.get('bio_en', '').strip()
                    member.email = request.POST.get('email', '').strip()
                    member.phone = request.POST.get('phone', '').strip()
                    member.facebook_url = request.POST.get('facebook_url', '').strip()
                    member.twitter_url = request.POST.get('twitter_url', '').strip()
                    member.linkedin_url = request.POST.get('linkedin_url', '').strip()

                    try:
                        member.order = int(request.POST.get('order', 0))
                    except ValueError:
                        member.order = 0

                    member.is_active = request.POST.get('is_active') == 'on'

                    # معالجة الصورة
                    if 'photo' in request.FILES:
                        member.photo = request.FILES['photo']

                    member.save()

                    ActivityLog.log_activity(
                        user=request.user,
                        action='create',
                        title='إضافة عضو مجلس إدارة',
                        description=f'تم إضافة: {member.name_ar}',
                        ip_address=get_client_ip(request),
                        user_agent=get_user_agent(request),
                        session_key=request.session.session_key
                    )

                    messages.success(request, f'تم إضافة العضو {member.name_ar} بنجاح')
                    return redirect(f'{reverse("dashboard:content_management")}?type=board')

                except Exception as e:
                    logger.error(f"خطأ في إضافة عضو: {e}")
                    messages.error(request, f'حدث خطأ: {str(e)}')
                    return redirect(f'{reverse("dashboard:content_management")}?type=board')
            else:
                context['form'] = BoardMemberForm()

        # ========================================
        # الأسئلة الشائعة
        # ========================================
        elif content_type == 'faq':
            # جلب الأسئلة الشائعة مع التصنيفات
            faqs = FAQ.objects.select_related('category').all().order_by('order', '-created_at')

            # معالجة العلامات لكل سؤال
            for faq in faqs:
                if faq.tags_ar:
                    faq.tags_ar_list = [tag.strip() for tag in faq.tags_ar.split(',') if tag.strip()]
                else:
                    faq.tags_ar_list = []

                if faq.tags_en:
                    faq.tags_en_list = [tag.strip() for tag in faq.tags_en.split(',') if tag.strip()]
                else:
                    faq.tags_en_list = []

            context['faqs'] = faqs
            context['categories'] = Category.objects.all().order_by('category_ar')
            context['category_form'] = CategoryForm()

            # معالجة إضافة سؤال جديد
            if request.method == 'POST':
                form = FAQForm(request.POST, request.FILES)
                if form.is_valid():
                    faq = form.save()

                    ActivityLog.log_activity(
                        user=request.user,
                        action='create',
                        title='إضافة سؤال شائع',
                        description=f'تم إضافة سؤال: {faq.question_ar[:50]}',
                        content_object=faq,
                        level='success',
                        ip_address=get_client_ip(request),
                        user_agent=get_user_agent(request),
                        session_key=request.session.session_key if request.session.session_key else ''
                    )

                    return JsonResponse({
                        'success': True,
                        'message': 'تم إضافة السؤال بنجاح',
                        'redirect': request.path + '?type=faq'
                    })
                else:
                    messages.error(request, 'فشل في الحفظ')
                    context['form'] = form
            else:
                context['form'] = FAQForm()
        # ========================================
        # رسائل التواصل
        # ========================================
        elif content_type == 'messages':
            messages_list = ContactMessage.objects.all().order_by('-created_at')
            status_filter = request.GET.get('status', '')
            if status_filter:
                messages_list = messages_list.filter(status=status_filter)

            paginator = Paginator(messages_list, 20)
            context['messages_page'] = paginator.get_page(request.GET.get('page'))
            context['status_filter'] = status_filter

        # ========================================
        # الاشتراكات البريدية
        # ========================================
        elif content_type == 'newsletter':
            newsletters = Newsletter.objects.all().order_by('-subscribed_at')
            active_filter = request.GET.get('active', '')
            if active_filter == 'true':
                newsletters = newsletters.filter(is_active=True)
            elif active_filter == 'false':
                newsletters = newsletters.filter(is_active=False)

            paginator = Paginator(newsletters, 20)
            context['newsletters_page'] = paginator.get_page(request.GET.get('page'))
            context['active_filter'] = active_filter

        # ========================================
        # روابط التواصل الاجتماعي
        # ========================================
        elif content_type == 'social':
            context['social_links'] = SocialMediaContact.objects.all().order_by('order')
            result = handle_add_form(
                SocialMediaContactForm, 'تم إضافة الرابط بنجاح', 'social'
            )
            if isinstance(result, HttpResponseRedirect):
                return result
            context['form'] = result

        # ========================================
        # معلومات الاتصال
        # ========================================
        elif content_type == 'contact_info':
            context['contact_infos'] = ContactInfo.objects.all().order_by('order')
            used_types = list(ContactInfo.objects.values_list('type', flat=True))
            used_icons = list(ContactInfo.objects.values_list('icon_class', flat=True))
            result = handle_add_form(
                ContactInfoForm, 'تم إضافة معلومات الاتصال بنجاح', 'contact_info',
                used_types=used_types, used_icons=used_icons
            )
            if isinstance(result, HttpResponseRedirect):
                return result
            context['form'] = result
            context['used_icons'] = used_icons

        # ========================================
        # الشركاء
        # ========================================
        elif content_type == 'partners':
            context['partners'] = Partner.objects.all().order_by('order', '-partnership_date')
            result = handle_add_form(
                PartnerForm, 'تم إضافة الشريك بنجاح', 'partners'
            )
            if isinstance(result, HttpResponseRedirect):
                return result
            context['form'] = result

        # ========================================
        # النظرة العامة
        # ========================================
        # ========================================
        # النظرة العامة
        # ========================================
        else:
            # ── query واحدة لكل موديل بدل 12 query ──
            from django.db.models import Count, Q

            overview_stats = cache.get('dashboard_content_overview')
            if not overview_stats:
                overview_stats = {
                    'slider_count': HomeSlider.objects.filter(is_active=True).count(),
                    'statistics_count': Statistic.objects.filter(is_active=True).count(),
                    'goals_count': Goal.objects.filter(is_active=True).count(),
                    'board_count': BoardMember.objects.filter(is_active=True).count(),
                    'faq_count': FAQ.objects.filter(is_active=True).count(),
                    'messages_count': ContactMessage.objects.filter(status='new').count(),
                    'newsletter_count': Newsletter.objects.filter(is_active=True).count(),
                    'social_count': SocialMediaContact.objects.filter(is_active=True).count(),
                    'contact_info_count': ContactInfo.objects.filter(is_active=True).count(),
                    'project_categories_count': ProjectCategory.objects.filter(is_active=True).count(),
                    'projects_count': Project.objects.filter(is_active=True).count(),
                    'partners_count': Partner.objects.filter(is_active=True).count(),
                }
                cache.set('dashboard_content_overview', overview_stats, 60 * 5)

            context.update(overview_stats)

        return render(request, 'dashboard/content_management.html', context)

    except Exception as e:
        logger.error(f"خطأ في صفحة إدارة المحتوى: {e}")
        messages.error(request, 'حدث خطأ في تحميل صفحة إدارة المحتوى')
        return redirect('dashboard:home')




# ========================================
# إدارة المستخدمين
# ========================================
@admin_required
def users_management(request):
    """إدارة المستخدمين"""
    try:
        search_query = request.GET.get('search', '')
        status_filter = request.GET.get('status', '')
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        online_threshold = now - timedelta(minutes=15)

        users = User.objects.select_related('profile').all().order_by('-date_joined')

        if search_query:
            users = users.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(father_name__icontains=search_query) |
                Q(family_name__icontains=search_query) |
                Q(phone__icontains=search_query)
            )

        if status_filter == 'active':
            users = users.filter(is_active=True)
        elif status_filter == 'inactive':
            users = users.filter(is_active=False)

        paginator = Paginator(users, 25)
        users_page = paginator.get_page(request.GET.get('page'))

        users_stats = cache.get('dashboard_users_stats')
        if not users_stats:
            users_stats = {
                'total': User.objects.count(),
                'active': User.objects.filter(is_active=True).count(),
                'inactive': User.objects.filter(is_active=False).count(),
                'online': User.objects.filter(
                    last_seen__gte=timezone.now() - timedelta(minutes=15)
                ).count(),
            }
            cache.set('dashboard_users_stats', users_stats, 60 * 5)

        ActivityLog.log_activity(
            user=request.user, action='view', title='عرض صفحة إدارة المستخدمين',
            description='دخل المستخدم إلى صفحة إدارة المستخدمين',
            ip_address=get_client_ip(request), user_agent=get_user_agent(request),
            session_key=request.session.session_key
        )

        context = {
            'users_page': users_page,
            'users_stats': users_stats,
            'search_query': search_query,
            'status_filter': status_filter,
            'page_title': 'إدارة المستخدمين',
            'online_threshold': online_threshold,
        }

        return render(request, 'dashboard/users_management.html', context)

    except Exception as e:
        logger.error(f"خطأ في صفحة إدارة المستخدمين: {e}")
        messages.error(request, 'حدث خطأ في تحميل صفحة إدارة المستخدمين')
        return redirect('dashboard:home')


@require_POST
@admin_required
def create_user_ajax(request):
    """إنشاء مستخدم جديد"""
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST

        # جمع البيانات
        username      = data.get('username', '').strip()
        email         = data.get('email', '').strip()
        first_name    = data.get('first_name', '').strip()
        father_name   = data.get('father_name', '').strip()
        grand_name    = data.get('grand_name', '').strip()
        family_name   = data.get('family_name', '').strip()
        phone         = data.get('phone', '').strip()
        phone_country = data.get('phone_country', '+970').strip()
        user_type     = data.get('user_type', 'admin').strip()
        password      = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        is_active     = data.get('is_active') in ['true', True, 'on', '1']

        # التحقق من البيانات
        all_errors = []

        username_errors = validate_username(username)
        all_errors.extend(username_errors)

        email_errors = validate_email_unique(email)
        all_errors.extend(email_errors)

        first_name_errors = validate_arabic_name(first_name)
        all_errors.extend([f"الاسم الأول: {e}" for e in first_name_errors])

        family_name_errors = validate_arabic_name(family_name)
        all_errors.extend([f"اسم العائلة: {e}" for e in family_name_errors])

        password_errors = validate_password_strength(password)
        all_errors.extend(password_errors)

        if password != confirm_password:
            all_errors.append('كلمات المرور غير متطابقة')

        if all_errors:
            return JsonResponse({'success': False, 'errors': all_errors}, status=400)

        # إنشاء المستخدم
        user = User.objects.create_user(
            username      = username,
            email         = email,
            password      = password,
            first_name    = first_name,
            father_name   = father_name,
            grand_name    = grand_name,
            family_name   = family_name,
            phone         = phone,
            phone_country = phone_country,
            user_type     = user_type,
            is_active     = is_active,
            is_staff      = True,
        )

        # إنشاء أو تحديث الملف الشخصي
        if hasattr(user, 'profile'):
            user.profile.role = 'admin'
            user.profile.save()
        else:
            UserProfile.objects.create(
                user=user,
                role='admin',
                full_name_ar=user.get_full_name(),
                is_active_staff=True,
            )

        ActivityLog.log_activity(
            user=request.user,
            action='create',
            title='إضافة مستخدم جديد',
            description=f'تم إضافة المستخدم: {username}',
            content_object=user,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            session_key=request.session.session_key
        )

        return JsonResponse({
            'success': True,
            'message': 'تم إنشاء المستخدم بنجاح',
            'user': {
                'id':        str(user.id),
                'username':  user.username,
                'full_name': user.get_full_name(),
                'email':     user.email,
            }
        })

    except Exception as e:
        logger.error(f"خطأ في إنشاء مستخدم: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET"])
@admin_required
def view_user_ajax(request, user_id):
    """عرض بيانات مستخدم"""
    try:
        user = get_object_or_404(User, id=user_id)
        gaza_tz = pytz.timezone('Asia/Gaza')

        data = {
            'id':           str(user.id),
            'username':     user.username,
            'email':        user.email,
            'first_name':   user.first_name,
            'father_name':  user.father_name,
            'grand_name':   user.grand_name,
            'family_name':  user.family_name,
            'full_name':    user.get_full_name(),
            'phone':        user.phone,
            'phone_country': user.phone_country,
            'user_type':    user.get_user_type_display(),
            'is_active':    user.is_active,
            'is_approved':  user.is_approved,
            'is_staff':     user.is_staff,
            'is_superuser': user.is_superuser,
            'date_joined':  user.date_joined.astimezone(gaza_tz).strftime('%Y-%m-%d %H:%M:%S'),
            'last_login':   user.last_login.astimezone(gaza_tz).strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'لم يسجل دخول بعد',
            'login_count':  user.login_count,
            'role':         user.profile.get_role_display() if hasattr(user, 'profile') else '',
        }
        return JsonResponse({'success': True, 'data': data})

    except Exception as e:
        logger.error(f"خطأ في عرض المستخدم: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET", "POST"])
@admin_required
def edit_user_ajax(request, user_id):
    """تعديل بيانات مستخدم"""
    try:
        user = get_object_or_404(User, id=user_id)

        if request.method == 'GET':
            data = {
                'id':           str(user.id),
                'username':     user.username,
                'email':        user.email,
                'first_name':   user.first_name,
                'father_name':  user.father_name,
                'grand_name':   user.grand_name,
                'family_name':  user.family_name,
                'phone':        user.phone,
                'phone_country': user.phone_country,
                'user_type':    user.user_type,
                'is_active':    user.is_active,
                'is_approved':  user.is_approved,
            }
            return JsonResponse({'success': True, 'data': data})

        else:  # POST
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST

            username      = data.get('username', '').strip()
            email         = data.get('email', '').strip()
            first_name    = data.get('first_name', '').strip()
            father_name   = data.get('father_name', '').strip()
            grand_name    = data.get('grand_name', '').strip()
            family_name   = data.get('family_name', '').strip()
            phone         = data.get('phone', '').strip()
            phone_country = data.get('phone_country', '+970').strip()
            user_type     = data.get('user_type', user.user_type).strip()
            is_active     = data.get('is_active') in ['true', True, 'on', '1']
            is_approved   = data.get('is_approved') in ['true', True, 'on', '1']
            new_password  = data.get('new_password', '').strip()
            confirm_password = data.get('confirm_password', '').strip()

            all_errors = []

            if username != user.username:
                all_errors.extend(validate_username(username, user_id))

            if email != user.email:
                all_errors.extend(validate_email_unique(email, user_id))

            first_name_errors = validate_arabic_name(first_name)
            all_errors.extend([f"الاسم الأول: {e}" for e in first_name_errors])

            family_name_errors = validate_arabic_name(family_name)
            all_errors.extend([f"اسم العائلة: {e}" for e in family_name_errors])

            if new_password:
                all_errors.extend(validate_password_strength(new_password))
                if new_password != confirm_password:
                    all_errors.append('كلمات المرور غير متطابقة')

            if all_errors:
                return JsonResponse({'success': False, 'errors': all_errors}, status=400)

            # تحديث البيانات
            user.username      = username
            user.email         = email
            user.first_name    = first_name
            user.father_name   = father_name
            user.grand_name    = grand_name
            user.family_name   = family_name
            user.phone         = phone
            user.phone_country = phone_country
            user.user_type     = user_type
            user.is_active     = is_active
            user.is_approved   = is_approved

            if new_password:
                user.set_password(new_password)

            user.save()

            ActivityLog.log_activity(
                user=request.user,
                action='update',
                title='تعديل بيانات مستخدم',
                description=f'تم تعديل بيانات المستخدم: {username}',
                content_object=user,
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                session_key=request.session.session_key
            )

            return JsonResponse({'success': True, 'message': 'تم تحديث البيانات بنجاح'})

    except Exception as e:
        logger.error(f"خطأ في تعديل المستخدم: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@admin_required
def delete_user_ajax(request, user_id):
    """حذف مستخدم"""
    try:
        user = get_object_or_404(User, id=user_id)

        if user.id == request.user.id:
            return JsonResponse({'success': False, 'error': 'لا يمكنك حذف حسابك الشخصي'}, status=400)

        if user.is_superuser:
            return JsonResponse({'success': False, 'error': 'لا يمكن حذف المدير العام'}, status=400)

        # حفظ البيانات قبل الحذف
        username    = user.username
        email       = user.email
        full_name   = user.get_full_name()
        user_type   = user.user_type
        user_id_str = str(user.id)

        # ✅ تنظيف العلاقات يدوياً قبل الحذف لتجنب مشكلة UUID vs INT
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("UPDATE contact_contactmessage      SET replied_by_id    = NULL WHERE replied_by_id    = %s", [user_id_str])
            cursor.execute("UPDATE beneficiary_payments        SET beneficiary_id   = NULL WHERE beneficiary_id   = %s", [user_id_str])
            cursor.execute("UPDATE beneficiary_payments        SET sponsor_id       = NULL WHERE sponsor_id       = %s", [user_id_str])
            cursor.execute("UPDATE beneficiary_family_forms    SET sponsor_id       = NULL WHERE sponsor_id       = %s", [user_id_str])
            cursor.execute("UPDATE beneficiary_orphan_forms    SET sponsor_id       = NULL WHERE sponsor_id       = %s", [user_id_str])
            cursor.execute("UPDATE beneficiary_special_forms   SET sponsor_id       = NULL WHERE sponsor_id       = %s", [user_id_str])
            cursor.execute("UPDATE sponsor_payment_schedules   SET sponsor_id       = NULL WHERE sponsor_id       = %s", [user_id_str])
            cursor.execute("UPDATE sponsor_receipts            SET sponsor_id       = NULL WHERE sponsor_id       = %s", [user_id_str])

        # تسجيل النشاط
        ActivityLog.log_activity(
            user=request.user,
            action='delete',
            title='حذف مستخدم',
            description=f'تم حذف المستخدم: {username} — {full_name}',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            session_key=request.session.session_key,
            extra_data={
                'deleted_user_id':   user_id_str,
                'deleted_username':  username,
                'deleted_email':     email,
                'deleted_full_name': full_name,
                'deleted_user_type': user_type,
                'deleted_at':        timezone.now().isoformat(),
            }
        )

        user.delete()

        return JsonResponse({
            'success': True,
            'message': f'تم حذف المستخدم "{username}" بنجاح'
        })

    except Exception as e:
        logger.error(f"خطأ في حذف المستخدم: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_http_methods(["GET"])
@dashboard_required
def get_users_stats_ajax(request):
    """API للحصول على إحصائيات المستخدمين"""
    try:
        from datetime import timedelta
        stats = cache.get('dashboard_users_stats')
        if not stats:
            stats = {
                'total':    User.objects.count(),
                'active':   User.objects.filter(is_active=True).count(),
                'inactive': User.objects.filter(is_active=False).count(),
                'online':   User.objects.filter(
                    last_seen__gte=timezone.now() - timedelta(minutes=15)
                ).count(),
            }
            cache.set('dashboard_users_stats', stats, 60 * 5)
        return JsonResponse({'success': True, **stats})
    except Exception as e:
        logger.error(f"خطأ في API الإحصائيات: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
# ========================================
# التحليلات
# ========================================





class DecimalEncoder(json.JSONEncoder):
    """JSON Encoder لدعم Decimal"""

    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


@dashboard_required
def analytics_view(request):
    """صفحة التحليلات والإحصائيات المتقدمة - نسخة شهرية نهائية"""
    try:
        # معالجة الفترة الزمنية
        period_type = request.GET.get('period', '30')
        date_from_str = request.GET.get('date_from', '')
        date_to_str = request.GET.get('date_to', '')

        # تحديد التواريخ
        now = timezone.now()

        if period_type == 'custom' and date_from_str and date_to_str:
            start_date = timezone.make_aware(datetime.strptime(date_from_str, '%Y-%m-%d'))
            end_date = timezone.make_aware(
                datetime.strptime(date_to_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
        elif period_type == 'all':
            start_date = Project.objects.aggregate(earliest=Min('created_at'))['earliest'] or now
            end_date = now
        else:
            try:
                days = int(period_type)
            except:
                days = 30
            start_date = now - timedelta(days=days)
            end_date = now

        # ===== إحصائيات المشاريع =====
        projects_all = Project.objects.all()
        projects_period = projects_all.filter(created_at__range=[start_date, end_date])

        total_target = float(projects_all.aggregate(total=Sum('target_amount'))['total'] or 0)
        total_raised = float(projects_all.aggregate(total=Sum('raised_amount'))['total'] or 0)
        total_remaining = max(0, total_target - total_raised)

        projects_stats = {
            'total': projects_all.count(),
            'active': projects_all.filter(status='active').count(),
            'completed': projects_all.filter(status='completed').count(),
            'planning': projects_all.filter(status='planning').count(),
            'suspended': projects_all.filter(status='suspended').count(),
            'cancelled': projects_all.filter(status='cancelled').count(),
            'new_this_period': projects_period.count(),
            'featured': projects_all.filter(is_featured=True).count(),
            'total_views': projects_all.aggregate(total=Sum('views_count'))['total'] or 0,
            'total_likes': projects_all.aggregate(total=Sum('likes_count'))['total'] or 0,
            'total_shares': projects_all.aggregate(total=Sum('shares_count'))['total'] or 0,
            'total_target_amount': total_target,
            'total_raised_amount': total_raised,
            'total_remaining_amount': total_remaining,
            'total_beneficiaries': projects_all.aggregate(total=Sum('beneficiaries_count'))['total'] or 0,
            'target_beneficiaries': projects_all.aggregate(total=Sum('target_beneficiaries'))['total'] or 0,
        }

        # حساب النسب
        if projects_stats['total_target_amount'] > 0:
            projects_stats['funding_percentage'] = round(
                (projects_stats['total_raised_amount'] / projects_stats['total_target_amount']) * 100, 2
            )
        else:
            projects_stats['funding_percentage'] = 0

        if projects_stats['target_beneficiaries'] > 0:
            projects_stats['beneficiaries_percentage'] = round(
                (projects_stats['total_beneficiaries'] / projects_stats['target_beneficiaries']) * 100, 2
            )
        else:
            projects_stats['beneficiaries_percentage'] = 0

        projects_stats['remaining_beneficiaries'] = max(0,
                                                        projects_stats['target_beneficiaries'] - projects_stats[
                                                            'total_beneficiaries']
                                                        )


        from core.utils import get_exchange_rates
        exchange_rate = get_exchange_rates()['ILS_TO_USD']
        projects_stats['total_target_usd'] = round(total_target * exchange_rate, 2)
        projects_stats['total_raised_usd'] = round(total_raised * exchange_rate, 2)
        projects_stats['total_remaining_usd'] = round(total_remaining * exchange_rate, 2)

        # ===== إحصائيات الرسائل =====
        messages_all = ContactMessage.objects.all()
        messages_period = messages_all.filter(created_at__range=[start_date, end_date])

        messages_stats = {
            'total': messages_all.count(),
            'new': messages_all.filter(status='new').count(),
            'reading': messages_all.filter(status='reading').count(),
            'replied': messages_all.filter(status='replied').count(),
            'closed': messages_all.filter(status='closed').count(),
            'new_this_period': messages_period.count(),
            'urgent': messages_all.filter(priority='urgent').count(),
            'high': messages_all.filter(priority='high').count(),
            'normal': messages_all.filter(priority='normal').count(),
            'low': messages_all.filter(priority='low').count(),
        }

        # ===== إحصائيات المستخدمين =====
        users_all = User.objects.all()
        users_period = users_all.filter(date_joined__range=[start_date, end_date])

        users_stats = {
            'total': users_all.count(),
            'active': users_all.filter(is_active=True).count(),
            'inactive': users_all.filter(is_active=False).count(),
            'staff': users_all.filter(is_staff=True).count(),
            'superuser': users_all.filter(is_superuser=True).count(),
            'new_this_period': users_period.count(),
        }

        # ===== إحصائيات النشرة البريدية =====
        newsletter_all = Newsletter.objects.all()
        newsletter_period = newsletter_all.filter(subscribed_at__range=[start_date, end_date])

        newsletter_stats = {
            'total': newsletter_all.count(),
            'active': newsletter_all.filter(is_active=True).count(),
            'inactive': newsletter_all.filter(is_active=False).count(),
            'confirmed': newsletter_all.filter(confirmed_at__isnull=False).count(),
            'unconfirmed': newsletter_all.filter(confirmed_at__isnull=True).count(),
            'new_this_period': newsletter_period.count(),
            'daily': newsletter_all.filter(frequency='daily').count(),
            'weekly': newsletter_all.filter(frequency='weekly').count(),
            'monthly': newsletter_all.filter(frequency='monthly').count(),
        }

        # ===== إحصائيات النشاط =====
        activity_all = ActivityLog.objects.all()
        activity_period = activity_all.filter(timestamp__range=[start_date, end_date])

        activity_stats = {
            'total': activity_all.count(),
            'this_period': activity_period.count(),
            'today': activity_all.filter(timestamp__date=now.date()).count(),
            'create': activity_period.filter(action='create').count(),
            'update': activity_period.filter(action='update').count(),
            'delete': activity_period.filter(action='delete').count(),
            'login': activity_period.filter(action='login').count(),
            'view': activity_period.filter(action='view').count(),
            'export': activity_period.filter(action='export').count(),
        }

        # ===== إحصائيات فئات المشاريع =====
        categories_all = ProjectCategory.objects.filter(is_active=True)
        categories_stats_data = list(categories_all.annotate(
            project_count=Count('projects', filter=Q(projects__is_active=True))
        ).values('name_ar', 'project_count').order_by('-project_count')[:10])

        categories_stats = {
            'total': categories_all.count(),
            'with_projects': categories_all.annotate(
                project_count=Count('projects')
            ).filter(project_count__gt=0).count(),
            'data': categories_stats_data
        }

        # ===== إحصائيات الأسئلة الشائعة =====
        faq_all = FAQ.objects.filter(is_active=True)
        faq_stats = {
            'total': faq_all.count(),
            'total_views': faq_all.aggregate(total=Sum('views_count'))['total'] or 0,
            'total_helpful': faq_all.aggregate(total=Sum('helpful_votes'))['total'] or 0,
        }

        # ===== إحصائيات وسائل التواصل =====
        social_all = SocialMediaContact.objects.filter(is_active=True)
        social_stats = {
            'total': social_all.count(),
            'total_clicks': social_all.aggregate(total=Sum('clicks_count'))['total'] or 0,
        }

        # ===== البيانات الزمنية - شهرية بتنسيق MM/YYYY =====
        def create_monthly_timeline(queryset, date_field_name, start, end):
            """إنشاء timeline شهري بتنسيق MM/YYYY"""
            try:
                # إنشاء قاموس للشهور
                month_counts = defaultdict(int)

                # جمع البيانات
                for obj in queryset:
                    try:
                        # الحصول على التاريخ حسب اسم الحقل
                        if date_field_name == 'created_at':
                            obj_date = obj.created_at
                        elif date_field_name == 'date_joined':
                            obj_date = obj.date_joined
                        elif date_field_name == 'subscribed_at':
                            obj_date = obj.subscribed_at
                        elif date_field_name == 'timestamp':
                            obj_date = obj.timestamp
                        else:
                            continue

                        # التأكد من أن التاريخ صالح
                        if obj_date:
                            # تحويل إلى date فقط (بدون الوقت)
                            if hasattr(obj_date, 'date'):
                                date_only = obj_date.date()
                            else:
                                date_only = obj_date

                            # تحويل إلى نص شهري بتنسيق MM/YYYY
                            month_str = date_only.strftime('%m/%Y')

                            # التأكد من أنه ضمن النطاق
                            if start.date() <= date_only <= end.date():
                                month_counts[month_str] += 1
                    except Exception as e:
                        logger.warning(f"تجاهل عنصر: {e}")
                        continue

                # إنشاء timeline لجميع الأشهر في النطاق
                timeline = []
                current = start.date().replace(day=1)  # أول يوم في الشهر
                end_date_month = end.date().replace(day=1)

                while current <= end_date_month:
                    month_str = current.strftime('%m/%Y')
                    timeline.append({
                        'date': month_str,
                        'count': month_counts.get(month_str, 0)
                    })

                    # الانتقال للشهر التالي
                    if current.month == 12:
                        current = current.replace(year=current.year + 1, month=1)
                    else:
                        current = current.replace(month=current.month + 1)

                # إذا لم تكن هناك بيانات، أنشئ timeline للأشهر الـ12 الأخيرة
                if not timeline:
                    timeline = []
                    current_date = datetime.now()
                    for i in range(11, -1, -1):  # من 11 إلى 0 (12 شهر)
                        month_date = current_date - timedelta(days=30 * i)
                        month_str = month_date.strftime('%m/%Y')
                        timeline.append({
                            'date': month_str,
                            'count': 0
                        })

                return timeline

            except Exception as e:
                logger.error(f"خطأ في create_monthly_timeline: {e}")
                import traceback
                traceback.print_exc()
                # إرجاع بيانات افتراضية للأشهر الـ12
                timeline = []
                current_date = datetime.now()
                for i in range(11, -1, -1):
                    month_date = current_date - timedelta(days=30 * i)
                    timeline.append({
                        'date': month_date.strftime('%m/%Y'),
                        'count': 0
                    })
                return timeline

        # إنشاء الـ timelines الشهرية
        print("🔄 [DEBUG] بدء إنشاء Timelines الشهرية...")

        projects_timeline = create_monthly_timeline(projects_period, 'created_at', start_date, end_date)
        print(f"📊 [DEBUG] Projects Timeline: {projects_timeline}")

        messages_timeline = create_monthly_timeline(messages_period, 'created_at', start_date, end_date)
        print(f"📊 [DEBUG] Messages Timeline: {messages_timeline}")

        users_timeline = create_monthly_timeline(users_period, 'date_joined', start_date, end_date)
        print(f"📊 [DEBUG] Users Timeline: {users_timeline}")

        newsletter_timeline = create_monthly_timeline(newsletter_period, 'subscribed_at', start_date, end_date)
        print(f"📊 [DEBUG] Newsletter Timeline: {newsletter_timeline}")

        activity_timeline = create_monthly_timeline(activity_period, 'timestamp', start_date, end_date)
        print(f"📊 [DEBUG] Activity Timeline: {activity_timeline}")

        # طباعة ملخص
        print(
            f"✅ [DEBUG] Projects: {len(projects_timeline)} months, Total: {sum(item['count'] for item in projects_timeline)}")
        print(
            f"✅ [DEBUG] Messages: {len(messages_timeline)} months, Total: {sum(item['count'] for item in messages_timeline)}")
        print(f"✅ [DEBUG] Users: {len(users_timeline)} months, Total: {sum(item['count'] for item in users_timeline)}")
        print(
            f"✅ [DEBUG] Activity: {len(activity_timeline)} months, Total: {sum(item['count'] for item in activity_timeline)}")

        # ===== توزيع حسب الحالة =====
        projects_by_status = list(projects_all.values('status').annotate(
            count=Count('id')
        ).order_by('-count'))

        status_translation = {
            'planning': 'في التخطيط',
            'active': 'نشط',
            'completed': 'مكتمل',
            'suspended': 'معلق',
            'cancelled': 'ملغى'
        }
        for item in projects_by_status:
            item['status_ar'] = status_translation.get(item['status'], item['status'])

        messages_by_status = list(messages_all.values('status').annotate(
            count=Count('id')
        ).order_by('-count'))

        message_status_translation = {
            'new': 'جديدة',
            'reading': 'قيد القراءة',
            'replied': 'تم الرد',
            'closed': 'مغلقة'
        }
        for item in messages_by_status:
            item['status_ar'] = message_status_translation.get(item['status'], item['status'])

        messages_by_priority = list(messages_all.values('priority').annotate(
            count=Count('id')
        ).order_by('-count'))

        priority_translation = {
            'low': 'منخفضة',
            'normal': 'عادية',
            'high': 'عالية',
            'urgent': 'عاجلة'
        }
        for item in messages_by_priority:
            item['priority_ar'] = priority_translation.get(item['priority'], item['priority'])

        # ===== توزيع النشاط =====
        activity_by_action = list(activity_period.values('action').annotate(
            count=Count('id')
        ).order_by('-count'))

        action_translation = {
            'create': 'إنشاء',
            'update': 'تحديث',
            'delete': 'حذف',
            'login': 'تسجيل دخول',
            'logout': 'تسجيل خروج',
            'view': 'عرض',
            'export': 'تصدير'
        }
        for item in activity_by_action:
            item['action_ar'] = action_translation.get(item['action'], item['action'])

        activity_by_level = list(activity_period.values('level').annotate(
            count=Count('id')
        ).order_by('-count'))

        level_translation = {
            'info': 'معلومات',
            'warning': 'تحذير',
            'error': 'خطأ',
            'critical': 'حرج'
        }
        for item in activity_by_level:
            item['level_ar'] = level_translation.get(item['level'], item['level'])

        # ===== نشاط حسب الساعة (آخر 7 أيام) =====
        try:
            # حساب تاريخ قبل 7 أيام
            seven_days_ago = now - timedelta(days=7)

          

            # الطريقة اليدوية الآمنة 100%
            activity_recent = activity_all.filter(timestamp__gte=seven_days_ago)
            activity_by_hour_dict = defaultdict(int)

            total_activities = 0
            for activity in activity_recent:
                try:
                    hour = activity.timestamp.hour
                    activity_by_hour_dict[hour] += 1
                    total_activities += 1
                except Exception as e:
                    logger.warning(f"تجاهل نشاط: {e}")
                    continue



            # إنشاء قائمة كاملة لجميع الساعات (0-23)
            activity_by_hour = []
            for hour in range(24):
                activity_by_hour.append({
                    'hour': hour,
                    'count': activity_by_hour_dict.get(hour, 0)
                })



        except Exception as e:
            logger.error(f"خطأ في حساب النشاط حسب الساعة: {e}")
            import traceback
            traceback.print_exc()

            # بيانات افتراضية
            activity_by_hour = []
            for hour in range(24):
                activity_by_hour.append({
                    'hour': hour,
                    'count': 0
                })


        # ===== المخطط الشامل للموقع =====
        overview_data = {
            'labels': ['المشاريع', 'الرسائل', 'المستخدمين', 'الاشتراكات', 'الأسئلة', 'التواصل'],
            'data': [
                projects_stats['total'],
                messages_stats['total'],
                users_stats['total'],
                newsletter_stats['total'],
                faq_stats['total'],
                social_stats['total']
            ]
        }

        # ===== أهم المشاريع =====
        top_projects_views = list(projects_all.filter(is_active=True).order_by('-views_count')[:5].values(
            'id', 'title_ar', 'views_count'
        ))

        top_projects_likes = list(projects_all.filter(is_active=True).order_by('-likes_count')[:5].values(
            'id', 'title_ar', 'likes_count'
        ))

        # ===== إحصائيات إضافية =====
        total_content = {
            'projects': projects_stats['total'],
            'messages': messages_stats['total'],
            'users': users_stats['total'],
            'newsletters': newsletter_stats['total'],
            'activities': activity_stats['total'],
            'categories': categories_stats['total'],
            'faqs': faq_stats['total'],
            'social': social_stats['total'],
        }

        context = {
            'projects_stats': projects_stats,
            'messages_stats': messages_stats,
            'users_stats': users_stats,
            'newsletter_stats': newsletter_stats,
            'activity_stats': activity_stats,
            'categories_stats': categories_stats,
            'faq_stats': faq_stats,
            'social_stats': social_stats,
            'total_content': total_content,
            'overview_data': json.dumps(overview_data, cls=DecimalEncoder),
            'projects_timeline': json.dumps(projects_timeline, cls=DecimalEncoder),
            'messages_timeline': json.dumps(messages_timeline, cls=DecimalEncoder),
            'users_timeline': json.dumps(users_timeline, cls=DecimalEncoder),
            'newsletter_timeline': json.dumps(newsletter_timeline, cls=DecimalEncoder),
            'activity_timeline': json.dumps(activity_timeline, cls=DecimalEncoder),
            'projects_by_status': json.dumps(projects_by_status, cls=DecimalEncoder),
            'messages_by_status': json.dumps(messages_by_status, cls=DecimalEncoder),
            'messages_by_priority': json.dumps(messages_by_priority, cls=DecimalEncoder),
            'activity_by_action': json.dumps(activity_by_action, cls=DecimalEncoder),
            'activity_by_level': json.dumps(activity_by_level, cls=DecimalEncoder),
            'activity_by_hour': json.dumps(activity_by_hour, cls=DecimalEncoder),
            'categories_stats_data': json.dumps(categories_stats_data, cls=DecimalEncoder),
            'top_projects_views': json.dumps(top_projects_views, cls=DecimalEncoder),
            'top_projects_likes': json.dumps(top_projects_likes, cls=DecimalEncoder),
            'selected_period': period_type,
            'date_from': date_from_str,
            'date_to': date_to_str,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'page_title': 'التحليلات والإحصائيات',
        }

        return render(request, 'dashboard/analytics.html', context)

    except Exception as e:
        logger.error(f"خطأ في صفحة التحليلات: {e}")
        import traceback
        traceback.print_exc()
        messages.error(request, 'حدث خطأ في تحميل التحليلات')
        return redirect('dashboard:home')

# ========================================
# التقارير
# ========================================

from .report_generators import (
    generate_monthly_report,
    generate_yearly_report,
    generate_projects_report,
    generate_users_activity_report,
    generate_messages_report,
    generate_custom_report,
    generate_advanced_custom_report
)

from .models import ReportLog, UserProfile, SiteSetting, ActivityLog, SystemHealth


@dashboard_required
def reports_view(request):
    """صفحة التقارير"""
    try:
        from django.contrib.auth import get_user_model
        from projects.models import Project, ProjectCategory
        from contact.models import ContactMessage, Newsletter

        context = {
            'projects_count': Project.objects.count(),
            'users_count': User.objects.count(),
            'messages_count': ContactMessage.objects.count(),
            'newsletter_count': Newsletter.objects.count(),
            'users': User.objects.filter(is_staff=True).order_by('username'),
            'categories': ProjectCategory.objects.filter(is_active=True).order_by('order'),
            'page_title': 'التقارير',
        }
        return render(request, 'dashboard/reports.html', context)
    except Exception as e:
        logger.error(f"خطأ في صفحة التقارير: {e}")
        messages.error(request, 'حدث خطأ')
        return redirect('dashboard:home')


@require_POST
@dashboard_required
def generate_report_api(request):
    """API لتوليد التقارير - محدث"""
    try:
        from django.contrib.auth import get_user_model

        data = json.loads(request.body)
        report_type = data.get('type')
        period_type = data.get('period_type', 'monthly')
        user_id = data.get('user_id')
        category_id = data.get('category_id')
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        selected_reports = data.get('selected_reports', [])

        # تحويل التواريخ
        if date_from:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        if date_to:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()

        # توليد التقرير حسب النوع
        if report_type == 'monthly_summary':
            output, filename = generate_monthly_report(request.user)

        elif report_type == 'yearly_summary':
            output, filename = generate_yearly_report(request.user)

        elif report_type == 'projects_report':
            output, filename = generate_projects_report(
                request.user, period_type, date_from, date_to, category_id
            )

        elif report_type == 'users_activity':
            user_filter = None
            if user_id and user_id != 'all':
                user_filter = User.objects.get(id=user_id)
            output, filename = generate_users_activity_report(
                request.user, user_filter, period_type, date_from, date_to
            )

        elif report_type == 'messages_report':
            output, filename = generate_messages_report(
                request.user, period_type, date_from, date_to
            )

        elif report_type == 'advanced_custom':
            output, filename = generate_advanced_custom_report(
                request.user, selected_reports, period_type, date_from, date_to
            )

        else:
            # تقرير مخصص
            output, filename = generate_custom_report(
                request.user, report_type, period_type, date_from, date_to
            )

        # تسجيل النشاط
        ActivityLog.log_activity(
            user=request.user,
            action='export',
            title=f'توليد تقرير {report_type}',
            description=f'تم توليد التقرير بنجاح',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            session_key=request.session.session_key
        )

        # إرجاع الملف
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        logger.error(f"خطأ في توليد التقرير: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@dashboard_required
def report_logs_view(request):
    """عرض سجل التقارير"""
    try:
        from .models import ReportLog

        logs = ReportLog.objects.select_related('generated_by', 'user_filter').order_by('-created_at')

        paginator = Paginator(logs, 20)
        logs_page = paginator.get_page(request.GET.get('page'))

        context = {
            'logs_page': logs_page,
            'page_title': 'سجل التقارير',
        }

        return render(request, 'dashboard/report_logs.html', context)

    except Exception as e:
        logger.error(f"خطأ في صفحة سجل التقارير: {e}")
        messages.error(request, 'حدث خطأ')
        return redirect('dashboard:reports')


@require_http_methods(["GET", "POST"])
@dashboard_required
def regenerate_report_ajax(request, log_id):
    """إعادة توليد تقرير من السجل"""
    try:
        from django.contrib.auth import get_user_model

        log = get_object_or_404(ReportLog, id=log_id)

        # إعادة توليد التقرير بنفس الإعدادات
        if log.report_type == 'monthly_summary':
            output, filename = generate_monthly_report(request.user)

        elif log.report_type == 'yearly_summary':
            output, filename = generate_yearly_report(request.user)

        elif log.report_type == 'projects_report':
            output, filename = generate_projects_report(
                request.user,
                log.period_type,
                log.date_from,
                log.date_to,
                None  # category_id غير محفوظ في السجل
            )

        elif log.report_type == 'users_activity':
            output, filename = generate_users_activity_report(
                request.user, log.user_filter, log.period_type,
                log.date_from, log.date_to
            )

        elif log.report_type == 'messages_report':
            output, filename = generate_messages_report(
                request.user, log.period_type, log.date_from, log.date_to
            )

        elif log.report_type == 'advanced_custom':
            # للتقرير المخصص المتقدم - نعيد توليده بدون selected_reports
            # لأنه غير محفوظ في السجل
            output, filename = generate_custom_report(
                request.user, log.report_type, log.period_type,
                log.date_from, log.date_to
            )

        else:
            # باقي التقارير المخصصة
            output, filename = generate_custom_report(
                request.user, log.report_type, log.period_type,
                log.date_from, log.date_to
            )

        # تسجيل النشاط
        ActivityLog.log_activity(
            user=request.user,
            action='export',
            title='إعادة توليد تقرير',
            description=f'تم إعادة توليد: {log.get_report_type_display()}',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            session_key=request.session.session_key
        )

        # إرجاع الملف للتحميل
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        logger.error(f"خطأ في إعادة توليد التقرير: {e}")
        return HttpResponse(
            json.dumps({'success': False, 'error': str(e)}),
            content_type='application/json',
            status=500
        )


@require_POST
@admin_required
def delete_report_log_ajax(request, log_id):
    """حذف تقرير من السجل"""
    try:
        log = get_object_or_404(ReportLog, id=log_id)
        log_name = log.get_report_type_display()

        # حذف الملف الفعلي
        import os
        from django.conf import settings

        file_path = os.path.join(settings.MEDIA_ROOT, log.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)

        ActivityLog.log_activity(
            user=request.user,
            action='delete',
            title='حذف سجل تقرير',
            description=f'تم حذف: {log_name}',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            session_key=request.session.session_key
        )

        log.delete()

        return JsonResponse({
            'success': True,
            'message': 'تم حذف السجل بنجاح'
        })

    except Exception as e:
        logger.error(f"خطأ في حذف سجل التقرير: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@dashboard_required
def report_details_ajax(request, log_id):
    """عرض تفاصيل التقرير"""
    try:
        log = get_object_or_404(ReportLog, id=log_id)

        data = {
            'report_type': log.get_report_type_display(),
            'period_type': log.get_period_type_display(),
            'file_name': log.file_name,
            'file_size': log.get_file_size_display(),
            'records_count': log.records_count,
            'generated_by': log.generated_by.username,
            'user_filter': log.user_filter.username if log.user_filter else None,
            'date_from': log.date_from.strftime('%Y/%m/%d') if log.date_from else None,
            'date_to': log.date_to.strftime('%Y/%m/%d') if log.date_to else None,
            'created_at': log.created_at.strftime('%Y/%m/%d %H:%M'),
        }

        return JsonResponse({'success': True, 'data': data})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



# ========================================
# صفحة الإعدادات
# ========================================

@admin_required
def settings_view(request):
    """صفحة إعدادات النظام"""
    try:
        if request.method == 'POST':
            return save_settings(request)

        # الحصول على الإعدادات الحالية
        settings_data = get_current_settings()

        # معلومات النظام
        system_info = get_system_info()

        context = {
            'form': settings_data,
            'dashboard_system_info': system_info,
            'page_title': 'إعدادات النظام',
        }

        return render(request, 'dashboard/settings.html', context)

    except Exception as e:
        logger.error(f"خطأ في صفحة الإعدادات: {e}")
        messages.error(request, 'حدث خطأ في تحميل الإعدادات')
        return redirect('dashboard:home')


def get_current_settings():
    """الحصول على الإعدادات الحالية - محدث"""
    try:
        settings_obj = SiteSetting.objects.first()
        if not settings_obj:
            settings_obj = SiteSetting.objects.create()

        return {
            # عام
            'site_name_ar': settings_obj.site_name_ar or 'جمعية نسائم فلسطين',
            'site_name_en': settings_obj.site_name_en or 'Nasaeem Palestine',
            'site_description': settings_obj.site_description or '',
            'site_email': settings_obj.site_email or 'info@nasaeem-palestine.org',
            'site_phone': settings_obj.site_phone or '',

            # الصيانة
            'site_maintenance_mode': settings_obj.maintenance_mode,
            'maintenance_message_ar': settings_obj.maintenance_message_ar or 'الموقع تحت الصيانة',
            'maintenance_message_en': settings_obj.maintenance_message_en or 'Site under maintenance',

            # الأمان
            'enable_two_factor': settings_obj.enable_two_factor,
            'session_timeout': settings_obj.session_timeout or 30,
            'max_login_attempts': settings_obj.max_login_attempts or 5,
            'force_https': settings_obj.force_https,
            'enable_ip_blocking': settings_obj.enable_ip_blocking,

            # الأداء
            'cache_timeout': settings_obj.cache_timeout or 3600,
            'enable_compression': settings_obj.enable_compression,
            'enable_lazy_loading': settings_obj.enable_lazy_loading,
            'enable_minification': settings_obj.enable_minification,
        }
    except Exception as e:
        logger.error(f"خطأ في get_current_settings: {e}")
        return {
            'site_name_ar': 'جمعية نسائم فلسطين',
            'site_name_en': 'Nasaeem Palestine',
            'site_description': '',
            'site_email': 'info@nasaeem-palestine.org',
            'site_phone': '',
            'site_maintenance_mode': False,
            'maintenance_message_ar': 'الموقع تحت الصيانة',
            'maintenance_message_en': 'Site under maintenance',
            'enable_two_factor': False,
            'session_timeout': 30,
            'max_login_attempts': 5,
            'force_https': False,
            'enable_ip_blocking': False,
            'cache_timeout': 3600,
            'enable_compression': True,
            'enable_lazy_loading': True,
            'enable_minification': False,
        }


def get_system_info():
    """معلومات النظام"""
    import django
    import sys

    try:
        db_size = get_database_size()
    except:
        db_size = 'غير متاح'

    return {
        'django_version': django.get_version(),
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'debug_mode': settings.DEBUG,
        'database_size': db_size,
        'current_time': datetime.now(),
    }




def save_settings(request):
    """حفظ الإعدادات - محدث"""
    try:
        settings_obj = SiteSetting.objects.first()
        if not settings_obj:
            settings_obj = SiteSetting.objects.create()

        # الحقول النصية
        text_fields = [
            'site_name_ar', 'site_name_en', 'site_description',
            'site_email', 'site_phone',
            'maintenance_message_ar', 'maintenance_message_en'
        ]

        for field in text_fields:
            value = request.POST.get(field, '')
            if hasattr(settings_obj, field):
                setattr(settings_obj, field, value)

        # الحقول الرقمية
        number_fields = {
            'session_timeout': 30,
            'max_login_attempts': 5,
            'cache_timeout': 3600
        }

        for field, default in number_fields.items():
            value = request.POST.get(field, default)
            try:
                value = int(value) if value else default
            except ValueError:
                value = default
            if hasattr(settings_obj, field):
                setattr(settings_obj, field, value)

        # الحقول Boolean (checkboxes)
        boolean_fields = [
            'maintenance_mode',
            'enable_two_factor',
            'force_https',
            'enable_ip_blocking',
            'enable_compression',
            'enable_lazy_loading',
            'enable_minification'
        ]

        for field in boolean_fields:
            value = field in request.POST
            if hasattr(settings_obj, field):
                setattr(settings_obj, field, value)

        settings_obj.save()

        # التحقق من نوع الطلب
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        # تسجيل النشاط
        ActivityLog.log_activity(
            user=request.user,
            action='update',
            title='تحديث إعدادات الموقع',
            description='تم تحديث إعدادات الموقع بنجاح',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            session_key=request.session.session_key
        )

        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': 'تم حفظ الإعدادات بنجاح'
            })
        else:
            messages.success(request, 'تم حفظ الإعدادات بنجاح')
            return redirect('dashboard:settings')

    except Exception as e:
        logger.error(f"خطأ في حفظ الإعدادات: {e}")

        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if is_ajax:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
        else:
            messages.error(request, 'فشل في حفظ الإعدادات')
            return redirect('dashboard:settings')


# ========================================
# API Endpoints
# ========================================

@require_POST
@admin_required
def clear_cache_api(request):
    """مسح الكاش"""
    try:
        cache.clear()
        return JsonResponse({'success': True, 'message': 'تم مسح الكاش بنجاح'})
    except Exception as e:
        logger.error(f"خطأ في مسح الكاش: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
@admin_required
def optimize_database_api(request):
    """تحسين قاعدة البيانات"""
    try:
        with connection.cursor() as cursor:
            tables = connection.introspection.table_names()
            for table in tables:
                cursor.execute(f'OPTIMIZE TABLE `{table}`')
        return JsonResponse({'success': True, 'message': f'تم تحسين {len(tables)} جدول بنجاح'})
    except Exception as e:
        logger.error(f"خطأ في تحسين قاعدة البيانات: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
@admin_required
def check_performance_api(request):
    """فحص الأداء"""
    try:
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent

        # تحديد الحالة
        if cpu < 50 and memory < 50:
            status = 'excellent'
            status_text = 'ممتاز'
        elif cpu < 70 and memory < 70:
            status = 'good'
            status_text = 'جيد'
        else:
            status = 'warning'
            status_text = 'يحتاج تحسين'

        return JsonResponse({
            'success': True,
            'response_time': '150',
            'memory_usage': f"{memory:.1f}",
            'cpu_usage': f"{cpu:.1f}",
            'cache_size': '2.5 MB',
            'status': status,
            'status_text': status_text
        })
    except Exception as e:
        logger.error(f"خطأ في فحص الأداء: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

# ========================================
# Ajax APIs - وظائف مساعدة موحدة
# ========================================

def log_delete_activity(user, item_name, item_type, request):
    """دالة موحدة لتسجيل نشاط الحذف"""
    ActivityLog.log_activity(
        user=user, action='delete', title=f'حذف {item_type}',
        description=f'تم حذف: {item_name}',
        ip_address=get_client_ip(request), user_agent=get_user_agent(request),
        session_key=request.session.session_key
    )


def log_update_activity(user, item_name, item_type, content_object, request):
    """دالة موحدة لتسجيل نشاط التحديث"""
    ActivityLog.log_activity(
        user=user, action='update', title=f'تحديث {item_type}',
        description=f'تم تحديث: {item_name}', content_object=content_object,
        ip_address=get_client_ip(request), user_agent=get_user_agent(request),
        session_key=request.session.session_key
    )


# ========================================
# APIs - السلايدر
# ========================================
@require_http_methods(["GET"])
@dashboard_required
def view_slider_ajax(request, item_id):
    """عرض تفاصيل شريحة السلايدر"""
    try:
        slider_item = get_object_or_404(HomeSlider, id=item_id)

        data = {
            'id': slider_item.id,
            'title_ar': slider_item.title_ar,
            'title_en': slider_item.title_en or '',
            'subtitle_ar': slider_item.subtitle_ar or '',
            'subtitle_en': slider_item.subtitle_en or '',
            'description_ar': slider_item.description_ar or '',
            'description_en': slider_item.description_en or '',
            'button_text_ar': slider_item.button_text_ar or '',
            'button_text_en': slider_item.button_text_en or '',
            'button_url': slider_item.button_url or '',
            'order': slider_item.order,
            'is_active': slider_item.is_active,
            'image_url': slider_item.image.url if slider_item.image else None,
        }
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
@require_http_methods(["GET", "POST"])
@editor_required
def edit_slider_ajax(request, item_id):
    """تعديل شريحة السلايدر"""
    try:
        from main.forms import HomeSliderForm
        slider_item = get_object_or_404(HomeSlider, id=item_id)

        if request.method == 'GET':
            data = {
                'id': slider_item.id,
                'title_ar': slider_item.title_ar,
                'title_en': slider_item.title_en or '',
                'subtitle_ar': slider_item.subtitle_ar or '',
                'subtitle_en': slider_item.subtitle_en or '',
                'description_ar': slider_item.description_ar or '',
                'description_en': slider_item.description_en or '',
                'button_text_ar': slider_item.button_text_ar or '',
                'button_text_en': slider_item.button_text_en or '',
                'button_url': slider_item.button_url or '',
                'order': slider_item.order,
                'is_active': slider_item.is_active,
                'image_url': slider_item.image.url if slider_item.image else None,
            }
            return JsonResponse({'success': True, 'data': data})

        else:  # POST
            form = HomeSliderForm(request.POST, request.FILES, instance=slider_item)
            if form.is_valid():
                updated = form.save()
                log_update_activity(request.user, updated.title_ar, 'شريحة سلايدر', updated, request)
                return JsonResponse({'success': True, 'message': 'تم التحديث بنجاح'})
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    except Exception as e:
        logger.error(f"خطأ في تعديل شريحة السلايدر: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@editor_required
def delete_slider_ajax(request, item_id):
    """حذف شريحة السلايدر"""
    try:
        slider_item = get_object_or_404(HomeSlider, id=item_id)
        title = slider_item.title_ar
        log_delete_activity(request.user, title, 'شريحة سلايدر', request)
        slider_item.delete()
        return JsonResponse({'success': True, 'message': 'تم الحذف بنجاح'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ========================================
# APIs - الإحصائيات
# ========================================

@require_http_methods(["GET", "POST"])
@editor_required
def edit_statistic_ajax(request, item_id):

        """تعديل إحصائية"""
        try:


            stat = get_object_or_404(Statistic, id=item_id)

            if request.method == 'GET':
                data = {
                    'id': stat.id,
                    'title_ar': stat.title_ar,
                    'title_en': stat.title_en or '',
                    'number': stat.number,
                    'auto_update_from': stat.auto_update_from or '',
                    'suffix_ar': stat.suffix_ar or '',
                    'suffix_en': stat.suffix_en or '',
                    'icon': stat.icon,
                    'color': stat.color or '#6B8E23',
                    'order': stat.order,
                    'is_active': stat.is_active,
                }
                return JsonResponse({'success': True, 'data': data})

            else:  # POST
                form = StatisticForm(request.POST, instance=stat)
                if form.is_valid():
                    updated = form.save()
                    log_update_activity(request.user, updated.title_ar, 'إحصائية', updated, request)
                    return JsonResponse({'success': True, 'message': 'تم التحديث بنجاح'})
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)

        except Exception as e:
            logger.error(f"خطأ في تعديل الإحصائية: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)





@require_http_methods(["GET", "POST"])
@editor_required  # أو @dashboard_required حسب نظامك
def edit_stat_ajax(request, item_id):
    """تعديل إحصائية"""
    try:


        stat = get_object_or_404(Statistic, id=item_id)

        if request.method == 'GET':
            data = {
                'id': stat.id,
                'title_ar': stat.title_ar,
                'title_en': stat.title_en or '',
                'number': stat.number,
                'auto_update_from': stat.auto_update_from or '',
                'suffix_ar': stat.suffix_ar or '',
                'suffix_en': stat.suffix_en or '',
                'icon': stat.icon,
                'color': stat.color or '#6B8E23',
                'order': stat.order,
                'is_active': stat.is_active,
            }
            return JsonResponse({'success': True, 'data': data})

        else:  # POST
            # معالجة البيانات
            stat.title_ar = request.POST.get('title_ar')
            stat.title_en = request.POST.get('title_en', '')
            stat.number = request.POST.get('number', 0)
            stat.auto_update_from = request.POST.get('auto_update_from', '')
            stat.suffix_ar = request.POST.get('suffix_ar', '')
            stat.suffix_en = request.POST.get('suffix_en', '')
            stat.icon = request.POST.get('icon')
            stat.color = request.POST.get('color', '#6B8E23')
            stat.order = request.POST.get('order', 0)
            stat.is_active = request.POST.get('is_active') == 'on'

            stat.save()

            # سجل النشاط إذا كان لديك
            # log_update_activity(request.user, stat.title_ar, 'إحصائية', stat, request)

            return JsonResponse({'success': True, 'message': 'تم التحديث بنجاح'})

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"خطأ في تعديل الإحصائية: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_POST
@editor_required
def delete_statistic_ajax(request, item_id):
    """حذف إحصائية"""
    try:
        statistic = get_object_or_404(Statistic, id=item_id)
        title = statistic.title_ar
        log_delete_activity(request.user, title, 'إحصائية', request)
        statistic.delete()
        return JsonResponse({'success': True, 'message': 'تم الحذف بنجاح'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ========================================
# APIs - الأهداف
# ========================================

@require_http_methods(["GET", "POST"])
@editor_required
def edit_goal_ajax(request, item_id):
    """تعديل هدف"""
    try:
        from main.forms import GoalForm
        goal = get_object_or_404(Goal, id=item_id)

        if request.method == 'GET':
            data = {
                'id': goal.id,
                'title_ar': goal.title_ar,
                'title_en': goal.title_en or '',
                'description_ar': goal.description_ar or '',
                'description_en': goal.description_en or '',
                'icon': goal.icon,
                'order': goal.order,
                'is_active': goal.is_active,
            }
            return JsonResponse({'success': True, 'data': data})

        else:  # POST
            used_icons = list(Goal.objects.exclude(id=item_id).values_list('icon', flat=True))
            form = GoalForm(request.POST, instance=goal, used_icons=used_icons)
            if form.is_valid():
                updated = form.save()
                log_update_activity(request.user, updated.title_ar, 'هدف', updated, request)
                return JsonResponse({'success': True, 'message': 'تم التحديث بنجاح'})
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@editor_required
def delete_goal_ajax(request, item_id):
    """حذف هدف"""
    try:
        goal = get_object_or_404(Goal, id=item_id)
        title = goal.title_ar
        log_delete_activity(request.user, title, 'هدف', request)
        goal.delete()
        return JsonResponse({'success': True, 'message': 'تم الحذف بنجاح'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ========================================
# APIs - مجلس الإدارة
# ========================================







@require_http_methods(["POST"])
@editor_required
def add_board_member(request):
    """إضافة عضو جديد لمجلس الإدارة"""
    try:
        # إنشاء عضو جديد
        member = BoardMember()

        # المعلومات الأساسية
        member.name_ar = request.POST.get('name_ar', '').strip()
        member.name_en = request.POST.get('name_en', '').strip()

        # ✅ معالجة المنصب
        is_custom = request.POST.get('is_custom_position') == 'on'
        member.is_custom_position = is_custom

        if is_custom:
            # منصب مخصص
            member.position_type_ar = request.POST.get('position_type_ar', '').strip()
            member.position_type_en = request.POST.get('position_type_en', '').strip()
            member.position_type = None

            if not member.position_type_ar or not member.position_type_en:
                return JsonResponse({
                    'success': False,
                    'error': 'يجب إدخال المنصب بالعربية والإنجليزية'
                }, status=400)
        else:
            # من القائمة
            position_type = request.POST.get('position_type', 'member').strip()
            member.position_type = position_type

            # تعيين الترجمات
            position_arabic = {
                'president': 'رئيس مجلس الإدارة',
                'vice_president': 'نائب الرئيس',
                'secretary': 'السكرتير',
                'treasurer': 'أمين الصندوق',
                'member': 'عضو'
            }

            position_english = {
                'president': 'President of the Board',
                'vice_president': 'Vice President',
                'secretary': 'Secretary',
                'treasurer': 'Treasurer',
                'member': 'Member'
            }

            member.position_type_ar = position_arabic.get(position_type, 'عضو')
            member.position_type_en = position_english.get(position_type, 'Member')

        # النبذة
        member.bio_ar = request.POST.get('bio_ar', '').strip()
        member.bio_en = request.POST.get('bio_en', '').strip()

        # معلومات الاتصال
        member.email = request.POST.get('email', '').strip()
        member.phone = request.POST.get('phone', '').strip()

        # وسائل التواصل الاجتماعي
        member.facebook_url = request.POST.get('facebook_url', '').strip()
        member.twitter_url = request.POST.get('twitter_url', '').strip()
        member.linkedin_url = request.POST.get('linkedin_url', '').strip()

        # الإعدادات
        try:
            member.order = int(request.POST.get('order', 0))
        except ValueError:
            member.order = 0

        member.is_active = request.POST.get('is_active') == 'on'

        # رفع الصورة
        if 'photo' in request.FILES:
            member.photo = request.FILES['photo']

        # حفظ العضو
        member.save()

        logger.info(f"تم إضافة عضو جديد: {member.name_ar}")

        return JsonResponse({
            'success': True,
            'message': 'تم إضافة العضو بنجاح'
        })

    except Exception as e:
        logger.error(f"خطأ في إضافة عضو جديد: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ أثناء إضافة العضو'
        }, status=500)
@require_http_methods(["GET"])
@login_required
def view_board_member_ajax(request, item_id):
    """عرض تفاصيل عضو مجلس الإدارة"""
    try:
        member = get_object_or_404(BoardMember, id=item_id)

        data = {
            'id': member.id,
            'name_ar': member.name_ar,
            'name_en': member.name_en or '',

            # ✅ المنصب المحدث
            'position_type_ar': member.position_type_ar,
            'position_type_en': member.position_type_en or '',
            'is_custom_position': member.is_custom_position,

            # النبذة
            'bio_ar': member.bio_ar or '',
            'bio_en': member.bio_en or '',

            # الصورة
            'photo_url': member.photo.url if member.photo else None,

            # معلومات الاتصال
            'email': member.email or '',
            'phone': member.phone or '',

            # وسائل التواصل الاجتماعي
            'facebook_url': member.facebook_url or '',
            'twitter_url': member.twitter_url or '',
            'linkedin_url': member.linkedin_url or '',
            'social_links': member.get_social_links(),

            # الإعدادات
            'order': member.order,
            'is_active': member.is_active,
        }

        return JsonResponse({'success': True, 'data': data})

    except Exception as e:
        logger.error(f"خطأ في عرض عضو مجلس الإدارة {item_id}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ أثناء تحميل البيانات'
        }, status=500)
@require_http_methods(["GET", "POST"])
@login_required
def edit_board_member_ajax(request, item_id):
    """تعديل عضو مجلس الإدارة"""
    try:
        member = get_object_or_404(BoardMember, id=item_id)

        if request.method == 'GET':
            # ✅ جلب البيانات للتعديل
            data = {
                'id': member.id,
                'name_ar': member.name_ar,
                'name_en': member.name_en or '',

                # ✅ المنصب المحدث
                'position_type_ar': member.position_type_ar,
                'position_type_en': member.position_type_en or '',
                'position_type': member.position_type or '',
                'is_custom_position': member.is_custom_position,

                # النبذة
                'bio_ar': member.bio_ar or '',
                'bio_en': member.bio_en or '',

                # الصورة
                'photo_url': member.photo.url if member.photo else None,

                # معلومات الاتصال
                'email': member.email or '',
                'phone': member.phone or '',

                # وسائل التواصل الاجتماعي
                'facebook_url': member.facebook_url or '',
                'twitter_url': member.twitter_url or '',
                'linkedin_url': member.linkedin_url or '',

                # الإعدادات
                'order': member.order,
                'is_active': member.is_active,
            }

            return JsonResponse({'success': True, 'data': data})

        else:  # POST
            # ✅ تحديث البيانات
            member.name_ar = request.POST.get('name_ar', '').strip()
            member.name_en = request.POST.get('name_en', '').strip()

            # ✅ معالجة المنصب
            is_custom = request.POST.get('is_custom_position') == 'on'
            member.is_custom_position = is_custom

            if is_custom:
                # منصب مخصص - استخدم الحقول النصية
                member.position_type_ar = request.POST.get('position_type_ar', '').strip()
                member.position_type_en = request.POST.get('position_type_en', '').strip()
                member.position_type = None  # إفراغ القائمة

                # التحقق من وجود القيم
                if not member.position_type_ar or not member.position_type_en:
                    return JsonResponse({
                        'success': False,
                        'error': 'يجب إدخال المنصب بالعربية والإنجليزية للمناصب المخصصة'
                    }, status=400)

            else:
                # من القائمة - استخدم القيمة المحددة
                position_type = request.POST.get('position_type', '').strip()

                if not position_type:
                    return JsonResponse({
                        'success': False,
                        'error': 'يجب اختيار نوع المنصب'
                    }, status=400)

                member.position_type = position_type

                # تعيين الترجمات من القاموس
                position_arabic = {
                    'president': 'رئيس مجلس الإدارة',
                    'vice_president': 'نائب الرئيس',
                    'secretary': 'السكرتير',
                    'treasurer': 'أمين الصندوق',
                    'member': 'عضو'
                }

                position_english = {
                    'president': 'President of the Board',
                    'vice_president': 'Vice President',
                    'secretary': 'Secretary',
                    'treasurer': 'Treasurer',
                    'member': 'Member'
                }

                member.position_type_ar = position_arabic.get(position_type, '')
                member.position_type_en = position_english.get(position_type, '')

            # ✅ النبذة
            member.bio_ar = request.POST.get('bio_ar', '').strip()
            member.bio_en = request.POST.get('bio_en', '').strip()

            # معلومات الاتصال
            member.email = request.POST.get('email', '').strip()
            member.phone = request.POST.get('phone', '').strip()

            # وسائل التواصل الاجتماعي
            member.facebook_url = request.POST.get('facebook_url', '').strip()
            member.twitter_url = request.POST.get('twitter_url', '').strip()
            member.linkedin_url = request.POST.get('linkedin_url', '').strip()

            # الإعدادات
            try:
                member.order = int(request.POST.get('order', 0))
            except ValueError:
                member.order = 0

            member.is_active = request.POST.get('is_active') == 'on'

            # ✅ رفع صورة جديدة
            if 'photo' in request.FILES:
                # حذف الصورة القديمة إذا كانت موجودة
                if member.photo:
                    try:
                        if os.path.isfile(member.photo.path):
                            os.remove(member.photo.path)
                    except Exception as e:
                        logger.warning(f"فشل حذف الصورة القديمة: {e}")

                member.photo = request.FILES['photo']
                logger.info(f"تم رفع صورة جديدة للعضو: {member.name_ar}")

            # حفظ التعديلات
            member.save()

            logger.info(f"تم تحديث عضو مجلس الإدارة: {member.name_ar} بواسطة {request.user.username}")

            return JsonResponse({
                'success': True,
                'message': 'تم تحديث العضو بنجاح'
            })

    except Exception as e:
        logger.error(f"خطأ في تعديل عضو مجلس الإدارة {item_id}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ أثناء تحديث العضو'
        }, status=500)
@require_http_methods(["POST"])
@login_required
def delete_board_member_ajax(request, item_id):
    """حذف عضو مجلس الإدارة"""
    try:
        member = get_object_or_404(BoardMember, id=item_id)
        member_name = member.name_ar

        # حذف الصورة من الخادم
        if member.photo:
            try:
                if os.path.isfile(member.photo.path):
                    os.remove(member.photo.path)
                    logger.info(f"تم حذف صورة العضو: {member_name}")
            except Exception as e:
                logger.warning(f"فشل حذف صورة العضو {member_name}: {e}")

        # حذف العضو من قاعدة البيانات
        member.delete()

        logger.info(f"تم حذف عضو مجلس الإدارة: {member_name} بواسطة {request.user.username}")

        return JsonResponse({
            'success': True,
            'message': 'تم حذف العضو بنجاح'
        })

    except Exception as e:
        logger.error(f"خطأ في حذف عضو مجلس الإدارة {item_id}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ أثناء حذف العضو'
        }, status=500)


# ========================================
# APIs - التصنيفات
# ========================================

@require_http_methods(["GET"])
@dashboard_required
def get_categories_ajax(request):
    """جلب جميع التصنيفات"""
    try:
        categories = Category.objects.all().order_by('category_ar')
        data = []

        for cat in categories:
            # عدد الأسئلة المرتبطة
            try:
                faqs_count = FAQ.objects.filter(category=cat).count()
            except:
                faqs_count = 0

            # التاريخ
            created_at = ''
            if hasattr(cat, 'created_at') and cat.created_at:
                created_at = cat.created_at.strftime('%Y-%m-%d %H:%M')

            data.append({
                'id': cat.id,
                'category_ar': cat.category_ar,
                'category_en': cat.category_en or '',
                'faqs_count': faqs_count,
                'created_at': created_at,
            })

        return JsonResponse({'success': True, 'data': data})

    except Exception as e:
        import traceback
        print("Error in get_categories_ajax:")
        print(traceback.format_exc())

        return JsonResponse({
            'success': False,
            'error': f'حدث خطأ: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
@editor_required
def add_category_ajax(request):
    """إضافة تصنيف جديد"""
    try:
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()

            # تسجيل النشاط
            ActivityLog.log_activity(
                user=request.user,
                action='create',
                title='إضافة تصنيف FAQ',
                description=f'تم إضافة تصنيف جديد: {category.category_ar}',
                content_object=category,
                level='success',
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                session_key=request.session.session_key if request.session.session_key else ''
            )

            return JsonResponse({
                'success': True,
                'message': 'تم إضافة التصنيف بنجاح',
                'data': {
                    'id': category.id,
                    'category_ar': category.category_ar,
                    'category_en': category.category_en or '',
                    'faqs_count': 0,
                    'created_at': category.created_at.strftime('%Y-%m-%d %H:%M') if hasattr(category,
                                                                                            'created_at') else '',
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'بيانات غير صالحة',
                'errors': form.errors
            }, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@editor_required
def edit_category_ajax(request, cat_id):
    """تعديل تصنيف"""
    try:
        category = get_object_or_404(Category, id=cat_id)

        category.category_ar = request.POST.get('category_ar', '').strip()
        category.category_en = request.POST.get('category_en', '').strip()

        if not category.category_ar:
            return JsonResponse({
                'success': False,
                'error': 'الاسم بالعربية مطلوب'
            }, status=400)

        category.save()

        # تسجيل النشاط
        ActivityLog.log_activity(
            user=request.user,
            action='update',
            title='تعديل تصنيف FAQ',
            description=f'تم تعديل تصنيف: {category.category_ar}',
            content_object=category,
            level='success',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            session_key=request.session.session_key if request.session.session_key else ''
        )

        return JsonResponse({
            'success': True,
            'message': 'تم تحديث التصنيف بنجاح',
            'data': {
                'id': category.id,
                'category_ar': category.category_ar,
                'category_en': category.category_en or '',
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@editor_required
def delete_category_ajax(request, cat_id):
    """حذف تصنيف"""
    try:
        category = get_object_or_404(Category, id=cat_id)

        # التحقق من وجود أسئلة مرتبطة
        faqs_count = FAQ.objects.filter(category=category).count()
        if faqs_count > 0:
            return JsonResponse({
                'success': False,
                'error': f'لا يمكن حذف التصنيف لأنه مرتبط بـ {faqs_count} سؤال/أسئلة'
            }, status=400)

        category_name = category.category_ar

        # تسجيل النشاط قبل الحذف
        ActivityLog.log_activity(
            user=request.user,
            action='delete',
            title='حذف تصنيف FAQ',
            description=f'تم حذف تصنيف: {category_name}',
            level='warning',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            session_key=request.session.session_key if request.session.session_key else ''
        )

        category.delete()

        return JsonResponse({
            'success': True,
            'message': f'تم حذف التصنيف "{category_name}" بنجاح'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ========================================
# APIs - الأسئلة الشائعة
# ========================================
@require_POST
@editor_required
def add_faq_ajax(request):
    """إضافة سؤال شائع جديد"""
    try:
        # التحقق من البيانات الأساسية
        question_ar = request.POST.get('question_ar', '').strip()
        answer_ar = request.POST.get('answer_ar', '').strip()

        if not question_ar:
            return JsonResponse({
                'success': False,
                'error': 'السؤال بالعربية مطلوب'
            }, status=400)

        if not answer_ar:
            return JsonResponse({
                'success': False,
                'error': 'الإجابة بالعربية مطلوبة'
            }, status=400)

        # إنشاء سؤال جديد
        faq = FAQ()

        # الأسئلة
        faq.question_ar = question_ar
        faq.question_en = request.POST.get('question_en', '').strip()

        # الإجابات
        faq.answer_ar = answer_ar
        faq.answer_en = request.POST.get('answer_en', '').strip()

        # التصنيف (ForeignKey)
        category_id = request.POST.get('category', '').strip()
        if category_id:
            try:
                faq.category = Category.objects.get(id=int(category_id))
            except (Category.DoesNotExist, ValueError):
                faq.category = None
        else:
            faq.category = None

        # العلامات
        faq.tags_ar = request.POST.get('tags_ar', '').strip()
        faq.tags_en = request.POST.get('tags_en', '').strip()

        # الترتيب
        order_value = request.POST.get('order', '0').strip()
        faq.order = int(order_value) if order_value.isdigit() else 0

        # الحالة
        faq.is_active = request.POST.get('is_active') == 'on'

        # حفظ السؤال
        faq.save()

        # تسجيل النشاط
        ActivityLog.log_activity(
            user=request.user,
            action='create',
            title='إضافة سؤال شائع',
            description=f'تم إضافة سؤال: {faq.question_ar[:50]}',
            content_object=faq,
            level='success',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            session_key=request.session.session_key if request.session.session_key else ''
        )

        logger.info(f"✅ تم إضافة سؤال شائع: {faq.question_ar} بواسطة {request.user.username}")

        return JsonResponse({
            'success': True,
            'message': 'تم إضافة السؤال بنجاح'
        })

    except Exception as e:
        logger.error(f"❌ خطأ في إضافة سؤال شائع: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ أثناء إضافة السؤال'
        }, status=500)



@require_http_methods(["GET", "POST"])
@editor_required
def edit_faq_ajax(request, item_id):
    """تعديل سؤال شائع"""
    try:
        faq = get_object_or_404(FAQ, id=item_id)

        if request.method == 'GET':
            # جلب بيانات السؤال للتعديل
            data = {
                'id': faq.id,
                'question_ar': faq.question_ar,
                'question_en': faq.question_en or '',
                'answer_ar': faq.answer_ar,
                'answer_en': faq.answer_en or '',
                'category_id': faq.category.id if faq.category else '',
                'tags_ar': faq.tags_ar or '',
                'tags_en': faq.tags_en or '',
                'order': faq.order,
                'is_active': faq.is_active,
            }
            return JsonResponse({'success': True, 'data': data})

        else:  # POST - حفظ التعديلات
            faq.question_ar = request.POST.get('question_ar', '').strip()
            faq.question_en = request.POST.get('question_en', '').strip()
            faq.answer_ar = request.POST.get('answer_ar', '').strip()
            faq.answer_en = request.POST.get('answer_en', '').strip()

            # التصنيف (ForeignKey)
            category_id = request.POST.get('category', '').strip()
            if category_id:
                try:
                    faq.category = Category.objects.get(id=int(category_id))
                except (Category.DoesNotExist, ValueError):
                    faq.category = None
            else:
                faq.category = None

            # العلامات
            faq.tags_ar = request.POST.get('tags_ar', '').strip()
            faq.tags_en = request.POST.get('tags_en', '').strip()

            # الترتيب
            order_value = request.POST.get('order', '0').strip()
            faq.order = int(order_value) if order_value.isdigit() else 0

            faq.is_active = 'is_active' in request.POST

            faq.save()

            # تسجيل النشاط
            ActivityLog.log_activity(
                user=request.user,
                action='update',
                title='تعديل سؤال شائع',
                description=f'تم تعديل سؤال: {faq.question_ar[:50]}',
                content_object=faq,
                level='success',
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                session_key=request.session.session_key if request.session.session_key else ''
            )

            return JsonResponse({'success': True, 'message': 'تم التحديث بنجاح'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET"])
@dashboard_required
def view_faq_ajax(request, item_id):
    """عرض تفاصيل سؤال شائع"""
    try:
        faq = get_object_or_404(FAQ, id=item_id)

        data = {
            'id': faq.id,
            'question_ar': faq.question_ar,
            'question_en': faq.question_en or '',
            'answer_ar': faq.answer_ar,
            'answer_en': faq.answer_en or '',
            'category': faq.category.category_ar if faq.category else 'غير محدد',
            'tags_ar': faq.tags_ar or '',
            'tags_en': faq.tags_en or '',
            'order': faq.order,
            'is_active': faq.is_active,
            'views_count': faq.views_count,
            'helpful_votes': faq.helpful_votes,
            'created_at': faq.created_at.strftime('%Y-%m-%d %H:%M'),
            'updated_at': faq.updated_at.strftime('%Y-%m-%d %H:%M'),
        }
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@editor_required
def delete_faq_ajax(request, item_id):
    """حذف سؤال شائع"""
    try:
        faq = get_object_or_404(FAQ, id=item_id)
        question = faq.question_ar[:50]

        # تسجيل النشاط قبل الحذف
        ActivityLog.log_activity(
            user=request.user,
            action='delete',
            title='حذف سؤال شائع',
            description=f'تم حذف سؤال: {question}',
            level='warning',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            session_key=request.session.session_key if request.session.session_key else ''
        )

        faq.delete()

        return JsonResponse({'success': True, 'message': 'تم الحذف بنجاح'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
# ========================================
# APIs - رسائل التواصل
# ========================================
@require_http_methods(["GET"])
@dashboard_required
def view_message_ajax(request, item_id):
    """عرض رسالة تواصل"""
    try:
        message = get_object_or_404(ContactMessage, id=item_id)
        message.mark_as_read()

        # معالجة بيانات المرفق
        attachment_data = None
        if message.attachment:
            import os
            file_size = message.attachment.size
            # تحويل الحجم إلى صيغة قابلة للقراءة
            if file_size < 1024:
                size_str = f"{file_size} بايت"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.2f} كيلوبايت"
            else:
                size_str = f"{file_size / (1024 * 1024):.2f} ميجابايت"

            attachment_data = {
                'url': message.attachment.url,
                'name': os.path.basename(message.attachment.name),
                'size': size_str
            }

        data = {
            'id': message.id,
            'name': message.name,
            'email': message.email,
            'phone': str(message.phone) if message.phone else None,
            'subject': message.subject,
            'message': message.message,
            'status': message.get_status_display(),
            'priority': message.get_priority_display(),
            'created_at': message.created_at.strftime('%Y-%m-%d %H:%M'),
            'attachment': attachment_data,  # إضافة بيانات المرفق
            'reply_message': message.reply_message,
            'replied_by': message.replied_by.username if message.replied_by else None,
            'replied_at': message.replied_at.strftime('%Y-%m-%d %H:%M') if message.replied_at else None,
        }
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@dashboard_required
def reply_message_ajax(request, item_id):
    """الرد على رسالة"""
    try:
        message = get_object_or_404(ContactMessage, id=item_id)
        reply_text = request.POST.get('reply_message', '').strip()
        status = request.POST.get('status', 'replied')

        if not reply_text:
            return JsonResponse({'success': False, 'error': 'الرد مطلوب'}, status=400)

        message.mark_as_replied(request.user, reply_text)
        message.status = status
        message.save()

        ActivityLog.log_activity(
            user=request.user, action='reply', title='الرد على رسالة تواصل',
            description=f'تم الرد على رسالة من: {message.name}', content_object=message,
            ip_address=get_client_ip(request), user_agent=get_user_agent(request),
            session_key=request.session.session_key
        )

        return JsonResponse({'success': True, 'message': 'تم إرسال الرد بنجاح'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@dashboard_required
def delete_message_ajax(request, item_id):
    """حذف رسالة"""
    try:
        message = get_object_or_404(ContactMessage, id=item_id)
        name = message.name
        log_delete_activity(request.user, name, 'رسالة تواصل', request)
        message.delete()
        return JsonResponse({'success': True, 'message': 'تم الحذف بنجاح'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ========================================
# APIs - الاشتراكات البريدية
# ========================================

@require_http_methods(["GET"])
@dashboard_required
def view_newsletter_ajax(request, item_id):
    """عرض اشتراك بريدي"""
    try:
        newsletter = get_object_or_404(Newsletter, id=item_id)
        data = {
            'id': newsletter.id,
            'email': newsletter.email,
            'name': newsletter.name,
            'frequency': newsletter.frequency,
            'frequency_display': newsletter.get_frequency_display(),
            'is_active': newsletter.is_active,
            'is_confirmed': newsletter.is_confirmed,
            'subscribed_at': newsletter.subscribed_at.strftime('%Y-%m-%d %H:%M'),
            'emails_sent': newsletter.emails_sent,
            'last_email_sent': newsletter.last_email_sent.strftime(
                '%Y-%m-%d %H:%M') if newsletter.last_email_sent else None,
        }
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@dashboard_required
def delete_newsletter_ajax(request, item_id):
    """حذف اشتراك بريدي"""
    try:
        newsletter = get_object_or_404(Newsletter, id=item_id)
        email = newsletter.email
        log_delete_activity(request.user, email, 'اشتراك بريدي', request)
        newsletter.delete()
        return JsonResponse({'success': True, 'message': 'تم الحذف بنجاح'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ========================================
# APIs - روابط التواصل الاجتماعي
# ========================================
@require_http_methods(["GET"])
@dashboard_required
def get_available_platforms_ajax(request):
    """الحصول على المنصات المتاحة"""
    try:
        available_platforms = SocialMediaContact.get_available_platforms()
        platforms_data = [
            {
                'value': platform,
                'label': label,
                'icon': SocialMediaContact.PLATFORM_ICONS.get(platform, 'fas fa-link')
            }
            for platform, label in available_platforms
        ]
        return JsonResponse({
            'success': True,
            'platforms': platforms_data,
            'has_available': len(platforms_data) > 0
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ========================================
# APIs - روابط التواصل الاجتماعي
# ========================================
@require_http_methods(["GET"])
@dashboard_required
def view_social_ajax(request, item_id):
    """عرض رابط تواصل"""
    try:
        social = get_object_or_404(SocialMediaContact, id=item_id)
        data = {
            'id': social.id,
            'platform': social.platform,
            'platform_display': social.get_platform_display(),
            'username': social.username,
            'url': social.url,
            'icon_class': social.get_icon_class(),
            'order': social.order,
            'is_active': social.is_active,
            'clicks_count': social.clicks_count,
        }
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET", "POST"])
@editor_required
def edit_social_ajax(request, item_id):
    """تعديل رابط تواصل"""
    try:
        social = get_object_or_404(SocialMediaContact, id=item_id)

        if request.method == 'GET':
            data = {
                'id': social.id,
                'platform': social.platform,
                'platform_display': social.get_platform_display(),
                'username': social.username,
                'url': social.url,
                'icon_class': social.get_icon_class(),
                'order': social.order,
                'is_active': social.is_active,
            }
            return JsonResponse({'success': True, 'data': data})

        else:  # POST
            # تحديث الحقول المسموحة فقط (بدون platform و icon_class)
            social.username = request.POST.get('username', '').strip()
            social.url = request.POST.get('url', '').strip()

            order_value = request.POST.get('order', '0').strip()
            social.order = int(order_value) if order_value.isdigit() else 0

            social.is_active = 'is_active' in request.POST

            social.save()

            log_update_activity(
                request.user,
                social.get_platform_display(),
                'رابط تواصل',
                social,
                request
            )

            return JsonResponse({'success': True, 'message': 'تم التحديث بنجاح'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@editor_required
def delete_social_ajax(request, item_id):
    """حذف رابط تواصل"""
    try:
        social = get_object_or_404(SocialMediaContact, id=item_id)
        platform = social.get_platform_display()
        log_delete_activity(request.user, platform, 'رابط تواصل', request)
        social.delete()
        return JsonResponse({'success': True, 'message': 'تم الحذف بنجاح'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ========================================
# APIs - معلومات الاتصال
# ========================================


@require_http_methods(["GET"])
@dashboard_required
def view_contact_info_ajax(request, item_id):
    """عرض معلومة اتصال"""
    try:
        info = get_object_or_404(ContactInfo, id=item_id)
        data = {
            'id': info.id,
            'type': info.type,
            'type_ar': info.type_ar,  # التسمية العربية
            'type_en': info.type_en,  # التسمية الإنجليزية
            'value_ar': info.value_ar,  # ✅ القيمة بالعربية
            'value_en': info.value_en,  # ✅ القيمة بالإنجليزية
            'icon_class': info.get_icon_class(),
            'order': info.order,
            'show_in_footer': info.show_in_footer,
            'is_active': info.is_active,
        }
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET", "POST"])
@editor_required
def edit_contact_info_ajax(request, item_id):
    """تعديل معلومة اتصال"""
    try:
        info = get_object_or_404(ContactInfo, id=item_id)

        if request.method == 'GET':
            # جلب جميع الأيقونات المستخدمة ما عدا الأيقونة الحالية
            all_used_icons = list(
                ContactInfo.objects
                .exclude(id=item_id)
                .values_list('icon_class', flat=True)
            )

            data = {
                'id': info.id,
                'type': info.type,
                'type_ar': info.type_ar,
                'type_en': info.type_en,
                'value_ar': info.value_ar,  # ✅ القيمة بالعربية
                'value_en': info.value_en,  # ✅ القيمة بالإنجليزية
                'icon_class': info.icon_class,
                'order': info.order,
                'show_in_footer': info.show_in_footer,
                'is_active': info.is_active,
            }

            return JsonResponse({
                'success': True,
                'data': data,
                'all_used_icons': all_used_icons
            })

        else:  # POST
            # ✅ تحديث القيم بالعربية والإنجليزية
            value_ar = request.POST.get('value_ar', '').strip()
            value_en = request.POST.get('value_en', '').strip()

            # التحقق من أن القيمة العربية غير فارغة
            if not value_ar:
                return JsonResponse({
                    'success': False,
                    'error': 'يجب إدخال القيمة بالعربية'
                }, status=400)

            info.value_ar = value_ar
            info.value_en = value_en
            info.icon_class = request.POST.get('icon_class', '').strip()

            order_value = request.POST.get('order', '0').strip()
            info.order = int(order_value) if order_value.isdigit() else 0

            info.show_in_footer = 'show_in_footer' in request.POST
            info.is_active = 'is_active' in request.POST

            info.save()

            # استخدام type_ar في سجل النشاط
            log_update_activity(request.user, info.type_ar, 'معلومات اتصال', info, request)

            return JsonResponse({'success': True, 'message': 'تم التحديث بنجاح'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@editor_required
def delete_contact_info_ajax(request, item_id):
    """حذف معلومة اتصال"""
    try:
        info = get_object_or_404(ContactInfo, id=item_id)

        # استخدام type_ar في سجل النشاط
        display_name = info.type_ar

        log_delete_activity(request.user, display_name, 'معلومات اتصال', request)
        info.delete()

        return JsonResponse({'success': True, 'message': 'تم الحذف بنجاح'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET", "POST"])
@editor_required
def add_contact_info_ajax(request):
    """إضافة معلومة اتصال جديدة"""
    try:
        if request.method == 'GET':
            # جلب الأنواع المستخدمة (لأن type فريد)
            used_types = list(ContactInfo.objects.values_list('type', flat=True))

            # جلب الأيقونات المستخدمة
            used_icons = list(ContactInfo.objects.values_list('icon_class', flat=True))

            return JsonResponse({
                'success': True,
                'used_types': used_types,
                'used_icons': used_icons,
                'available_types': [
                    {'value': choice[0], 'label': str(choice[1])}
                    for choice in ContactInfo.INFO_TYPES
                    if choice[0] not in used_types
                ]
            })

        else:  # POST
            # استلام البيانات من الطلب
            type_value = request.POST.get('type', '').strip()
            value_ar = request.POST.get('value_ar', '').strip()
            value_en = request.POST.get('value_en', '').strip()
            icon_class = request.POST.get('icon_class', '').strip()
            order_value = request.POST.get('order', '0').strip()
            show_in_footer = 'show_in_footer' in request.POST
            is_active = 'is_active' in request.POST

            # التحقق من البيانات الأساسية
            if not type_value:
                return JsonResponse({
                    'success': False,
                    'error': 'يجب اختيار نوع المعلومة'
                }, status=400)

            if not value_ar:
                return JsonResponse({
                    'success': False,
                    'error': 'يجب إدخال القيمة بالعربية'
                }, status=400)

            # التحقق من عدم تكرار النوع
            if ContactInfo.objects.filter(type=type_value).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'معلومة من هذا النوع موجودة بالفعل'
                }, status=400)

            # إنشاء المعلومة الجديدة
            info = ContactInfo.objects.create(
                type=type_value,
                value_ar=value_ar,
                value_en=value_en,
                icon_class=icon_class,
                order=int(order_value) if order_value.isdigit() else 0,
                show_in_footer=show_in_footer,
                is_active=is_active
            )
            from dashboard.utils import log_create_activity, log_update_activity, log_delete_activity
            # تسجيل النشاط
            log_create_activity(request.user, info.type_ar, 'معلومات اتصال', info, request)

            return JsonResponse({
                'success': True,
                'message': 'تم الإضافة بنجاح',
                'data': {
                    'id': info.id,
                    'type': info.type,
                    'type_ar': info.type_ar,
                    'type_en': info.type_en,
                    'value_ar': info.value_ar,
                    'value_en': info.value_en,
                    'icon_class': info.get_icon_class(),
                    'order': info.order,
                    'show_in_footer': info.show_in_footer,
                    'is_active': info.is_active,
                }
            })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@editor_required
def toggle_contact_info_status_ajax(request, item_id):
    """تبديل حالة تفعيل معلومة الاتصال"""
    try:
        info = get_object_or_404(ContactInfo, id=item_id)
        info.is_active = not info.is_active
        info.save(update_fields=['is_active'])

        status_text = 'تفعيل' if info.is_active else 'إلغاء تفعيل'
        log_update_activity(
            request.user,
            f"{status_text} {info.type_ar}",
            'معلومات اتصال',
            info,
            request
        )

        return JsonResponse({
            'success': True,
            'message': f'تم {status_text} المعلومة بنجاح',
            'is_active': info.is_active
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@editor_required
def reorder_contact_info_ajax(request):
    """إعادة ترتيب معلومات الاتصال"""
    try:
        from django.db import transaction

        order_data = request.POST.get('order', '')
        if not order_data:
            return JsonResponse({
                'success': False,
                'error': 'بيانات الترتيب مفقودة'
            }, status=400)

        # تحليل بيانات الترتيب (مثال: "1,2,3,4" أو JSON)
        try:
            import json
            order_list = json.loads(order_data)
        except:
            order_list = [int(x.strip()) for x in order_data.split(',') if x.strip().isdigit()]

        # تحديث الترتيب
        with transaction.atomic():
            for index, item_id in enumerate(order_list, start=1):
                ContactInfo.objects.filter(id=item_id).update(order=index)

        log_update_activity(
            request.user,
            'إعادة ترتيب معلومات الاتصال',
            'معلومات اتصال',
            None,
            request
        )

        return JsonResponse({
            'success': True,
            'message': 'تم تحديث الترتيب بنجاح'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ========================================
# APIs عامة
# ========================================

@require_http_methods(["GET"])
@dashboard_required
def get_statistics_ajax(request):
    """API للحصول على الإحصائيات الحديثة"""
    try:
        statistics = get_dashboard_statistics()
        return JsonResponse({'success': True, 'data': statistics})
    except Exception as e:
        logger.error(f"خطأ في API الإحصائيات: {e}")
        return JsonResponse({'error': 'حدث خطأ في الخادم'}, status=500)


@require_http_methods(["GET"])
@dashboard_required
def get_chart_data_ajax(request):
    """API للحصول على بيانات المخططات"""
    try:
        chart_type = request.GET.get('type', '')
        period = int(request.GET.get('period', '30'))
        start_date = timezone.now() - timedelta(days=period)

        if chart_type == 'projects_timeline':
            data = list(Project.objects.filter(created_at__gte=start_date).extra(
                {'date': 'DATE(created_at)'}
            ).values('date').annotate(count=Count('id')).order_by('date'))

        elif chart_type == 'messages_timeline':
            data = list(ContactMessage.objects.filter(created_at__gte=start_date).extra(
                {'date': 'DATE(created_at)'}
            ).values('date').annotate(count=Count('id')).order_by('date'))

        elif chart_type == 'projects_by_status':
            data = list(Project.objects.values('status').annotate(count=Count('id')))

        else:
            return JsonResponse({'error': 'نوع مخطط غير صحيح'}, status=400)

        return JsonResponse({'success': True, 'data': data})

    except Exception as e:
        logger.error(f"خطأ في API بيانات المخططات: {e}")
        return JsonResponse({'error': 'حدث خطأ في الخادم'}, status=500)


@require_POST
@dashboard_required
def generate_report_ajax(request):
    """API لتوليد التقارير"""
    try:
        data = json.loads(request.body)
        report_type = data.get('type', '')
        format_type = data.get('format', 'pdf')

        if not report_type:
            return JsonResponse({'error': 'نوع التقرير مطلوب'}, status=400)

        report_result = generate_report(report_type, format_type, request.user)

        if report_result['success']:
            ActivityLog.log_activity(
                user=request.user, action='export', title=f'توليد تقرير {report_type}',
                description=f'تم توليد تقرير {report_type} بصيغة {format_type}',
                ip_address=get_client_ip(request), user_agent=get_user_agent(request),
                session_key=request.session.session_key
            )
            return JsonResponse({
                'success': True,
                'download_url': report_result['url'],
                'filename': report_result['filename']
            })
        else:
            return JsonResponse({'success': False, 'error': report_result['error']})

    except Exception as e:
        logger.error(f"خطأ في API توليد التقارير: {e}")
        return JsonResponse({'error': 'حدث خطأ في الخادم'}, status=500)


@require_POST
@admin_required
def update_user_status_ajax(request):
    """API لتحديث حالة المستخدم"""
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        is_active = data.get('is_active')

        user = get_object_or_404(User, id=user_id)
        user.is_active = is_active
        user.save()

        ActivityLog.log_activity(
            user=request.user, action='update', title='تحديث حالة المستخدم',
            description=f'تم {"تفعيل" if is_active else "إلغاء تفعيل"} المستخدم {user.username}',
            content_object=user, ip_address=get_client_ip(request),
            user_agent=get_user_agent(request), session_key=request.session.session_key
        )

        return JsonResponse({
            'success': True,
            'message': f'تم {"تفعيل" if is_active else "إلغاء تفعيل"} المستخدم بنجاح'
        })

    except Exception as e:
        logger.error(f"خطأ في API تحديث حالة المستخدم: {e}")
        return JsonResponse({'error': 'حدث خطأ في الخادم'}, status=500)


# ========================================
# APIs - فئات المشاريع
# ========================================

@require_http_methods(["GET"])
@dashboard_required
def view_project_category_ajax(request, item_id):
    """عرض فئة مشروع"""
    try:
        category = get_object_or_404(ProjectCategory, id=item_id)
        data = {
            'id': category.id,
            'name_ar': category.name_ar,
            'name_en': category.name_en,
            'slug': category.slug,
            'description_ar': category.description_ar,
            'description_en': category.description_en,
            'icon': category.icon,
            'color': category.color,
            'order': category.order,
            'is_active': category.is_active,
            'projects_count': category.get_projects_count(),
            'image_url': category.image.url if category.image else None,
        }
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET", "POST"])
@editor_required
def edit_project_category_ajax(request, item_id):
    """تعديل فئة مشروع"""
    try:
        category = get_object_or_404(ProjectCategory, id=item_id)

        if request.method == 'GET':
            data = {
                'id': category.id,
                'name_ar': category.name_ar,
                'name_en': category.name_en,
                'slug': category.slug,
                'description_ar': category.description_ar,
                'description_en': category.description_en,
                'icon': category.icon,
                'color': category.color,
                'order': category.order,
                'is_active': category.is_active,
            }
            return JsonResponse({'success': True, 'data': data})

        else:  # POST
            category.name_ar = request.POST.get('name_ar', '').strip()
            category.name_en = request.POST.get('name_en', '').strip()
            category.slug = request.POST.get('slug', '').strip()
            category.description_ar = request.POST.get('description_ar', '').strip()
            category.description_en = request.POST.get('description_en', '').strip()
            category.icon = request.POST.get('icon', '').strip()
            category.color = request.POST.get('color', '#6B8E23').strip()

            order_value = request.POST.get('order', '0').strip()
            category.order = int(order_value) if order_value.isdigit() else 0
            category.is_active = 'is_active' in request.POST

            if 'image' in request.FILES:
                category.image = request.FILES['image']

            category.save()
            log_update_activity(request.user, category.name_ar, 'فئة مشروع', category, request)
            return JsonResponse({'success': True, 'message': 'تم التحديث بنجاح'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@editor_required
def delete_project_category_ajax(request, item_id):
    """حذف فئة مشروع"""
    try:
        category = get_object_or_404(ProjectCategory, id=item_id)
        name = category.name_ar
        log_delete_activity(request.user, name, 'فئة مشروع', request)
        category.delete()
        return JsonResponse({'success': True, 'message': 'تم الحذف بنجاح'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ========================================
# APIs - المشاريع
# ========================================


from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods, require_POST
from django.db import models
import os
import logging
from datetime import datetime
from decimal import Decimal


@require_http_methods(["GET"])
def view_project_ajax(request, item_id):
    """عرض تفاصيل مشروع بشكل كامل"""
    try:
        # جلب المشروع
        project = get_object_or_404(Project, id=item_id)

        # ========================================
        # ✅ تعريف الألوان والأيقونات
        # ========================================
        status_colors = {
            'planning': '#6c757d',  # رمادي
            'active': '#28a745',  # أخضر
            'completed': '#007bff',  # أزرق
            'suspended': '#ffc107',  # أصفر
            'cancelled': '#dc3545',  # أحمر
        }

        priority_colors = {
            'low': '#28a745',  # أخضر
            'medium': '#ffc107',  # أصفر
            'high': '#fd7e14',  # برتقالي
            'urgent': '#dc3545',  # أحمر
        }

        status_icons = {
            'planning': 'fas fa-clipboard-list',
            'active': 'fas fa-play-circle',
            'completed': 'fas fa-check-circle',
            'suspended': 'fas fa-pause-circle',
            'cancelled': 'fas fa-times-circle',
        }

        priority_icons = {
            'low': 'fas fa-arrow-down',
            'medium': 'fas fa-minus',
            'high': 'fas fa-arrow-up',
            'urgent': 'fas fa-exclamation-triangle',
        }

        # ========================================
        # ✅ جلب الصور الإضافية مع معالجة الأخطاء
        # ========================================
        additional_images = []
        try:
            for img in project.images.filter(is_active=True).order_by('order'):
                try:
                    image_url = img.image.url if img.image else None
                    if image_url:
                        additional_images.append({
                            'id': img.id,
                            'url': image_url,
                            'title_ar': img.title_ar or '',
                            'title_en': img.title_en or '',
                            'description_ar': img.description_ar or '',
                            'order': img.order
                        })
                except Exception as img_error:
                    logger.warning(f"خطأ في جلب الصورة {img.id}: {img_error}")
                    continue
        except Exception as e:
            logger.warning(f"خطأ في جلب الصور الإضافية: {e}")

        # ========================================
        # ✅ جلب الفيديوهات مع معالجة الأخطاء
        # ========================================
        videos = []
        try:
            for video in project.videos.filter(is_active=True).order_by('order'):
                try:
                    thumbnail_url = None
                    if video.thumbnail:
                        try:
                            thumbnail_url = video.thumbnail.url
                        except:
                            pass

                    videos.append({
                        'id': video.id,
                        'title_ar': video.title_ar,
                        'title_en': video.title_en or '',
                        'youtube_url': video.youtube_url or '',
                        'embed_url': video.get_embed_url() or '',
                        'thumbnail': thumbnail_url,
                        'description_ar': video.description_ar or '',
                        'description_en': video.description_en or '',
                        'duration': video.duration or 0,
                        'order': video.order
                    })
                except Exception as video_error:
                    logger.warning(f"خطأ في جلب الفيديو {video.id}: {video_error}")
                    continue
        except Exception as e:
            logger.warning(f"خطأ في جلب الفيديوهات: {e}")

        # ========================================
        # ✅ جلب المستندات
        # ========================================
        documents = []
        try:
            for doc in project.documents.filter(is_active=True).order_by('-created_at'):
                try:
                    file_url = None
                    if doc.file:
                        try:
                            file_url = doc.file.url
                        except:
                            pass

                    if file_url:
                        documents.append({
                            'id': doc.id,
                            'title_ar': doc.title_ar,
                            'title_en': doc.title_en or '',
                            'document_type': doc.document_type,
                            'document_type_display': doc.get_document_type_display(),
                            'file_url': file_url,
                            'file_extension': doc.get_file_extension(),
                            'file_size': doc.get_formatted_file_size(),
                            'download_count': doc.download_count,
                            'is_public': doc.is_public,
                        })
                except Exception as doc_error:
                    logger.warning(f"خطأ في جلب المستند {doc.id}: {doc_error}")
                    continue
        except Exception as e:
            logger.warning(f"خطأ في جلب المستندات: {e}")

        # ========================================
        # ✅ معالجة الصورة الرئيسية
        # ========================================
        main_image_url = None
        if project.main_image:
            try:
                main_image_url = project.main_image.url
            except Exception as e:
                logger.warning(f"خطأ في جلب الصورة الرئيسية: {e}")

        # ========================================
        # ✅ حساب النسب المئوية
        # ========================================
        try:
            progress_percentage = project.get_progress_percentage()
        except:
            progress_percentage = 0.0

        try:
            beneficiaries_percentage = project.get_beneficiaries_percentage()
        except:
            beneficiaries_percentage = 0.0

        try:
            overall_percentage = project.get_overall_percentage()
        except:
            overall_percentage = 0.0

        # ========================================
        # ✅ معالجة التواريخ
        # ========================================
        start_date_str = None
        end_date_str = None

        if project.start_date:
            try:
                start_date_str = project.start_date.strftime('%Y-%m-%d')
            except:
                pass

        if project.end_date:
            try:
                end_date_str = project.end_date.strftime('%Y-%m-%d')
            except:
                pass

        # ========================================
        # ✅ بناء البيانات النهائية
        # ========================================
        data = {
            # معلومات أساسية
            'id': project.id,
            'title_ar': project.title_ar,
            'title_en': project.title_en or '',
            'slug': project.slug,

            # الفئة
            'category_id': project.category.id,
            'category_name': project.category.name_ar,
            'category_name_en': project.category.name_en or '',
            'category_color': project.category.color,
            'category_icon': project.category.icon,

            # الملخص والوصف
            'summary_ar': project.summary_ar,
            'summary_en': project.summary_en or '',
            'description_ar': project.description_ar or '',
            'description_en': project.description_en or '',

            # الحالة والأولوية
            'status': project.status,
            'status_display': project.get_status_display(),
            'status_color': status_colors.get(project.status, '#6c757d'),
            'status_icon': status_icons.get(project.status, 'fas fa-project-diagram'),

            'priority': project.priority,
            'priority_display': project.get_priority_display(),
            'priority_color': priority_colors.get(project.priority, '#6c757d'),
            'priority_icon': priority_icons.get(project.priority, 'fas fa-star'),

            # التواريخ
            'start_date': start_date_str,
            'end_date': end_date_str,
            'created_at': project.created_at.strftime('%Y-%m-%d %H:%M:%S') if project.created_at else None,
            'updated_at': project.updated_at.strftime('%Y-%m-%d %H:%M:%S') if project.updated_at else None,

            # المبالغ المالية
            'target_amount': float(project.target_amount) if project.target_amount else 0,
            'raised_amount': float(project.raised_amount) if project.raised_amount else 0,
            'remaining_amount': float(project.remaining_amount) if hasattr(project, 'remaining_amount') else 0,
            'progress_percentage': progress_percentage,

            # المستفيدون
            'beneficiaries_count': project.beneficiaries_count,
            'target_beneficiaries': project.target_beneficiaries,
            'remaining_beneficiaries': project.remaining_beneficiaries if hasattr(project,
                                                                                  'remaining_beneficiaries') else 0,
            'beneficiaries_percentage': beneficiaries_percentage,

            # النسبة الإجمالية
            'overall_percentage': overall_percentage,

            # الموقع
            'location_ar': project.location_ar or '',
            'location_en': project.location_en or '',

            # الكلمات المفتاحية
            'keywords_ar': project.keywords_ar or '',
            'keywords_en': project.keywords_en or '',

            # SEO
            'meta_description_ar': project.meta_description_ar or '',
            'meta_description_en': project.meta_description_en or '',

            # إعدادات العرض
            'is_featured': project.is_featured,
            'is_active': project.is_active,
            'allow_comments': project.allow_comments,

            # الإحصائيات
            'views_count': project.views_count,
            'likes_count': project.likes_count,
            'shares_count': project.shares_count,

            # الصور والفيديوهات والمستندات
            'main_image_url': main_image_url,
            'additional_images': additional_images,
            'videos': videos,
            'documents': documents,

            # معلومات إضافية
            'images_count': len(additional_images),
            'videos_count': len(videos),
            'documents_count': len(documents),
        }

        logger.info(f"✅ تم جلب بيانات المشروع بنجاح: {project.title_ar}")
        return JsonResponse({'success': True, 'data': data})

    except Project.DoesNotExist:
        logger.warning(f"⚠️ المشروع {item_id} غير موجود")
        return JsonResponse({
            'success': False,
            'error': 'المشروع غير موجود'
        }, status=404)

    except Exception as e:
        logger.error(f"❌ خطأ في عرض المشروع {item_id}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ أثناء جلب بيانات المشروع'
        }, status=500)


@require_POST
def delete_project_ajax(request, item_id):
    """حذف مشروع"""
    try:
        project = get_object_or_404(Project, id=item_id)
        title = project.title_ar

        # حذف جميع الصور المرتبطة
        for img in project.images.all():
            if img.image and os.path.isfile(img.image.path):
                try:
                    os.remove(img.image.path)
                except Exception as e:
                    logger.warning(f"فشل حذف صورة: {e}")

        # حذف الصورة الرئيسية
        if project.main_image and os.path.isfile(project.main_image.path):
            try:
                os.remove(project.main_image.path)
            except Exception as e:
                logger.warning(f"فشل حذف الصورة الرئيسية: {e}")

        # حذف المشروع
        project.delete()

        logger.info(f"تم حذف المشروع: {title}")
        return JsonResponse({'success': True, 'message': 'تم حذف المشروع بنجاح'})

    except Exception as e:
        logger.error(f"خطأ في حذف المشروع: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'حدث خطأ أثناء حذف المشروع'}, status=500)


@require_http_methods(["GET", "POST"])
def edit_project_ajax(request, item_id):
    """تعديل مشروع"""
    try:
        project = get_object_or_404(Project, id=item_id)

        if request.method == 'GET':
            # ✅ جلب رابط الفيديو
            video = project.videos.first()

            # ✅ جلب الصور الإضافية
            additional_images = []
            for img in project.images.all().order_by('order'):
                try:
                    additional_images.append({
                        'id': img.id,
                        'url': img.image.url if img.image else '',
                        'order': img.order,
                    })
                except Exception as e:
                    logger.warning(f"خطأ في جلب صورة إضافية: {e}")
                    continue

            # ✅ التأكد من وجود الصورة الرئيسية
            main_image_url = None
            if project.main_image:
                try:
                    main_image_url = project.main_image.url
                except Exception as e:
                    logger.warning(f"خطأ في جلب الصورة الرئيسية: {e}")

            data = {
                'id': project.id,
                'title_ar': project.title_ar,
                'title_en': project.title_en or '',
                'slug': project.slug,
                'category_id': project.category.id,
                'summary_ar': project.summary_ar,
                'summary_en': project.summary_en or '',
                'description_ar': project.description_ar or '',
                'description_en': project.description_en or '',
                'status': project.status,
                'priority': project.priority,
                'start_date': project.start_date.strftime('%Y-%m-%d') if project.start_date else None,
                'end_date': project.end_date.strftime('%Y-%m-%d') if project.end_date else None,
                'target_amount': str(project.target_amount),
                'raised_amount': str(project.raised_amount),
                'beneficiaries_count': project.beneficiaries_count,
                'target_beneficiaries': project.target_beneficiaries,
                'location_ar': project.location_ar or '',
                'location_en': project.location_en or '',
                'keywords_ar': project.keywords_ar or '',
                'keywords_en': project.keywords_en or '',
                'is_featured': project.is_featured,
                'is_active': project.is_active,
                'allow_comments': project.allow_comments,
                'main_image_url': main_image_url,
                'additional_images': additional_images,
                'video_url': video.youtube_url if video else '',
            }
            return JsonResponse({'success': True, 'data': data})

        else:  # POST
            # ========================================
            # ✅ معالجة حذف الصورة الرئيسية
            # ========================================
            delete_main_image = request.POST.get('delete_main_image', 'false')
            if delete_main_image == 'true' and project.main_image:
                # حذف الملف من الخادم
                if os.path.isfile(project.main_image.path):
                    try:
                        os.remove(project.main_image.path)
                        logger.info(f"تم حذف الصورة الرئيسية للمشروع: {project.title_ar}")
                    except Exception as e:
                        logger.warning(f"فشل حذف الصورة الرئيسية: {e}")

                project.main_image = None

            # ========================================
            # ✅ معالجة حذف الصور الإضافية
            # ========================================
            deleted_images = request.POST.get('deleted_images', '')
            if deleted_images:
                deleted_ids = [int(id.strip()) for id in deleted_images.split(',') if id.strip()]

                for img_id in deleted_ids:
                    try:
                        img = ProjectImage.objects.get(id=img_id, project=project)

                        # حذف الملف من الخادم
                        if img.image and os.path.isfile(img.image.path):
                            try:
                                os.remove(img.image.path)
                            except Exception as e:
                                logger.warning(f"فشل حذف الصورة {img_id}: {e}")

                        # حذف السجل من قاعدة البيانات
                        img.delete()
                        logger.info(f"تم حذف الصورة {img_id} من المشروع: {project.title_ar}")

                    except ProjectImage.DoesNotExist:
                        logger.warning(f"الصورة {img_id} غير موجودة")

            # ========================================
            # تحديث بيانات المشروع
            # ========================================
            project.title_ar = request.POST.get('title_ar', '').strip()
            project.title_en = request.POST.get('title_en', '').strip()
            project.slug = request.POST.get('slug', '').strip()

            # التأكد من وجود الفئة
            category_id = request.POST.get('category')
            if category_id:
                project.category_id = category_id

            project.summary_ar = request.POST.get('summary_ar', '').strip()
            project.summary_en = request.POST.get('summary_en', '').strip()
            project.description_ar = request.POST.get('description_ar', '').strip()
            project.description_en = request.POST.get('description_en', '').strip()
            project.status = request.POST.get('status', 'planning')
            project.priority = request.POST.get('priority', 'medium')

            # التواريخ
            start_date_str = request.POST.get('start_date', '').strip()
            if start_date_str:
                try:
                    project.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                except ValueError:
                    logger.warning(f"تنسيق تاريخ البداية غير صحيح: {start_date_str}")

            end_date_str = request.POST.get('end_date', '').strip()
            if end_date_str:
                try:
                    project.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                except ValueError:
                    logger.warning(f"تنسيق تاريخ النهاية غير صحيح: {end_date_str}")

            # المبالغ
            try:
                target_amount = request.POST.get('target_amount', '0')
                project.target_amount = Decimal(target_amount) if target_amount else Decimal('0')

                raised_amount = request.POST.get('raised_amount', '0')
                project.raised_amount = Decimal(raised_amount) if raised_amount else Decimal('0')
            except Exception as e:
                logger.warning(f"خطأ في تحويل المبالغ: {e}")

            # المستفيدون
            try:
                target_beneficiaries = request.POST.get('target_beneficiaries', '0')
                project.target_beneficiaries = int(target_beneficiaries) if target_beneficiaries else 0

                beneficiaries_count = request.POST.get('beneficiaries_count', '0')
                project.beneficiaries_count = int(beneficiaries_count) if beneficiaries_count else 0
            except Exception as e:
                logger.warning(f"خطأ في تحويل عدد المستفيدين: {e}")

            # الموقع
            project.location_ar = request.POST.get('location_ar', '').strip()
            project.location_en = request.POST.get('location_en', '').strip()

            # الكلمات المفتاحية
            project.keywords_ar = request.POST.get('keywords_ar', '').strip()
            project.keywords_en = request.POST.get('keywords_en', '').strip()

            # الإعدادات
            project.is_featured = 'is_featured' in request.POST
            project.is_active = 'is_active' in request.POST
            project.allow_comments = 'allow_comments' in request.POST

            # ========================================
            # ✅ رفع صورة رئيسية جديدة
            # ========================================
            if 'main_image' in request.FILES:
                # حذف الصورة القديمة إذا كانت موجودة
                if project.main_image:
                    try:
                        if os.path.isfile(project.main_image.path):
                            os.remove(project.main_image.path)
                    except Exception as e:
                        logger.warning(f"فشل حذف الصورة القديمة: {e}")

                project.main_image = request.FILES['main_image']
                logger.info(f"تم رفع صورة رئيسية جديدة للمشروع: {project.title_ar}")

            # ========================================
            # ✅ رفع صور إضافية جديدة
            # ========================================
            additional_images = request.FILES.getlist('additional_images')
            if additional_images:
                # احصل على آخر ترتيب للصور الحالية
                last_order = ProjectImage.objects.filter(project=project).aggregate(
                    max_order=models.Max('order')
                )['max_order'] or 0

                for idx, image_file in enumerate(additional_images, start=1):
                    try:
                        ProjectImage.objects.create(
                            project=project,
                            image=image_file,
                            order=last_order + idx,
                            is_active=True
                        )
                        logger.info(f"تم رفع صورة إضافية جديدة للمشروع: {project.title_ar}")
                    except Exception as e:
                        logger.error(f"فشل رفع صورة إضافية: {e}")

            # ========================================
            # ✅ معالجة رابط الفيديو
            # ========================================
            video_url = request.POST.get('video_url', '').strip()
            if video_url:
                # تحديث الفيديو الموجود أو إنشاء جديد
                video = project.videos.first()
                if video:
                    video.youtube_url = video_url
                    video.save()
                    logger.info(f"تم تحديث رابط الفيديو للمشروع: {project.title_ar}")
                else:
                    try:
                        ProjectVideo.objects.create(
                            project=project,
                            title_ar=f'فيديو {project.title_ar}',
                            title_en=f'Video {project.title_en}' if project.title_en else '',
                            youtube_url=video_url,
                            order=1,
                            is_active=True
                        )
                        logger.info(f"تم إضافة فيديو جديد للمشروع: {project.title_ar}")
                    except Exception as e:
                        logger.error(f"فشل إضافة الفيديو: {e}")
            else:
                # إذا كان الحقل فارغاً، احذف الفيديو إذا كان موجوداً
                video = project.videos.first()
                if video:
                    video.delete()
                    logger.info(f"تم حذف الفيديو من المشروع: {project.title_ar}")

            # حفظ التعديلات
            project.save()

            logger.info(f"تم تحديث المشروع: {project.title_ar}")

            return JsonResponse({
                'success': True,
                'message': 'تم تحديث المشروع بنجاح'
            })

    except Project.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'المشروع غير موجود'}, status=404)
    except Exception as e:
        logger.error(f"خطأ في تعديل المشروع: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ أثناء تحديث المشروع'
        }, status=500)


import re
from django.contrib.auth.hashers import make_password
from django.core.validators import validate_email
from django.core.exceptions import ValidationError




def validate_username(username, user_id=None):
    """التحقق من اسم المستخدم"""
    errors = []

    if len(username) < 8:
        errors.append('اسم المستخدم يجب أن يكون 8 أحرف على الأقل')

    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        errors.append('اسم المستخدم يجب أن يحتوي على أحرف إنجليزية وأرقام فقط')

    query = User.objects.filter(username=username)
    if user_id:
        query = query.exclude(id=user_id)
    if query.exists():
        errors.append('اسم المستخدم موجود مسبقاً')

    return errors


def validate_password_strength(password):
    """التحقق من قوة كلمة المرور"""
    errors = []

    if len(password) < 8:
        errors.append('كلمة المرور يجب أن تكون 8 أحرف على الأقل')

    if not re.search(r'[A-Z]', password):
        errors.append('كلمة المرور يجب أن تحتوي على حرف كبير واحد على الأقل')

    if not re.search(r'[a-z]', password):
        errors.append('كلمة المرور يجب أن تحتوي على حرف صغير واحد على الأقل')

    if not re.search(r'[0-9]', password):
        errors.append('كلمة المرور يجب أن تحتوي على رقم واحد على الأقل')

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append('كلمة المرور يجب أن تحتوي على رمز خاص واحد على الأقل')

    return errors


def validate_arabic_name(name):
    """التحقق من الاسم العربي"""
    errors = []

    if not name or len(name.strip()) == 0:
        errors.append('الاسم مطلوب')
        return errors

    if not re.match(r'^[\u0621-\u064A\s]+$', name):
        errors.append('الاسم يجب أن يحتوي على أحرف عربية فقط')

    return errors


def validate_saudi_phone(phone, user_id=None):
    """التحقق من رقم الجوال السعودي"""
    errors = []

    if not phone:
        return errors  # رقم الجوال اختياري

    phone = phone.strip()

    if not re.match(r'^(056|059)\d{7}$', phone):
        errors.append('رقم الجوال يجب أن يبدأ بـ 056 أو 059 ويتكون من 10 أرقام')

    query = UserProfile.objects.filter(phone=phone)
    if user_id:
        query = query.exclude(user_id=user_id)
    if query.exists():
        errors.append('رقم الجوال مستخدم مسبقاً')

    return errors


def validate_email_unique(email, user_id=None):
    """التحقق من البريد الإلكتروني"""
    errors = []

    try:
        validate_email(email)
    except ValidationError:
        errors.append('البريد الإلكتروني غير صحيح')
        return errors

    query = User.objects.filter(email=email)
    if user_id:
        query = query.exclude(id=user_id)
    if query.exists():
        errors.append('البريد الإلكتروني مستخدم مسبقاً')

    return errors


@require_http_methods(["GET", "POST"])
@editor_required
def edit_partner_ajax(request, item_id):
    """تعديل شريك"""
    try:
        partner = get_object_or_404(Partner, id=item_id)

        if request.method == 'GET':
            data = {
                'id': partner.id,
                'name_ar': partner.name_ar,
                'name_en': partner.name_en,
                'description_ar': partner.description_ar,
                'description_en': partner.description_en,
                'partnership_date': partner.partnership_date.strftime('%Y-%m-%d'),
                'projects_count': partner.projects_count,
                'website': partner.website,
                'email': partner.email,
                'phone': partner.phone,
                'order': partner.order,
                'is_active': partner.is_active,
            }
            return JsonResponse({'success': True, 'data': data})

        else:  # POST
            form = PartnerForm(request.POST, request.FILES, instance=partner)
            if form.is_valid():
                form.save()
                log_update_activity(request.user, partner.name_ar, 'شريك', partner, request)
                return JsonResponse({'success': True, 'message': 'تم التحديث بنجاح'})
            return JsonResponse({'success': False, 'error': 'حدث خطأ في البيانات'}, status=400)

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@editor_required
def delete_partner_ajax(request, item_id):
    """حذف شريك"""
    try:
        partner = get_object_or_404(Partner, id=item_id)
        name = partner.name_ar
        log_delete_activity(request.user, name, 'شريك', request)
        partner.delete()
        return JsonResponse({'success': True, 'message': 'تم الحذف بنجاح'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET"])
@dashboard_required
def view_partner_ajax(request, item_id):
    """عرض تفاصيل شريك"""
    try:
        partner = get_object_or_404(Partner, id=item_id)

        data = {
            'id': partner.id,
            'name_ar': partner.name_ar,
            'name_en': partner.name_en,
            'logo_url': partner.logo.url if partner.logo else None,
            'description_ar': partner.description_ar,
            'description_en': partner.description_en,
            'partnership_date': partner.partnership_date.strftime('%Y/%m/%d'),
            'projects_count': partner.projects_count,
            'website': partner.website,
            'email': partner.email,
            'phone': partner.phone,
            'order': partner.order,
            'is_active': partner.is_active,
        }
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET"])
@dashboard_required
def view_goal_ajax(request, item_id):
    """عرض تفاصيل هدف"""
    try:
        goal = get_object_or_404(Goal, id=item_id)

        data = {
            'id': goal.id,
            'title_ar': goal.title_ar,
            'title_en': goal.title_en,
            'description_ar': goal.description_ar,
            'description_en': goal.description_en,
            'icon': goal.icon,
            'order': goal.order,
            'is_active': goal.is_active,
        }
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)






@dashboard_required
def activity_logs_view(request):
    """صفحة سجل نشاط المستخدمين"""
    try:
        # الفلاتر
        search_query = request.GET.get('search', '')
        action_filter = request.GET.get('action', '')
        level_filter = request.GET.get('level', '')
        user_filter = request.GET.get('user', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')

        # استرجاع السجلات
        logs = ActivityLog.objects.select_related('user', 'content_type').all().order_by('-timestamp')

        # تطبيق الفلاتر
        if search_query:
            logs = logs.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(username__icontains=search_query)
            )

        if action_filter:
            logs = logs.filter(action=action_filter)

        if level_filter:
            logs = logs.filter(level=level_filter)

        if user_filter:
            logs = logs.filter(user_id=user_filter)

        if date_from:
            logs = logs.filter(timestamp__gte=date_from)

        if date_to:
            from datetime import datetime, timedelta
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            logs = logs.filter(timestamp__lt=date_to_obj)

        # الترقيم
        paginator = Paginator(logs, 30)
        logs_page = paginator.get_page(request.GET.get('page'))

        # إحصائيات
        stats = {
            'total': ActivityLog.objects.count(),
            'today': ActivityLog.objects.filter(timestamp__date=timezone.now().date()).count(),
            'actions': ActivityLog.objects.values('action').annotate(count=Count('id')),
            'levels': ActivityLog.objects.values('level').annotate(count=Count('id')),
        }

        # قائمة المستخدمين للفلتر
        active_users = User.objects.filter(
            id__in=ActivityLog.objects.values_list('user_id', flat=True).distinct()
        ).order_by('username')

        context = {
            'logs_page': logs_page,
            'stats': stats,
            'active_users': active_users,
            'search_query': search_query,
            'action_filter': action_filter,
            'level_filter': level_filter,
            'user_filter': user_filter,
            'date_from': date_from,
            'date_to': date_to,
            'page_title': 'نشاط المستخدمين',
        }

        return render(request, 'dashboard/activity_logs.html', context)

    except Exception as e:
        logger.error(f"خطأ في صفحة نشاط المستخدمين: {e}")
        messages.error(request, 'حدث خطأ في تحميل السجل')
        return redirect('dashboard:home')


@require_POST
@admin_required
def reset_settings_api(request):
    """إعادة الإعدادات إلى القيم الافتراضية"""
    try:
        settings_obj = SiteSetting.objects.first()
        if not settings_obj:
            settings_obj = SiteSetting.objects.create()

        # إعادة القيم الافتراضية
        settings_obj.site_name_ar = 'جمعية نسائم فلسطين'
        settings_obj.site_name_en = 'Nasaeem Palestine'
        settings_obj.site_description = ''
        settings_obj.site_email = 'info@nasaeem-palestine.org'
        settings_obj.site_phone = ''

        # وضع الصيانة
        settings_obj.maintenance_mode = False
        settings_obj.maintenance_message_ar = 'الموقع تحت الصيانة، سنعود قريباً'
        settings_obj.maintenance_message_en = 'Site under maintenance, we will be back soon'

        # الأمان
        settings_obj.enable_two_factor = False
        settings_obj.session_timeout = 30
        settings_obj.max_login_attempts = 5
        settings_obj.force_https = False
        settings_obj.enable_ip_blocking = False

        # الأداء
        settings_obj.cache_timeout = 3600
        settings_obj.enable_compression = True
        settings_obj.enable_lazy_loading = True
        settings_obj.enable_minification = False

        settings_obj.save()

        # تسجيل النشاط
        ActivityLog.log_activity(
            user=request.user,
            action='update',
            title='إعادة ضبط الإعدادات',
            description='تم إعادة جميع الإعدادات إلى القيم الافتراضية',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            session_key=request.session.session_key
        )

        return JsonResponse({
            'success': True,
            'message': 'تم إعادة الإعدادات إلى الحالة الافتراضية بنجاح'
        })

    except Exception as e:
        logger.error(f"خطأ في إعادة ضبط الإعدادات: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
# ========================================
# النقاط والرسالة
# ========================================
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json



@require_POST
def save_value(request):
    try:
        data = json.loads(request.body)
        value_id = data.get('id')
        content_ar = data.get('ar')
        content_en = data.get('en')

        if value_id == 'new':
            # إنشاء قيمة جديدة
            vision_page = VisionPage.objects.first()
            value = ValuePoint.objects.create(
                vision_page=vision_page,
                content_ar=content_ar,
                content_en=content_en
            )
            return JsonResponse({'ok': True, 'id': value.id})
        else:
            # تحديث قيمة موجودة
            value = ValuePoint.objects.get(id=value_id)
            value.content_ar = content_ar
            value.content_en = content_en
            value.save()
            return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


@require_POST
def delete_value(request):
    try:
        data = json.loads(request.body)
        value_id = data.get('id')
        ValuePoint.objects.filter(id=value_id).delete()
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})



# ========================================
# معالجات الأخطاء
# ========================================


def get_used_icons(request):
    icons = Statistic.objects.exclude(icon__isnull=True).exclude(icon__exact='').values_list('icon', flat=True)
    return JsonResponse({'used_icons': list(icons)})


def custom_404(request, exception):
    """معالج خطأ 404"""
    return render(request, 'main/404.html', status=404)


def custom_500(request):
    """معالج خطأ 500"""
    return render(request, 'main/500.html', status=500)
