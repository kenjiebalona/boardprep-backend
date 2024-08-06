from django.db import models
from django.utils import timezone
from Question.models import Question, QuestionGenerator


# Create your models here.
class Challenge(QuestionGenerator):
    challengeID = models.BigAutoField(primary_key=True)
    date = models.DateField(default=timezone.now, unique=True)

    def __str__(self):
        return f"Daily Challenge for {self.date}"

    def generate_questions(self, num_easy, num_medium, num_hard):
        return super().generate_questions(num_easy, num_medium, num_hard)


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
