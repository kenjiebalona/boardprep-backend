# Generated by Django 4.2.4 on 2024-08-05 08:11

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('Course', '0001_initial'),
        ('Class', '0002_initial'),
        ('User', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Exam',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('classID', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='Class.class')),
                ('course', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='Course.course')),
            ],
        ),
        migrations.CreateModel(
            name='StudentExamAttempt',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('score', models.IntegerField()),
                ('total_questions', models.IntegerField()),
                ('start_time', models.DateTimeField(default=django.utils.timezone.now)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('exam', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='Exam.exam')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='User.student')),
            ],
        ),
    ]
