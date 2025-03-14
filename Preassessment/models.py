from django.db import models
from django.utils import timezone
from Question.models import Question, QuestionGenerator


# Create your models here.
class Preassessment(QuestionGenerator):
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


class StudentPreassessmentAttempt(models.Model):
    preassessmentID = models.BigAutoField(primary_key=True)
    preassessment = models.ForeignKey(Preassessment, on_delete=models.CASCADE, related_name='preassessment')
    student = models.ForeignKey('User.Student', on_delete=models.CASCADE, related_name='preassessment_scores')
    score = models.FloatField()
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    total_questions = models.IntegerField()

    class Meta:
        unique_together = ['preassessment', 'student']

    def __str__(self):
        return f"{self.student} - {self.preassessment} - {self.score}"
