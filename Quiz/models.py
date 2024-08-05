from django.db import models
from django.utils import timezone


# Create your models here.
class Quiz(models.Model):
    id = models.AutoField(primary_key=True)
    topic = models.OneToOneField('Course.Lesson', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    questions = models.ManyToManyField('Question.Question')

    def __str__(self):
        return self.title


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
