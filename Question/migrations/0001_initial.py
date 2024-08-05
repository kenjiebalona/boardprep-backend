# Generated by Django 4.2.4 on 2024-08-05 08:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('Challenge', '0001_initial'),
        ('Exam', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Choice',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('text', models.CharField(max_length=255)),
                ('is_correct', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('text', models.TextField()),
                ('difficulty', models.IntegerField(choices=[(1, 'Easy'), (2, 'Medium'), (3, 'Hard')])),
            ],
        ),
        migrations.CreateModel(
            name='StudentAnswer',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('is_correct', models.BooleanField()),
                ('challenge_attempt', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='Challenge.studentchallengeattempt')),
                ('exam_attempt', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='Exam.studentexamattempt')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='Question.question')),
            ],
        ),
    ]
