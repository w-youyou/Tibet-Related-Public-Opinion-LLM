# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chunker_api', '0005_chatmessage_rag_v1_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='suggested_next_questions',
            field=models.JSONField(blank=True, null=True, verbose_name='引导式追问'),
        ),
    ]
