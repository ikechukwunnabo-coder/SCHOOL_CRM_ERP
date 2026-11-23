from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("institutions", "0001_initial"),
        ("students", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AlumniRecord",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("graduation_date", models.DateField()),
                ("graduation_reference", models.CharField(blank=True, max_length=120)),
                (
                    "campus",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="alumni_records",
                        to="institutions.campus",
                    ),
                ),
                (
                    "graduation_event",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="alumni_record",
                        to="students.studentlifecycleevent",
                    ),
                ),
                (
                    "institution",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="alumni_records",
                        to="institutions.institution",
                    ),
                ),
                (
                    "student",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="alumni_record",
                        to="students.student",
                    ),
                ),
            ],
            options={
                "ordering": ["institution__code", "student__admission_number", "-graduation_date"],
            },
        ),
        migrations.AddConstraint(
            model_name="alumnirecord",
            constraint=models.UniqueConstraint(fields=("institution", "student"), name="uq_alumni_record_institution_student"),
        ),
        migrations.AddIndex(
            model_name="alumnirecord",
            index=models.Index(fields=["institution", "campus", "graduation_date"], name="alumni_alum_institu_98201b_idx"),

        ),
    ]
