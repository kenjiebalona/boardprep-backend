from django.db import models
from Question.models import Question as ExistingQuestion, Choice as ExistingChoice, StudentAnswer as ExistingStudentAnswer
from Class.models import Attachment


# Create your models here.
class Question(ExistingQuestion):
    is_preassessment = models.BooleanField(default=True)
    preassessment_attachments = models.ManyToManyField(Attachment, blank=True, related_name='preassessment_questions')
    

    def __str__(self):
        difficulty_label = dict(self._meta.get_field('difficulty').choices).get(self.difficulty, 'Unknown')
        return f"Question ID: {self.id} - Difficulty: {difficulty_label} - Text: {self.text[:50]}..."


class Choice(ExistingChoice):
    def __str__(self):
        return f"Choice ID: {self.id} - Question ID: {self.question.id} - Text: {self.text} - Correct: {self.is_correct}"


class StudentAnswer(ExistingStudentAnswer):
    # Inherits from ExistingStudentAnswer
    def __str__(self):
        student_id = self.student.user_name if self.student else "None"
        question_id = self.question.id if self.question else "None"
        choice_id = self.selected_choice.id if self.selected_choice else "None"
        return f"Student: {student_id} - Question: {question_id} - Choice: {choice_id} - Correct: {self.is_correct}"
