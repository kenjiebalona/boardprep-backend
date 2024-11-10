from django.db import models
import random

from Class.models import Attachment


# Create your models here.
class Question(models.Model):
    id = models.AutoField(primary_key=True)
    learning_objective = models.ForeignKey('Course.LearningObjective', on_delete=models.CASCADE)
    text = models.TextField()
    difficulty = models.IntegerField(choices=[(1, 'Beginner'), (2, 'Intermediate'), (3, 'Advanced')])
    attachments = models.ManyToManyField(Attachment, blank=True, related_name='questions')

    def __str__(self):
        difficulty_label = dict(self._meta.get_field('difficulty').choices).get(self.difficulty, 'Unknown')
        return f"Question ID: {self.id} - Difficulty: {difficulty_label} - Text: {self.text[:50]}..."


class Choice(models.Model):
    id = models.AutoField(primary_key=True)
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"Choice ID: {self.id} - Question ID: {self.question.id} - Text: {self.text} - Correct: {self.is_correct}"


class StudentAnswer(models.Model):
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey('User.Student', on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    is_correct = models.BooleanField()
    quiz_attempt = models.ForeignKey('Quiz.StudentQuizAttempt', null=True, blank=True, on_delete=models.CASCADE)
    exam_attempt = models.ForeignKey('Exam.StudentExamAttempt', null=True, blank=True, on_delete=models.CASCADE)
    challenge_attempt = models.ForeignKey('Challenge.StudentChallengeAttempt', null=True, blank=True, on_delete=models.CASCADE)
    preassessment_attempt = models.ForeignKey('Preassessment.StudentPreassessmentAttempt', null=True, blank=True, on_delete=models.CASCADE)
    mocktest_attempt = models.ForeignKey('Mocktest.StudentMocktestAttempt', null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        student_id = self.student.user_name if self.student else "None"
        question_id = self.question.id if self.question else "None"
        choice_id = self.selected_choice.id if self.selected_choice else "None"

        return f"Student: {student_id} - Question: {question_id} - Choice: {choice_id} - Correct: {self.is_correct}"


class QuestionGenerator(models.Model):
    questions = models.ManyToManyField('Question.Question')

    class Meta:
        abstract = True

    def generate_questions(self, num_easy, num_medium, num_hard, filter_by=None):
        if filter_by:
            easy_questions = Question.objects.filter(difficulty=1, **filter_by).order_by('?')[:num_easy]
            medium_questions = Question.objects.filter(difficulty=2, **filter_by).order_by('?')[:num_medium]
            hard_questions = Question.objects.filter(difficulty=3, **filter_by).order_by('?')[:num_hard]
        else:
            easy_questions = Question.objects.filter(difficulty=1).order_by('?')[:num_easy]
            medium_questions = Question.objects.filter(difficulty=2).order_by('?')[:num_medium]
            hard_questions = Question.objects.filter(difficulty=3).order_by('?')[:num_hard]

        questions = list(easy_questions) + list(medium_questions) + list(hard_questions)

        # if len(questions) < num_easy + num_medium + num_hard:
        #     raise ValueError("Insufficient questions available to meet the requested quantities.")

        random.shuffle(questions)
        return questions
