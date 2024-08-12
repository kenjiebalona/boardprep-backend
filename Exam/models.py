from django.db import models
from django.utils import timezone
from django.apps import apps

from Question.models import Question, QuestionGenerator, StudentAnswer

class Exam(QuestionGenerator):
    id = models.AutoField(primary_key=True)
    course = models.OneToOneField('Course.Course', on_delete=models.CASCADE, related_name='exam', null=True, blank=True)
    student = models.ForeignKey('User.Student', on_delete=models.CASCADE)
    class_instance = models.ForeignKey('Class.Class', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    questions = models.ManyToManyField(Question, through='ExamQuestion')
    passing_score = models.FloatField(default=0.75)

    def __str__(self):
        return self.title
    
    def get_failed_lessons(self, student_exam_attempt):
        lesson_scores = {}
        student_answers = StudentAnswer.objects.filter(exam_attempt=student_exam_attempt)
        
        for answer in student_answers:
            lesson = answer.question.quiz.lesson
            if lesson not in lesson_scores:
                lesson_scores[lesson] = {'correct': 0, 'total': 0}
            
            lesson_scores[lesson]['total'] += 1
            if answer.is_correct:
                lesson_scores[lesson]['correct'] += 1

        failed_lessons = []
        for lesson, scores in lesson_scores.items():
            if scores['total'] > 0 and scores['correct'] / scores['total'] < 0.75:  
                failed_lessons.append(lesson)

        return failed_lessons
    
class StudentExamAttempt(models.Model):
    id = models.AutoField(primary_key=True)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    score = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    total_questions = models.IntegerField()
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student} - {self.exam} - {self.score}"
    
    def process_results(self):
        self.score = self.calculate_score()
        self.save()

        student_lesson_progress_model = apps.get_model('Course', 'StudentLessonProgress')

        if not self.passed:
            failed_lessons = self.exam.get_failed_lessons(self)
            for lesson in failed_lessons:
                student_lesson_progress_model.objects.filter(student=self.student, lesson=lesson).update(is_completed=False)

    def calculate_score(self):
        correct_answers = StudentAnswer.objects.filter(exam_attempt=self, is_correct=True).count()
        return (correct_answers / self.total_questions) * 100

class ExamQuestion(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']
