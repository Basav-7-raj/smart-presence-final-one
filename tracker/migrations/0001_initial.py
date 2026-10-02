from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="PersonProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("student_id", models.CharField(max_length=50, unique=True)),
                ("encoding_json", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="PresenceRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("device_source", models.CharField(default="Browser Webcam", max_length=120)),
                ("person", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="tracker.personprofile")),
            ],
            options={"ordering": ["-timestamp"]},
        ),
        migrations.CreateModel(
            name="UnknownEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("best_score", models.FloatField(default=0.0)),
                ("liveness_passed", models.BooleanField(default=False)),
                ("source", models.CharField(default="Browser Webcam", max_length=120)),
            ],
            options={"ordering": ["-timestamp"]},
        ),
    ]
