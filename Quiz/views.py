from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from Question.models import StudentAnswer
from Quiz.models import Quiz, StudentQuizAttempt
from Quiz.serializer import QuizSerializer, StudentQuizAttemptSerializer

# Create your views here.
class QuizViewSet(viewsets.ModelViewSet):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            num_easy = 3  # Example hardcoded values
            num_medium = 2
            num_hard = 1
            quiz = serializer.save()
            try:
                questions = quiz.generate_questions(num_easy, num_medium, num_hard)
            except ValueError as e:
                quiz.delete()
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            quiz.questions.set(questions)
            quiz.save()
            response_serializer = self.get_serializer(quiz)
            headers = self.get_success_headers(response_serializer.data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='class')
    def get_by_lesson_and_class(self, request, *args, **kwargs):
        lesson_id = request.query_params.get('lesson_id')
        class_id = request.query_params.get('class_id')

        if not lesson_id or not class_id:
            return Response(
                {"detail": "Both 'lesson_id' and 'class_id' query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        quizzes = self.queryset.filter(lesson_id=lesson_id, class_instance_id=class_id)

        best_attempts = {}

        for quiz in quizzes:
            student_quiz_attempts = StudentQuizAttempt.objects.filter(quiz=quiz)

            for attempt in student_quiz_attempts:
                key = (quiz.student_id, quiz.lesson_id)
                current_best_score = best_attempts.get(key).score if key in best_attempts else None
                if current_best_score is None or (attempt.score is not None and attempt.score > current_best_score):
                    best_attempts[key] = attempt

        result = []
        for (student_id, lesson_id), attempt in best_attempts.items():
            result.append({
                'student': attempt.quiz.student.first_name + " " + attempt.quiz.student.last_name,
                'quiz_id': attempt.quiz.id,
                'lesson': attempt.quiz.lesson.lesson_id,
                'score': attempt.score,
                'total_questions': attempt.total_questions,
                'start_time': attempt.start_time,
                'end_time': attempt.end_time,
                'passed': attempt.passed,
            })

        return Response(result, status=status.HTTP_200_OK)

    def get_queryset(self):
        queryset = super().get_queryset()
        student_id = self.request.query_params.get('student_id')
        lesson_id = self.request.query_params.get('lesson_id')

        if student_id and lesson_id:
            queryset = queryset.filter(student_id=student_id, lesson_id=lesson_id)
        else:
            queryset = queryset.none()
        return queryset

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class StudentQuizAttemptViewSet(viewsets.ModelViewSet):
    queryset = StudentQuizAttempt.objects.all()
    serializer_class = StudentQuizAttemptSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        quiz_id = self.request.query_params.get('quiz_id')

        if quiz_id:
            queryset = queryset.filter(quiz_id=quiz_id)
        else:
            queryset = queryset.none()
        return queryset

    @action(detail=False, methods=['post'])
    def calculate_score(self, request):
        attempt_id = request.data.get('attempt_id')
        if not attempt_id:
            return Response({"detail": "attempt_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            attempt = StudentQuizAttempt.objects.get(id=attempt_id)
        except StudentQuizAttempt.DoesNotExist:
            return Response({"detail": "Quiz attempt not found."}, status=status.HTTP_404_NOT_FOUND)

        correct_answers_count = StudentAnswer.objects.filter(
            quiz_attempt=attempt,
            is_correct=True
        ).count()

        attempt.score = correct_answers_count
        attempt.end_time = timezone.now()

        total_questions = attempt.total_questions
        passing_score = attempt.quiz.passing_score
        passed = (correct_answers_count / total_questions) >= passing_score
        attempt.passed = passed

        attempt.save()

        time_taken = attempt.end_time - attempt.start_time

        return Response({
            'score': attempt.score,
            'total_questions': attempt.total_questions,
            'passed': attempt.passed,
            'time_taken': str(time_taken)
        }, status=status.HTTP_200_OK)

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

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
