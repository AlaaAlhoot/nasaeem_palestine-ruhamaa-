# admin_panel/management/commands/send_newsletter.py

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'إرسال النشرة البريدية التلقائية (daily/weekly/monthly)'

    def add_arguments(self, parser):
        parser.add_argument('type', choices=['daily', 'weekly', 'monthly'])

    def handle(self, *args, **options):
        from admin_panel.views.newsletter import send_auto_newsletter

        send_type = options['type']
        now       = timezone.now()

        # تحقق من الوقت المناسب
        if send_type == 'daily':
            # كل يوم 4 عصراً
            if now.hour != 16:
                self.stdout.write(f'[daily] ليس وقت الإرسال (الآن: {now.hour}:00 — المطلوب: 16:00)')
                return

        elif send_type == 'weekly':
            # السبت 12 ليلاً
            if now.weekday() != 5 or now.hour != 0:
                self.stdout.write(f'[weekly] ليس وقت الإرسال')
                return

        elif send_type == 'monthly':
            # أول يوم بالشهر 12 ليلاً
            if now.day != 1 or now.hour != 0:
                self.stdout.write(f'[monthly] ليس وقت الإرسال')
                return

        self.stdout.write(f'بدء إرسال النشرة [{send_type}]...')
        sent, failed = send_auto_newsletter(send_type)
        self.stdout.write(
            self.style.SUCCESS(f'✅ تم: {sent} ناجح، {failed} فاشل')
        )
