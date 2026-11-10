from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("agent", "0001_initial")]
    operations = [
        migrations.AddField(model_name="agentinvocation", name="status", field=models.CharField(max_length=20, default="success")),
        migrations.AddField(model_name="agentinvocation", name="duration_ms", field=models.IntegerField(default=0)),
    ]
