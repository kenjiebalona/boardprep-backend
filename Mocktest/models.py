from django.db import models
from django.utils import timezone
from Question.models import Question, QuestionGenerator


# Create your models here.
class Mocktest(QuestionGenerator):
    mocktestID = models.BigAutoField(primary_key=True)
    course = models.ForeignKey('Course.Course', on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now, unique=False)

    def __str__(self):
        return f"MockTest ID: {self.mocktestID}"

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
class MocktestSetQuestion(models.Model):
    learning_objective =  models.ForeignKey('Course.LearningObjective', on_delete=models.CASCADE, related_name='learning_objective')
    difficulty = models.IntegerField(choices=[(1, 'Beginner'), (2, 'Intermediate'), (3, 'Advanced')])
    number_of_questions = models.IntegerField()
    number_ai_questions = models.IntegerField()

class MocktestQuestion(models.Model):
    mocktest_set_question_id = models.ForeignKey(MocktestSetQuestion, on_delete=models.CASCADE, related_name='mocktest')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='question')
