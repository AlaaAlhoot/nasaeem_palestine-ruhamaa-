from django.utils.translation import get_language
import html
from django import template
import re

register = template.Library()


# ==================== Translation Filters ====================

@register.filter
def get_trans(obj, field_name):
    """Get translated field value based on current language"""
    try:
        if not obj:
            return ""
        current_language = get_language()
        if current_language == 'en':
            field_en = f"{field_name}_en"
            value_en = getattr(obj, field_en, None)
            if value_en and str(value_en).strip():
                return value_en
        field_ar = f"{field_name}_ar"
        value_ar = getattr(obj, field_ar, None)
        return value_ar if value_ar else ""
    except Exception:
        return ""


@register.simple_tag
def trans_field(obj, field_name):
    """Simple tag for translation"""
    return get_trans(obj, field_name)


@register.filter
def translate_field(obj, field_name):
    """Filter for translation"""
    return get_trans(obj, field_name)


@register.filter
def translate_field_or(obj, args):
    """Translate field with default value"""
    try:
        parts = args.split(',', 1)
        field_name = parts[0].strip()
        default_value = parts[1].strip() if len(parts) > 1 else "غير متوفر"
        value = get_trans(obj, field_name)
        return value if value else default_value
    except Exception:
        return "غير متوفر"


# ==================== Days & Time Filters ====================

_DAYS_TIME_MAP = {
    'السبت':    {'en': 'Saturday',   'ar': 'السبت'},
    'الأحد':    {'en': 'Sunday',     'ar': 'الأحد'},
    'الاثنين':  {'en': 'Monday',     'ar': 'الاثنين'},
    'الثلاثاء': {'en': 'Tuesday',    'ar': 'الثلاثاء'},
    'الأربعاء': {'en': 'Wednesday',  'ar': 'الأربعاء'},
    'الخميس':   {'en': 'Thursday',   'ar': 'الخميس'},
    'الجمعة':   {'en': 'Friday',     'ar': 'الجمعة'},
    'صباحاً':   {'en': 'AM',         'ar': 'صباحاً'},
    'مساءً':    {'en': 'PM',         'ar': 'مساءً'},
}


@register.filter
def translate_day(value):
    """ترجمة اسم اليوم العربي حسب اللغة الحالية"""
    if not value:
        return value
    lang = (get_language() or 'ar')[:2]
    return _DAYS_TIME_MAP.get(value, {}).get(lang, value)


@register.filter
def translate_time_of_day(value):
    """ترجمة صباحاً / مساءً حسب اللغة الحالية"""
    if not value:
        return value
    lang = (get_language() or 'ar')[:2]
    return _DAYS_TIME_MAP.get(value, {}).get(lang, value)


# ==================== Math Filters ====================

@register.filter
def mul(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def sub(value, arg):
    """Subtract arg from value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0


# ==================== String Filters ====================

@register.filter
def split(value, arg=','):
    """Split string by separator"""
    try:
        if not value:
            return []
        return str(value).split(arg)
    except Exception:
        return []


@register.filter
def trim(value):
    """Trim whitespace from string"""
    try:
        if value is None:
            return ''
        return str(value).strip()
    except Exception:
        return ''


@register.filter
def strip_html(value):
    """Remove HTML tags from string"""
    try:
        if not value:
            return ""
        clean = re.compile('<.*?>')
        text = re.sub(clean, '', str(value))
        return ' '.join(text.split())
    except Exception:
        return value


@register.filter
def smart_truncate(value, length=100):
    """Smart truncate with word boundary"""
    try:
        if not value:
            return ""
        value = str(value).strip()
        length = int(length)
        if len(value) <= length:
            return value
        truncated = value[:length].rsplit(' ', 1)[0]
        return f"{truncated}..."
    except Exception:
        return value


# ==================== Number Filters ====================

@register.filter
def format_number(value):
    """Format number with thousand separators"""
    try:
        number = int(value)
        return "{:,}".format(number)
    except (ValueError, TypeError):
        return value


# ==================== Safety Filters ====================

@register.filter
def safe_value(value):
    """Safe display of value with HTML escaping"""
    try:
        if value is None:
            return "غير متوفر"
        value_str = str(value).strip()
        if value_str == "" or value_str.lower() in ["none", "null", "undefined"]:
            return "غير متوفر"
        clean_value = html.escape(value_str)
        if len(clean_value) > 200:
            clean_value = clean_value[:197] + "..."
        return clean_value
    except Exception:
        return "غير متوفر"


@register.filter
def is_empty(value):
    """Check if value is empty"""
    try:
        if value is None:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        if isinstance(value, (list, dict)) and len(value) == 0:
            return True
        return False
    except Exception:
        return True


@register.filter
def safe_count(value):
    """Safe count of objects"""
    try:
        if hasattr(value, 'count'):
            return value.count()
        if hasattr(value, '__len__'):
            return len(value)
        return 0
    except Exception:
        return 0


# ==================== YouTube Filter ====================

@register.filter
def extract_youtube_id(url):
    """Extract YouTube video ID from various YouTube URL formats"""
    if not url:
        return ''

    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return ''