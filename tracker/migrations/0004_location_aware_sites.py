from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("tracker", "0003_align_existing_model_state"),
    ]

    operations = [
        migrations.CreateModel(
            name="LocationSite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True)),
                ("address", models.CharField(blank=True, max_length=255)),
                ("latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddField(
            model_name="presencerecord",
            name="site",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="presence_records", to="tracker.locationsite"),
        ),
        migrations.AddField(
            model_name="unknownevent",
            name="site",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="unknown_events", to="tracker.locationsite"),
        ),
        migrations.AddField(
            model_name="systemevent",
            name="site",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="system_events", to="tracker.locationsite"),
        ),
    ]
