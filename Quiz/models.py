from django.db import models
from django.utils import timezone

from Question.models import QuestionGenerator


# Create your models here.
class Quiz(QuestionGenerator):
    id = models.AutoField(primary_key=True)
    topic = models.ForeignKey('Course.Lesson', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)

    def __str__(self):
        return self.title

    def generate_questions(self, num_easy, num_medium, num_hard):
        filter_by = {'topic': self.topic}
        return super().generate_questions(num_easy, num_medium, num_hard, filter_by)


class StudentQuizAttempt(models.Model):
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey('User.Student', on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.IntegerField(null=True, blank=True)
    total_questions = models.IntegerField()
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student} - {self.quiz} - {self.score}"
