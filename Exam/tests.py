from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from Course.models import Course, Syllabus, Lesson
from Quiz.models import Quiz, StudentQuizAttempt
from Question.models import Question, Choice
from User.models import Student, Specialization, User
from Institution.models import Institution
from .models import Exam, ExamQuestion
from django.contrib.auth.hashers import make_password
from datetime import date
from django.db.models import Count

class AdaptiveExamTest(TestCase):
    def setUp(self):
        # Create necessary objects
        self.client = APIClient()
        self.institution = Institution.objects.create(InstitutionName='Test Institution')
        self.specialization = Specialization.objects.create(name='Test Specialization')
        
        # Create User instance directly
        self.user = User.objects.create(
            user_name='teststudent',
            password=make_password('testpass'),  # Hash the password manually
            first_name='Test',
            last_name='Student',
            email='test@student.com',
            registration_date=date.today()  # Explicitly set the registration date
        )
        
        # Create Student instance based on User
        self.student = Student.objects.create(
            user_name=self.user.user_name,
            password=self.user.password,
            first_name=self.user.first_name,
            last_name=self.user.last_name,
            email=self.user.email,
            registration_date=self.user.registration_date,  # Explicitly set the registration date
            specialization=self.specialization,
            institution_id=self.institution
        )
        
        self.course = Course.objects.create(course_id='TEST101', course_title='Test Course')
        self.syllabus = Syllabus.objects.create(course=self.course, syllabus_id='SYL101')
        self.exam = Exam.objects.create(course=self.course, title='Test Adaptive Exam')

        self.lessons = []
        self.quizzes = []
        for i in range(5):
            lesson = Lesson.objects.create(syllabus=self.syllabus, lesson_id=f'L{i+1}', lesson_title=f'Lesson {i+1}', order=i+1)
            self.lessons.append(lesson)
            quiz = Quiz.objects.create(lesson=lesson, title=f'Quiz {i+1}', student=self.student)
            self.quizzes.append(quiz)
            for j in range(100):  # Create 100 questions per lesson to ensure enough questions
                difficulty = (j % 3) + 1  # Distribute difficulties evenly
                question = Question.objects.create(
                    lesson=lesson, 
                    text=f'Question {j+1} for Lesson {i+1}',
                    difficulty=difficulty
                )
                Choice.objects.create(question=question, text='Correct', is_correct=True)
                Choice.objects.create(question=question, text='Incorrect', is_correct=False)

    def create_quiz_attempts(self, scores):
        for quiz, score in zip(self.quizzes, scores):
            StudentQuizAttempt.objects.create(
                quiz=quiz,
                score=score,
                total_questions=30
            )

    def test_generate_adaptive_exam(self):
        self.create_quiz_attempts([55, 75, 90, 65, 85])
        self.client.force_authenticate(user=self.user)
        url = reverse('exam-generate-adaptive-exam', kwargs={'pk': self.exam.id})
        response = self.client.post(url, {'student_id': self.student.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        exam_questions = ExamQuestion.objects.filter(exam=self.exam)
        question_count = exam_questions.count()

        # Check that exactly 100 questions were generated
        self.assertEqual(question_count, 100)

        # Check distribution
        question_distribution = response.data['question_distribution']
        self.assertEqual(sum(question_distribution.values()), 100)

        # Check that lessons with lower scores have more questions
        self.assertGreater(question_distribution[self.lessons[0].lesson_id], question_distribution[self.lessons[2].lesson_id])
        self.assertGreater(question_distribution[self.lessons[3].lesson_id], question_distribution[self.lessons[4].lesson_id])

        # Check difficulty distribution
        difficulty_counts = exam_questions.values('question__difficulty').annotate(count=Count('id'))
        difficulty_dict = {item['question__difficulty']: item['count'] for item in difficulty_counts}

        # Ensure there's a roughly equal distribution of difficulties
        self.assertAlmostEqual(difficulty_dict[1] / question_count, 1/3, delta=0.05)
        self.assertAlmostEqual(difficulty_dict[2] / question_count, 1/3, delta=0.05)
        self.assertAlmostEqual(difficulty_dict[3] / question_count, 1/3, delta=0.05)

        # Check average difficulty
        avg_difficulty = response.data['average_difficulty']
        self.assertAlmostEqual(avg_difficulty, 2, delta=0.1)

    def test_regenerate_exam(self):
        self.create_quiz_attempts([70, 70, 70, 70, 70])
        self.client.force_authenticate(user=self.user)
        url = reverse('exam-generate-adaptive-exam', kwargs={'pk': self.exam.id})
        
        # Generate exam twice
        self.client.post(url, {'student_id': self.student.id})
        first_questions = set(ExamQuestion.objects.filter(exam=self.exam).values_list('question_id', flat=True))
        
        ExamQuestion.objects.filter(exam=self.exam).delete()  # Clear existing questions
        
        self.client.post(url, {'student_id': self.student.id})
        second_questions = set(ExamQuestion.objects.filter(exam=self.exam).values_list('question_id', flat=True))

        # Check that the questions are different (or at least not all the same)
        self.assertNotEqual(first_questions, second_questions)
        self.assertLess(len(first_questions.intersection(second_questions)), 100)  # Some questions should be different
