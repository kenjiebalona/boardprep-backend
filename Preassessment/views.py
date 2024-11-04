from django.db.models import ExpressionWrapper, F, FloatField
from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from Question.models import StudentAnswer
from User.models import StudentMastery
from Course.models import Course
from .models import Preassessment, StudentPreassessmentAttempt
from .serializer import PreassessmentSerializer, StudentPreassessmentAttemptSerializer


# Create your views here.
class PreassessmentViewSet(viewsets.ModelViewSet):
    queryset = Preassessment.objects.all()
    serializer_class = PreassessmentSerializer

    @action(detail=False, methods=['get'])
    def today(self, request):
        course_id = request.query_params.get('course_id')
        today = timezone.now().date()

        if not course_id:
            return Response({"detail": "course_id parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            course = Course.objects.get(course_id=course_id)
            subtopics = course.syllabus.lessons.values_list('topics__subtopics', flat=True)
        except Course.DoesNotExist:
            return Response({"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

        preassessment, created = Preassessment.objects.get_or_create(date=today, course=course)

        if created:
            filter_by = {'subtopic__in': subtopics}
            try:
                preassessment.generate_questions(num_easy=20, num_medium=29, num_hard=1, filter_by=filter_by)
            except ValueError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(preassessment)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class StudentPreassessmentAttemptViewSet(viewsets.ModelViewSet):
    queryset = StudentPreassessmentAttempt.objects.all()
    serializer_class = StudentPreassessmentAttemptSerializer

    @action(detail=False, methods=['post'])
    def calculate_score(self, request):
        attempt_id = request.data.get('attempt_id')
        if not attempt_id:
            return Response({"detail": "attempt_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            attempt = StudentPreassessmentAttempt.objects.get(preassessmentID=attempt_id)
        except StudentPreassessmentAttempt.DoesNotExist:
            return Response({"detail": "Preassessment attempt not found."}, status=status.HTTP_404_NOT_FOUND)

        answers = StudentAnswer.objects.filter(preassessment_attempt=attempt)
        correct_answers_count = answers.filter(is_correct=True).count()

        subtopic_answers = {}
        for answer in answers:
            subtopic = answer.question.subtopic
            if subtopic not in subtopic_answers:
                subtopic_answers[subtopic] = []
            subtopic_answers[subtopic].append({
                'question': answer.question,
                'is_correct': answer.is_correct
            })

        for subtopic, answers in subtopic_answers.items():
            student_mastery, created = StudentMastery.objects.get_or_create(student=attempt.student, subtopic=subtopic)
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
