from django.db import models


# Create your models here.
class Question(models.Model):
    id = models.AutoField(primary_key=True)
    text = models.TextField()

    def __str__(self):
        return f"Pre-Assessment: {self.id}"


class Choice(models.Model):
    id = models.AutoField(primary_key=True)
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"Choice ID: {self.id} - Question ID: {self.question.id} - Text: {self.text} - Correct: {self.is_correct}"


class StudentAnswer(models.Model):
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey('User.Student', related_name='student_answers', on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    is_correct = models.BooleanField()

    def __str__(self):
        student_id = self.student.user_name if self.student else "None"
        question_id = self.question.id if self.question else "None"
        choice_id = self.selected_choice.id if self.selected_choice else "None"

        return f"Student: {student_id} - Question: {question_id} - Choice: {choice_id} - Correct: {self.is_correct}"
