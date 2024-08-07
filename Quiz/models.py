from django.db import models
from django.utils import timezone

from Question.models import QuestionGenerator

from Course.models import StudentLessonProgress
from Question.models import StudentAnswer

# Create your models here.
class Quiz(QuestionGenerator):
    id = models.AutoField(primary_key=True)
    lesson = models.ForeignKey('Course.Lesson', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    questions = models.ManyToManyField('Question.Question')
    passing_score = models.FloatField(default=0.75)

    def __str__(self):
        return self.title

    def generate_questions(self, num_easy, num_medium, num_hard):
        filter_by = {'lesson': self.lesson}
        return super().generate_questions(num_easy, num_medium, num_hard, filter_by)


class StudentQuizAttempt(models.Model):
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey('User.Student', on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.IntegerField(null=True, blank=True)
    total_questions = models.IntegerField()
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    passed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student} - {self.quiz} - {self.score}"
    
    def mark_lesson_completed(self):
        if self.passed:
            StudentLessonProgress.objects.update_or_create(
                student=self.student,
                lesson=self.quiz.lesson,
                defaults={'is_completed': True}
            )
    def calculate_score(self):
        correct_answers = StudentAnswer.objects.filter(quiz_attempt=self, is_correct=True).count()
        return (correct_answers / self.total_questions) * 100
