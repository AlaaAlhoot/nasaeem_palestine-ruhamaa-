from django import template

register = template.Library()

@register.filter
def split(value, arg):
    """تقسيم النص"""
    if value:
        return value.split(arg)
    return []

@register.filter
def trim(value):
    """إزالة المسافات"""
    if value:
        return value.strip()
    return value