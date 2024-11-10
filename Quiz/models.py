from django.db import models
from django.utils import timezone

from Question.models import QuestionGenerator

from Course.models import StudentLessonProgress
from Question.models import StudentAnswer

# Create your models here.
class Quiz(QuestionGenerator):
    id = models.AutoField(primary_key=True)
    learning_objective = models.ForeignKey('Course.LearningObjective', on_delete=models.CASCADE)
    student = models.ForeignKey('User.Student', on_delete=models.CASCADE)
    class_instance = models.ForeignKey('Class.Class', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    questions = models.ManyToManyField('Question.Question')
    passing_score = models.FloatField(default=0.75)
    is_locked = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    def generate_questions(self, num_easy, num_medium, num_hard):
        filter_by = {'subtopic': self.subtopic}
        return super().generate_questions(num_easy, num_medium, num_hard, filter_by)


class StudentQuizAttempt(models.Model):
    id = models.AutoField(primary_key=True)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.IntegerField(null=True, blank=True)
    total_questions = models.IntegerField()
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    passed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.quiz} - {self.score}"

    def mark_lesson_completed(self):
        if self.passed:
            StudentLessonProgress.objects.update_or_create(
                student=self.student,
                subtopic=self.quiz.subtopic,
                defaults={'is_completed': True}
            )
    def calculate_score(self):
        correct_answers = StudentAnswer.objects.filter(quiz_attempt=self, is_correct=True).count()
        return (correct_answers / self.total_questions) * 100
