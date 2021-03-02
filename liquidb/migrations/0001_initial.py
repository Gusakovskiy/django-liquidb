# Generated by Django 3.1.6 on 2021-03-01 19:43

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import liquidb.models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Snapshot',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField(db_index=True, default=liquidb.models._generate_commit_name, unique=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('applied', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='MigrationState',
            fields=[
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, primary_key=True, serialize=False, unique=True)),
                ('migration_id', models.IntegerField(db_index=True)),
                ('app', models.CharField(max_length=255)),
                ('name', models.CharField(max_length=255)),
                ('snapshot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='migrations', to='liquidb.snapshot')),
            ],
        ),
    ]
