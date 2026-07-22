import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0003_archivebatch_qr_token_step2'),
    ]

    operations = [
        migrations.AlterField(
            model_name='archivebatch',
            name='qr_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]