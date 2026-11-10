from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0001_initial"),
        ("prospecting", "0001_initial"),
    ]
    operations = [
        migrations.AddField(
            model_name="targetcompany",
            name="source_niche",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="companies_found", to="prospecting.nicheconfig"),
        ),
    ]
