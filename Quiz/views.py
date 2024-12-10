from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from Question.models import StudentAnswer
from Quiz.models import Quiz, StudentQuizAttempt
from Quiz.serializer import QuizSerializer, StudentQuizAttemptSerializer
from User.models import StudentMastery
from Course.models import LearningObjective
from Question.models import Question
from Question.models import Choice
from Course.models import Subtopic

# Create your views here.
class QuizViewSet(viewsets.ModelViewSet):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            num_easy = 1  # Example hardcoded values
            num_medium = 1
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
        learning_objective_id = request.query_params.get('learning_objective_id')
        class_id = request.query_params.get('class_id')

        if not learning_objective_id or not class_id:
            return Response(
                {"detail": "Both 'learning_objective_id' and 'class_id' query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        quizzes = self.queryset.filter(learning_objective_id=learning_objective_id, class_instance_id=class_id)

        best_attempts = {}

        for quiz in quizzes:
            student_quiz_attempts = StudentQuizAttempt.objects.filter(quiz=quiz)

            for attempt in student_quiz_attempts:
                key = (quiz.student_id, quiz.learning_objective_id)
                current_best_score = best_attempts.get(key).score if key in best_attempts else None
                if current_best_score is None or (attempt.score is not None and attempt.score > current_best_score):
                    best_attempts[key] = attempt

        result = []
        for (student_id, learning_objective_id), attempt in best_attempts.items():
            result.append({
                'student': attempt.quiz.student.first_name + " " + attempt.quiz.student.last_name,
                'quiz_id': attempt.quiz.id,
                'subtopic': attempt.quiz.learning_objective.subtopic.subtopic_id,
                'score': attempt.score,
                'total_questions': attempt.total_questions,
                'start_time': attempt.start_time,
                'end_time': attempt.end_time,
                'passed': attempt.passed,
            })

        return Response(result, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='subtopic')
    def subtopic(self, request, *args, **kwargs):
        subtopic_id = request.query_params.get('id')
        serializer = self.get_serializer(data=request.data)

        try:
            subtopic = Subtopic.objects.get(id=subtopic_id)
        except Subtopic.DoesNotExist:
            return Response({"detail": "Subtopic not found."}, status=status.HTTP_404_NOT_FOUND)

        if serializer.is_valid():
            quiz = serializer.save()

        learning_objectives = LearningObjective.objects.filter(subtopic_id=subtopic_id)

        questions = Question.objects.filter(learning_objective__in=learning_objectives)

        quiz.questions.set(questions)

        quiz.save()
        response_serializer = self.get_serializer(quiz)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)


    def get_queryset(self):
        queryset = super().get_queryset()
        student_id = self.request.query_params.get('student_id')
        subtopic_id = self.request.query_params.get('subtopic_id')

        if student_id and subtopic_id:
            queryset = queryset.filter(student_id=student_id, subtopic_id=subtopic_id)
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

        answers = StudentAnswer.objects.filter(quiz_attempt=attempt)
        correct_answers_count = answers.filter(is_correct=True).count()

        learning_objective_answers = {}
        for answer in answers:
            learning_objective = answer.question.learning_objective
            if learning_objective not in learning_objective_answers:
                learning_objective_answers[learning_objective] = []
            learning_objective_answers[learning_objective].append({
                'question': answer.question,
                'is_correct': answer.is_correct
            })

        for learning_objective, answers in learning_objective_answers.items():
            student_mastery, created = StudentMastery.objects.get_or_create(student=attempt.quiz.student, learning_objective=learning_objective)
            student_mastery.update_mastery(answers)

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
