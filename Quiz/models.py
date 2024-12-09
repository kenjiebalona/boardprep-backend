from collections import defaultdict
import random
from django.db import models
from django.utils import timezone

from Question.models import QuestionGenerator, Question

from Course.models import LearningObjective, StudentLessonProgress
from Question.models import StudentAnswer

# Create your models here.
class Quiz(QuestionGenerator):
    id = models.AutoField(primary_key=True)
    lesson = models.ForeignKey('Course.Lesson', on_delete=models.CASCADE)
    subtopic = models.ForeignKey('Course.Subtopic', on_delete=models.CASCADE)
    student = models.ForeignKey('User.Student', on_delete=models.CASCADE)
    class_instance = models.ForeignKey('Class.Class', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    questions = models.ManyToManyField('Question.Question')
    passing_score = models.FloatField(default=0.75)
    is_locked = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    def generate_questions(self, num_easy, num_medium, num_hard):
        # Gather all learning objectives associated with the lesson through its topics and subtopics
        learning_objectives = LearningObjective.objects.filter(
            subtopic__topic__lesson=self.lesson
        )

        questions_by_difficulty = defaultdict(list)

        # For each learning objective, gather questions by difficulty level
        for objective in learning_objectives:
            easy_questions = Question.objects.filter(learning_objective=objective, difficulty=1).order_by('?')[:num_easy]
            medium_questions = Question.objects.filter(learning_objective=objective, difficulty=2).order_by('?')[:num_medium]
            hard_questions = Question.objects.filter(learning_objective=objective, difficulty=3).order_by('?')[:num_hard]

            # Add questions to the grouped lists
            questions_by_difficulty[1].extend(easy_questions)
            questions_by_difficulty[2].extend(medium_questions)
            questions_by_difficulty[3].extend(hard_questions)

        # Consolidate all questions, ensuring they’re shuffled
        selected_easy_questions = random.sample(questions_by_difficulty[1], min(5, len(questions_by_difficulty[1])))
        selected_medium_questions = random.sample(questions_by_difficulty[2], min(3, len(questions_by_difficulty[2])))
        selected_hard_questions = random.sample(questions_by_difficulty[3], min(2, len(questions_by_difficulty[3])))

        # Combine selected questions and shuffle
        all_questions = selected_easy_questions + selected_medium_questions + selected_hard_questions
        random.shuffle(all_questions)

        return all_questions


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
                learning_objective=self.quiz.learning_objective,
                defaults={'is_completed': True}
            )
    def calculate_score(self):
        correct_answers = StudentAnswer.objects.filter(quiz_attempt=self, is_correct=True).count()
        return (correct_answers / self.total_questions) * 100
