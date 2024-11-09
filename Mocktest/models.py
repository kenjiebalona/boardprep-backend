from django.db import models
from django.utils import timezone
from Question.models import Question, QuestionGenerator


# Create your models here.
class Mocktest(QuestionGenerator):
    preassessmentID = models.BigAutoField(primary_key=True)
    course = models.ForeignKey('Course.Course', on_delete=models.CASCADE)  
    date = models.DateField(default=timezone.now, unique=True)

    def __str__(self):
        return f"Pre Assessment ID: {self.preassessmentID}"

    def generate_questions(self, num_easy, num_medium, num_hard, filter_by=None):
        questions = super().generate_questions(num_easy, num_medium, num_hard, filter_by)
        self.questions.set(questions)
        self.save()
        return questions


class StudentMocktestAttempt(models.Model):
    mocktestID = models.BigAutoField(primary_key=True)
    mocktest = models.ForeignKey(Mocktest, on_delete=models.CASCADE, related_name='mocktest')
    student = models.ForeignKey('User.Student', on_delete=models.CASCADE, related_name='mocktest_scores')
    score = models.FloatField()
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    total_questions = models.IntegerField()

    class Meta:
        unique_together = ['mocktest', 'student']

    def __str__(self):
        return f"{self.student} - {self.mocktest} - {self.score}"

# Create your models here.
