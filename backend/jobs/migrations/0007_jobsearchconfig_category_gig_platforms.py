from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("jobs", "0006_joblisting_ai_talking_points")]
    operations = [
        migrations.AlterField(
            model_name="jobsearchconfig",
            name="category",
            field=models.CharField(
                max_length=30,
                default="general",
                choices=[
                    ("general", "General"),
                    ("ai_training", "AI Training (micro1-style)"),
                    ("startup", "Startup / Entry-Level"),
                    ("internship", "Internship"),
                    ("visa_sponsorship", "Visa Sponsorship"),
                    ("gig_platforms", "Gig & Microtask Platforms"),
                ],
            ),
        ),
    ]
