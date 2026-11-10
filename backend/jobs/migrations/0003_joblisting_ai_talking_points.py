from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("jobs", "0002_jobsearchconfig_joblisting")]
    operations = [
        migrations.AddField(model_name="joblisting", name="ai_talking_points", field=models.TextField(blank=True)),
    ]
