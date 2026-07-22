from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='archivebatch',
            name='qr_token',
            field=models.UUIDField(null=True, blank=True, editable=False),
        ),
    ]