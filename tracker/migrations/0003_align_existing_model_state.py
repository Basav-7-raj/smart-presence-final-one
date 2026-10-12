from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("tracker", "0002_final_features"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="systemevent",
            options={"ordering": ["-timestamp"]},
        ),
        migrations.AlterField(
            model_name="presencerecord",
            name="person",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="presence_records",
                to="tracker.personprofile",
            ),
        ),
    ]
