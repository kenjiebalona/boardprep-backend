from django.db import models
from django.utils import timezone


# Create your models here.
class Exam(models.Model):
    id = models.AutoField(primary_key=True)
    classID = models.ForeignKey('Class.Class', on_delete=models.CASCADE, blank=True, null=True)
    course = models.ForeignKey('Course.Course', on_delete=models.CASCADE, blank=True, null=True)
    title = models.CharField(max_length=200)
    questions = models.ManyToManyField('Question.Question')

    def __str__(self):
        return self.title


class StudentExamAttempt(models.Model):
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey('User.Student', on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    score = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    total_questions = models.IntegerField()
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student} - {self.exam} - {self.score}"
