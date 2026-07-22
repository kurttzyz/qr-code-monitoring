"""
python manage.py fix_qr_tokens

Reassigns a fresh, unique qr_token to every ArchiveBatch row. Safe to run
more than once. Put this at: records/management/commands/fix_qr_tokens.py
"""

import uuid

from django.core.management.base import BaseCommand

from records.models import ArchiveBatch


class Command(BaseCommand):
    help = "Reassign a fresh unique qr_token to every ArchiveBatch row."

    def handle(self, *args, **options):
        total = ArchiveBatch.objects.count()
        self.stdout.write(f"Total ArchiveBatch rows: {total}")

        fixed = 0
        for batch in ArchiveBatch.objects.all():
            batch.qr_token = uuid.uuid4()
            batch.save(update_fields=['qr_token'])
            fixed += 1

        self.stdout.write(self.style.SUCCESS(f"Reassigned qr_token on {fixed} rows."))