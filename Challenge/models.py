from django.db import models
from django.utils import timezone
import random
from Question.models import Question


# Create your models here.
class Challenge(models.Model):
    challengeID = models.BigAutoField(primary_key=True)
    date = models.DateField(default=timezone.now, unique=True)
    questions = models.ManyToManyField('Question.Question')

    def __str__(self):
        return f"Daily Challenge for {self.date}"

    def generate_challenge(self, num_easy, num_medium, num_hard):
        easy_questions = list(Question.objects.filter(difficulty=1).order_by('?')[:num_easy])
        medium_questions = list(Question.objects.filter(difficulty=2).order_by('?')[:num_medium])
        hard_questions = list(Question.objects.filter(difficulty=3).order_by('?')[:num_hard])

        questions = easy_questions + medium_questions + hard_questions
        random.shuffle(questions)

        for question in questions:
            self.questions.add(question)
        self.save()


class StudentChallengeAttempt(models.Model):
    leaderboardID = models.BigAutoField(primary_key=True)
    daily_challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='leaderboard')
    student = models.ForeignKey('User.Student', on_delete=models.CASCADE, related_name='daily_challenge_scores')
    score = models.FloatField()
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    total_questions = models.IntegerField()

    class Meta:
        unique_together = ['daily_challenge', 'student']

    def __str__(self):
        return f"{self.student} - {self.daily_challenge} - {self.score}"
