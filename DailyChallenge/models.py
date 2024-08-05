from django.db import models
from django.utils import timezone
import random

from Mocktest.models import MockQuestions


# Create your models here.
class DailyChallenge(models.Model):
    challengeID = models.BigAutoField(primary_key=True)
    date = models.DateField(default=timezone.now, unique=True)

    def __str__(self):
        return f"Daily Challenge for {self.date}"

    def generate_challenge(self, num_easy, num_medium, num_hard):
        easy_questions = list(MockQuestions.objects.filter(difficulty__name='Easy').order_by('?')[:num_easy])
        medium_questions = list(MockQuestions.objects.filter(difficulty__name='Medium').order_by('?')[:num_medium])
        hard_questions = list(MockQuestions.objects.filter(difficulty__name='Hard').order_by('?')[:num_hard])

        questions = easy_questions + medium_questions + hard_questions
        random.shuffle(questions)

        for question in questions:
            DailyChallengeQuestion.objects.create(daily_challenge=self, question=question)


class DailyChallengeQuestion(models.Model):
    daily_challenge = models.ForeignKey(DailyChallenge, on_delete=models.CASCADE,
                                        related_name='daily_challenge_questions')
    question = models.ForeignKey(MockQuestions, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.daily_challenge} - {self.question}"


class DailyChallengeLeaderboard(models.Model):
    leaderboardID = models.BigAutoField(primary_key=True)
    daily_challenge = models.ForeignKey(DailyChallenge, on_delete=models.CASCADE, related_name='leaderboard')
    student = models.ForeignKey('User.Student', on_delete=models.CASCADE, related_name='daily_challenge_scores')
    score = models.FloatField()
    completion_time = models.DateTimeField()
    totalQuestions = models.IntegerField()

    class Meta:
        unique_together = ['daily_challenge', 'student']

    def __str__(self):
        return f"{self.student} - {self.daily_challenge} - {self.score}"
