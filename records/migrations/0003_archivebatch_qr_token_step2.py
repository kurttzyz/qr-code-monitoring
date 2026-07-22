import uuid

from django.db import migrations


def populate_qr_tokens(apps, schema_editor):
    ArchiveBatch = apps.get_model('records', 'ArchiveBatch')
    for batch in ArchiveBatch.objects.all():
        batch.qr_token = uuid.uuid4()
        batch.save(update_fields=['qr_token'])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0002_archivebatch_qr_token_step1'),
    ]

    operations = [
        migrations.RunPython(populate_qr_tokens, reverse_noop),
    ]