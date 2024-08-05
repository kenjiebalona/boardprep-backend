# Generated by Django 4.2.4 on 2024-08-05 08:11

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('Question', '0001_initial'),
        ('Challenge', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='challenge',
            name='questions',
            field=models.ManyToManyField(to='Question.question'),
        ),
        migrations.AlterUniqueTogether(
            name='studentchallengeattempt',
            unique_together={('daily_challenge', 'student')},
        ),
    ]
