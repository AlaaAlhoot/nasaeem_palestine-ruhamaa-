from django import template
from django.utils.translation import get_language

register = template.Library()


@register.filter
def get_trans(obj, field_name):
    """
    جلب الحقل المترجم حسب اللغة الحالية

    الاستخدام:
        {{ project|get_trans:"title" }}
        {{ member|get_trans:"name" }}
        {{ category|get_trans:"description" }}
    """
    current_language = get_language()

    # إذا كانت اللغة إنجليزية، جرب الحقل الإنجليزي
    if current_language == 'en':
        field_en = f"{field_name}_en"
        value_en = getattr(obj, field_en, None)

        # إذا كان الحقل الإنجليزي موجود وغير فارغ
        if value_en:
            return value_en

    # وإلا ارجع الحقل العربي (الافتراضي)
    field_ar = f"{field_name}_ar"
    return getattr(obj, field_ar, '')


@register.simple_tag
def trans_field(obj, field_name):
    """
    نسخة بديلة كـ simple_tag

    الاستخدام:
        {% trans_field project "title" %}
        {% trans_field member "name" %}
    """
    return get_trans(obj, field_name)