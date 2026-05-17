"""
python compress_images.py
compress_images.py
سكريبت ضغط الصور الموجودة
التشغيل: python manage.py shell < compress_images.py
أو:      python compress_images.py (مع إعداد Django مسبقاً)
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nasaeem_palestine.settings')
django.setup()

from PIL import Image
from django.apps import apps

# ==================== إعدادات ====================
QUALITY   = 75     # جودة الضغط (1-100)
MAX_WIDTH = 1200   # أقصى عرض للصورة بالبكسل
# ================================================


def compress_single(path, quality=QUALITY, max_width=MAX_WIDTH):
    """يضغط صورة واحدة ويحفظها في نفس المكان"""
    try:
        ext = os.path.splitext(path)[1].lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
            return None

        original_size = os.path.getsize(path)

        img = Image.open(path)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        if img.width > max_width:
            ratio = max_width / img.width
            img   = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)

        img.save(path, format='JPEG', quality=quality, optimize=True)

        new_size = os.path.getsize(path)
        return original_size, new_size, original_size - new_size

    except Exception as e:
        print(f'  ⚠️ خطأ: {path} — {e}')
        return None


# ==================== الموديلات ====================
IMAGE_MODELS = [
    ('main',        'SiteSettings',     ['logo', 'favicon', 'default_image']),
    ('main',        'AboutPage',        ['image']),
    ('main',        'VisionPage',       ['vision_image', 'mission_image', 'values_image']),
    ('main',        'BoardMember',      ['photo']),
    ('main',        'HomeSlider',       ['image']),
    ('main',        'Partner',          ['logo']),
    ('projects',    'ProjectCategory',  ['image']),
    ('projects',    'Project',          ['main_image']),
    ('projects',    'ProjectImage',     ['image']),
    ('sponsor',     'SponsorProfile',   ['photo']),
    ('sponsor',     'PaymentReceipt',   ['receipt_image']),
    ('beneficiary', 'OrphanForm',       ['photo']),
    ('beneficiary', 'SpecialNeedsForm', ['photo']),
    ('beneficiary', 'FamilyForm',       ['photo']),
    ('beneficiary', 'FamilyWife',       ['photo']),
]


def run():
    total_saved = 0
    total_files = 0
    skipped     = 0
    errors      = 0

    print('=' * 60)
    print('🗜️  بدء ضغط الصور...')
    print(f'   الجودة: {QUALITY}% | أقصى عرض: {MAX_WIDTH}px')
    print('=' * 60)

    for app_label, model_name, fields in IMAGE_MODELS:
        try:
            model = apps.get_model(app_label, model_name)
            print(f'\n📁 {model_name}:')

            for field_name in fields:
                try:
                    records = model.objects.exclude(
                        **{f'{field_name}__isnull': True}
                    ).exclude(**{f'{field_name}': ''})

                    for obj in records:
                        field = getattr(obj, field_name)
                        if not field:
                            continue
                        try:
                            path = field.path
                            if not os.path.exists(path):
                                skipped += 1
                                continue

                            result = compress_single(path)
                            if result:
                                orig, new, saved = result
                                total_files += 1
                                total_saved += saved
                                if saved > 10 * 1024:  # أكثر من 10KB توفير
                                    print(f'  ✅ {orig//1024}KB → {new//1024}KB'
                                          f' (وفّر {saved//1024}KB) — {os.path.basename(path)}')
                                else:
                                    print(f'  ➖ {orig//1024}KB — {os.path.basename(path)} (لا توفير يُذكر)')
                            else:
                                skipped += 1

                        except Exception as e:
                            errors += 1
                            print(f'  ❌ خطأ في السجل: {e}')

                except Exception as e:
                    print(f'  ❌ خطأ في الحقل {field_name}: {e}')

        except Exception as e:
            print(f'❌ {model_name}: {e}')

    print('\n' + '=' * 60)
    print(f'✅ تم معالجة : {total_files} صورة')
    print(f'💾 إجمالي التوفير: {total_saved // 1024 // 1024}MB'
          f' ({total_saved // 1024}KB)')
    print(f'➖ تخطى       : {skipped}')
    print(f'❌ أخطاء      : {errors}')
    print('=' * 60)


if __name__ == '__main__':
    run()
