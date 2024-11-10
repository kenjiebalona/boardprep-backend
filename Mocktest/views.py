from django.db.models import ExpressionWrapper, F, FloatField
from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from Question.models import StudentAnswer
from User.models import StudentMastery
from Course.models import Course
from .models import Mocktest, StudentMocktestAttempt
from .serializer import MocktestSerializer, StudentMocktestAttemptSerializer


# Create your views here.
class MocktestViewSet(viewsets.ModelViewSet):
    queryset = Mocktest.objects.all()
    serializer_class = MocktestSerializer

    @action(detail=False, methods=['get'])
    def today(self, request):
        course_id = request.query_params.get('course_id')
        course_id = "FME101"
        today = timezone.now().date()

        if not course_id:
            return Response({"detail": "course_id parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            course = Course.objects.get(course_id=course_id)
            learning_objectives = course.syllabus.lessons.values_list('topics__learning_objectives', flat=True)
        except Course.DoesNotExist:
            return Response({"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

        mocktest, created = Mocktest.objects.create(date=today, course=course)

        if created:
            try:
                mocktest.generate_questions(num_easy=1, num_medium=1, num_hard=1)
            except ValueError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(mocktest)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class StudentMocktestAttemptViewSet(viewsets.ModelViewSet):
    queryset = StudentMocktestAttempt.objects.all()
    serializer_class = StudentMocktestAttemptSerializer

    @action(detail=False, methods=['post'])
    def calculate_score(self, request):
        attempt_id = request.data.get('attempt_id')
        if not attempt_id:
            return Response({"detail": "attempt_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            attempt = StudentMocktestAttempt.objects.get(mocktestID=attempt_id)
        except StudentMocktestAttempt.DoesNotExist:
            return Response({"detail": "Mocktest attempt not found."}, status=status.HTTP_404_NOT_FOUND)

        answers = StudentAnswer.objects.filter(mocktest_attempt=attempt)
        correct_answers_count = answers.filter(is_correct=True).count()

        subtopic_answers = {}
        for answer in answers:
            subtopic = answer.question.learning_objective
            if subtopic not in subtopic_answers:
                subtopic_answers[subtopic] = []
            subtopic_answers[subtopic].append({
                'question': answer.question,
                'is_correct': answer.is_correct
            })

        for subtopic, answers in subtopic_answers.items():
            student_mastery, created = StudentMastery.objects.get_or_create(student=attempt.student, learning_objective=subtopic)
            student_mastery.update_mastery(answers)

        attempt.score = correct_answers_count
        attempt.end_time = timezone.now()

        attempt.save()

        time_taken = attempt.end_time - attempt.start_time

        return Response({
            'score': attempt.score,
            'total_questions': attempt.total_questions,
            'time_taken': str(time_taken)
        }, status=status.HTTP_200_OK)

    def get_queryset(self):
        student_id = self.request.query_params.get('student_id')
        course_id = self.request.query_params.get('course_id')
        queryset = super().get_queryset()

        if student_id:
            queryset = queryset.filter(student=student_id)

        if course_id:
            mocktests = Mocktest.objects.filter(course__course_id=course_id)
            queryset = queryset.filter(mocktest__in=mocktests)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
