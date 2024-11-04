from django.db import models
from django.utils import timezone
from django.apps import apps

from Question.models import Question, QuestionGenerator, StudentAnswer

class Exam(QuestionGenerator):
    id = models.AutoField(primary_key=True)
    course = models.ForeignKey('Course.Course', on_delete=models.CASCADE)  
    student = models.ForeignKey('User.Student', on_delete=models.CASCADE)
    class_instance = models.ForeignKey('Class.Class', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    questions = models.ManyToManyField(Question, through='ExamQuestion')
    passing_score = models.FloatField(default=0.75)
    
    class Meta:
        unique_together = ('student', 'course', 'class_instance')  

    def __str__(self):
        return self.title
    
    def get_failed_lessons(self, student_exam_attempt):
        subtopic_scores = {}
        student_answers = StudentAnswer.objects.filter(exam_attempt=student_exam_attempt)
        
        for answer in student_answers:
            subtopic = answer.question.quiz.subtopic
            if subtopic not in subtopic_scores:
                subtopic_scores[subtopic] = {'correct': 0, 'total': 0}
            
            subtopic_scores[subtopic]['total'] += 1
            if answer.is_correct:
                subtopic_scores[subtopic]['correct'] += 1

        failed_subtopics = []
        for subtopic, scores in subtopic_scores.items():
            if scores['total'] > 0 and scores['correct'] / scores['total'] < 0.75:  
                failed_subtopics.append(subtopic)

        return failed_subtopics
    
class StudentExamAttempt(models.Model):
    id = models.AutoField(primary_key=True)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    score = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    total_questions = models.IntegerField()
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    attempt_number = models.IntegerField(default=1)
    passed = models.BooleanField(default=False)
    failed_lessons = models.ManyToManyField("Course.Subtopic", blank=True)
    
    def __str__(self):
        return f"{self.exam.student} - {self.exam} - {self.score}"
    
    def process_results(self):
        self.score = self.calculate_score()
        self.save()

        student_subtopic_progress_model = apps.get_model('Course', 'StudentLessonProgress')

        if not self.passed:
            failed_subtopics = self.exam.get_failed_lessons(self)
            for subtopic in failed_subtopics:
                student_subtopic_progress_model.objects.filter(student=self.exam.student, subtopic=subtopic).update(is_completed=False)

    def calculate_score(self):
        correct_answers = StudentAnswer.objects.filter(exam_attempt=self, is_correct=True).count()
        return (correct_answers / self.total_questions) * 100

class ExamQuestion(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)
    attempt = models.ForeignKey(StudentExamAttempt, on_delete=models.CASCADE, related_name='exam_questions')
    class Meta:
        ordering = ['order']
