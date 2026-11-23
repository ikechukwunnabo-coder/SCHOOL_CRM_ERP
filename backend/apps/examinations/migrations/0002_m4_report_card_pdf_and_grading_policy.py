from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid
import apps.core.storage


class Migration(migrations.Migration):

    dependencies = [
        ('app_examinations', '0001_initial'),
        ('institutions', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='reportcard',
            name='content_type',
            field=models.CharField(default='application/pdf', max_length=150),
        ),
        migrations.AddField(
            model_name='reportcard',
            name='document_snapshot',
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name='reportcard',
            name='file',
            field=models.FileField(blank=True, max_length=500, storage=apps.core.storage.private_document_storage, upload_to='report_cards/%Y/%m/'),
        ),
        migrations.AddField(
            model_name='reportcard',
            name='file_ref',
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name='reportcard',
            name='pdf_sha256',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='reportcard',
            name='size_bytes',
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.CreateModel(
            name='GradingPolicy',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('code', models.CharField(max_length=30)),
                ('effective_from', models.DateField()),
                ('effective_to', models.DateField(blank=True, null=True)),
                ('result_completeness_rules', models.JSONField(default=dict)),
                ('report_card_settings', models.JSONField(default=dict)),
                ('is_active', models.BooleanField(default=True)),
                ('campus', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='grading_policies', to='institutions.campus')),
                ('grading_scale', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='grading_policies', to='app_examinations.gradingscale')),
                ('institution', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='grading_policies', to='institutions.institution')),
            ],
            options={
                'ordering': ['institution__code', '-effective_from', 'code'],
            },
        ),
        migrations.AddConstraint(
            model_name='gradingpolicy',
            constraint=models.UniqueConstraint(fields=('institution', 'code'), name='uq_grading_policy_institution_code'),
        ),
        migrations.AddConstraint(
            model_name='gradingpolicy',
            constraint=models.CheckConstraint(condition=models.Q(('effective_to__isnull', True), ('effective_to__gte', models.F('effective_from')), _connector='OR'), name='ck_grading_policy_effective_dates'),
        ),
    ]
