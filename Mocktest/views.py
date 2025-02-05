from django.db.models import ExpressionWrapper, F, FloatField
from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from Question.models import StudentAnswer, Choice
from User.models import StudentMastery
from Course.models import Course
from .models import Mocktest, StudentMocktestAttempt, MocktestSetQuestion, MocktestQuestion
from .serializer import MocktestSerializer, StudentMocktestAttemptSerializer, MocktestSetQuestionSerializer, MocktestQuestionSerializer
from Question.models import Question
from Question.serializer import QuestionSerializer
import os, environ
from openai import OpenAI

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

        mocktest = Mocktest.objects.create(date=today, course=course)
        mocktest.generate_questions(num_easy=20, num_medium=20, num_hard=10)

        serializer = self.get_serializer(mocktest)
        return Response(serializer.data)

    # @action(detail=False, methods=['get'])
    # def generate_from_set(self, request):
    #     course_id = request.query_params.get('course_id')
    #     course_id = "FME101"
    #     today = timezone.now().date()

    #     if not course_id:
    #         return Response({"detail": "course_id parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

    #     try:

    #         # Create new mocktest
    #         course = Course.objects.get(course_id=course_id)
    #         mocktest = Mocktest.objects.create(date=today, course=course)

    #         # Get all MocktestSetQuestions for the course's learning objectives
    #         mocktest_sets = MocktestSetQuestion.objects.all()

    #         selected_questions = []

    #         # Generate questions based on each MocktestSetQuestion specification
    #         for mocktest_set in mocktest_sets:
    #             # Get regular questions
    #             regular_questions = Question.objects.filter(
    #                 learning_objective=mocktest_set.learning_objective,
    #                 difficulty=mocktest_set.difficulty,
    #                 isai=False
    #             ).order_by('?')[:mocktest_set.number_of_questions]

    #             # Get AI-generated questions
    #             ai_questions = Question.objects.filter(
    #                 learning_objective=mocktest_set.learning_objective,
    #                 difficulty=mocktest_set.difficulty,
    #                 isai=True
    #             ).order_by('?')[:mocktest_set.number_ai_questions]

    #             selected_questions.extend(regular_questions)
    #             selected_questions.extend(ai_questions)

    #         # Add questions to mocktest
    #         mocktest.questions.set(selected_questions)

    #         serializer = self.get_serializer(mocktest)
    #         return Response(serializer.data)

    #     except Exception as e:
    #         return Response(
    #             {"detail": str(e)},
    #             status=status.HTTP_500_INTERNAL_SERVER_ERROR
    #         )

    @action(detail=False, methods=['get'])
    def generate_from_set(self, request):
        course_id = request.query_params.get('course_id')
        course_id = "FME101"
        today = timezone.now().date()

        if not course_id:
            return Response({"detail": "course_id parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:

            # Create new mocktest
            course = Course.objects.get(course_id=course_id)
            mocktest = Mocktest.objects.create(date=today, course=course)

            mocktest_questions = MocktestQuestion.objects.all()

            question_ids = mocktest_questions.values_list('question_id', flat=True).distinct()

            selected_questions = Question.objects.filter(id__in=question_ids)

            # Add questions to mocktest
            mocktest.questions.set(selected_questions)

            serializer = self.get_serializer(mocktest)
            return Response(serializer.data)

        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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

        feedback = StudentMocktestAttemptViewSet().generate_feedback(attempt)
        attempt.feedback = feedback
        attempt.save()
        analytics = StudentMocktestAttemptViewSet().generate_analytics(attempt)

        return Response({
            'score': attempt.score,
            'total_questions': attempt.total_questions,
            'time_taken': str(time_taken),
            'feedback': feedback,
            'analytics': analytics
        }, status=status.HTTP_200_OK)

    def create_answer_paragraph(self, correct_answers, wrong_answers):

        correct_paragraph = ""
        wrong_paragraph = ""

        if correct_answers.exists():
            correct_paragraph = "Questions you answered correctly:\n\n"
            for answer in correct_answers:
                question_text = answer.question.text
                learning_objective_title = answer.question.learning_objective.text
                selected_choice_text = answer.selected_choice.text

                correct_paragraph += (
                    f"Learning Objective: {learning_objective_title}\n"
                    f"Question: {question_text}\n"
                    f"Your Answer: {selected_choice_text}\n\n"
                )
        else:
            correct_paragraph = "You didn't answer any questions correctly.\n"

        if wrong_answers.exists():
            wrong_paragraph = "Questions you answered incorrectly:\n\n"
            for answer in wrong_answers:
                question_text = answer.question.text
                # learning_objective_title = answer.question.learning_objective.learning_objective_title
                learning_objective_title = answer.question.learning_objective.text
                selected_choice_text = answer.selected_choice.text
                correct_choice = Choice.objects.filter(question=answer.question, is_correct=True).first()
                correct_answer_text = correct_choice.text if correct_choice else "Not available"

                wrong_paragraph += (
                    f"Learning Objective: {learning_objective_title}\n"
                    f"Question: {question_text}\n"
                    f"Your Answer: {selected_choice_text}\n"
                    f"Correct Answer: {correct_answer_text}\n\n"
                )
        else:
            wrong_paragraph = "You answered all questions correctly.\n"

        return correct_paragraph + wrong_paragraph

    def generate_feedback(self, attempt):
        print("Starting feedback generation")

        env = environ.Env(DEBUG=(bool, False))
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        environ.Env.read_env(os.path.join(BASE_DIR, '.env'))
        client = OpenAI(api_key=env('OPENAI_API_KEY'))

        student = attempt.student
        student_name = f"{student.first_name} {student.last_name}"
        specialization_name = "Computer Science"  # Placeholder for specialization name

        correct_answers = StudentAnswer.objects.filter(mocktest_attempt=attempt, is_correct=True)
        wrong_answers = StudentAnswer.objects.filter(mocktest_attempt=attempt, is_correct=False)

        print(correct_answers)
        print(wrong_answers)

        answers_paragraph = self.create_answer_paragraph(correct_answers, wrong_answers)
        print(answers_paragraph)

        total_questions = attempt.total_questions
        correct_count = correct_answers.count()
        score_percentage = (attempt.score / total_questions) * 100 if total_questions > 0 else 0

        passed = score_percentage >= 75

        print(f"Generating feedback for {student_name}, {specialization_name}")

        if 0 <= score_percentage < 25:
            score_feedback = f"Poor performance. You answered {correct_count} out of {total_questions} questions correctly. You need to review the material and focus on understanding the key concepts."
        elif 25 <= score_percentage < 50:
            score_feedback = f"Below average performance. You answered {correct_count} out of {total_questions} questions correctly. You have some understanding, but there are significant areas for improvement."
        elif 50 <= score_percentage < 75:
            score_feedback = f"Average performance. You answered {correct_count} out of {total_questions} questions correctly. You understand the basics, but more practice is needed to strengthen your knowledge."
        elif 75 <= score_percentage < 90:
            score_feedback = f"Good performance. You answered {correct_count} out of {total_questions} questions correctly. You have a solid understanding, but there's still room for improvement."
        elif 90 <= score_percentage <= 100:
            score_feedback = f"Excellent performance! You answered {correct_count} out of {total_questions} questions correctly. You have a strong grasp of the material."
        else:
            score_feedback = "Invalid score. Please check the data."

        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are Preppy, BoardPrep's Engineering Companion and an excellent and critical engineer, tasked with providing constructive feedback on mocktest performances of your students. In giving feedback, you don't thank the student for sharing the details, instead you congratulate the student first for finishing the mocktest, then you provide your feedbacks. Be critical about your feedback expecially if the student failed the mocktest so that they will know more where and how to improve. After providing your feedbacks, you then put your signature at the end of your response"},
                {"role": "user", "content": f"I am {student_name}, a {specialization_name} major, and here are the details of my test. Score: {attempt.score}, Total Questions: {total_questions}, Perecentage: {score_percentage:.2f}%), Passed: {passed}\n\n{answers_paragraph}\n\nHere's an initial assessment of your performance:\n\n{score_feedback}\n\nBased on these results, can you provide some detailed feedback and suggestions for improvement if needed, like what subjects to focus on, which field I excel in, and some strategies? Address me directly, and don't put any placeholders as this will be displayed directly in unformatted text form."}
            ]
        )

        print(completion)

        ai_feedback = completion.choices[0].message.content.strip()
        final_feedback = f"{ai_feedback}\n\nAdditional Performance Summary:\n{score_feedback}"
        print(f"Feedback generated: {final_feedback[:100]}...")
        return final_feedback

    def generate_analytics(self, attempt):
        print("Starting analytics generation")

        correct_answers = StudentAnswer.objects.filter(mocktest_attempt=attempt, is_correct=True)
        wrong_answers = StudentAnswer.objects.filter(mocktest_attempt=attempt, is_correct=False)

        total_questions = attempt.total_questions
        score_percentage = (attempt.score / total_questions) * 100 if total_questions > 0 else 0
        passed = score_percentage >= 75

        if attempt.end_time:
            total_time = attempt.end_time - attempt.start_time
            total_time_seconds = total_time.total_seconds()
        else:
            total_time_seconds = 0  # If end_time is not set yet
        average_time_per_question = total_time_seconds / total_questions if total_questions > 0 else 0


        # Analyze difficulty levels
        difficulty_analysis = {
            "correct": {},
            "wrong": {}
        }

        for answer in correct_answers:
            difficulty = answer.question.difficulty
            difficulty_analysis["correct"].setdefault(difficulty, 0)
            difficulty_analysis["correct"][difficulty] += 1

        for answer in wrong_answers:
            difficulty = answer.question.difficulty
            difficulty_analysis["wrong"].setdefault(difficulty, 0)
            difficulty_analysis["wrong"][difficulty] += 1

        # Analyze learning objectives
        learning_objective_analysis = {
            "correct": {},
            "wrong": {}
        }

        for answer in correct_answers:
            learning_objective_text = answer.question.learning_objective.text
            learning_objective_analysis["correct"].setdefault(learning_objective_text, 0)
            learning_objective_analysis["correct"][learning_objective_text] += 1

        for answer in wrong_answers:
            learning_objective_text = answer.question.learning_objective.text
            learning_objective_analysis["wrong"].setdefault(learning_objective_text, 0)
            learning_objective_analysis["wrong"][learning_objective_text] += 1


        # Summary of performance trends
        performance_trends = {
            "strong_learning_objectives": [
                obj for obj, count in learning_objective_analysis["correct"].items() if count >= 3
            ],
            "weak_learning_objectives": [
                obj for obj, count in learning_objective_analysis["wrong"].items() if count >= 3
            ],
            "hardest_difficulty": max(difficulty_analysis["wrong"].items(), key=lambda x: x[1], default=None),
            "easiest_difficulty": max(difficulty_analysis["correct"].items(), key=lambda x: x[1], default=None)
        }

        # Construct analytics object
        analytics = {
            "total_questions": total_questions,
            "correct_answers": correct_answers.count(),
            "wrong_answers": wrong_answers.count(),
            "score_percentage": round(score_percentage, 2),
            "difficulty_analysis": difficulty_analysis,
            "learning_objective_analysis": learning_objective_analysis,
            "time_spent": {
                "total_time": total_time_seconds,
                "average_time_per_question": round(average_time_per_question, 2)
            },
            "performance_trends": performance_trends
        }

        print("Analytics generated:", analytics)
        return analytics

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

class MocktestSetQuestionViewSet(viewsets.ModelViewSet):
    queryset = MocktestSetQuestion.objects.all()
    serializer_class = MocktestSetQuestionSerializer

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

    # @action(detail=False, methods=['post'])
    # def bulk(self, request, *args, **kwargs):
    #     serializer = self.get_serializer(data=request.data, many=True)
    #     if serializer.is_valid():
    #         self.perform_create(serializer)
    #         headers = self.get_success_headers(serializer.data)
    #         return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def bulk(self, request, *args, **kwargs):
        """
        Bulk create MocktestSetQuestions with automatic syncing
        """
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        # Save and sync each created instance
        instances = serializer.save()

        for instance in instances:
            self.sync_mocktest_questions(instance)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

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

        mocktest_set_question_id = instance.id

        MocktestQuestion.objects.filter(mocktest_set_question_id=mocktest_set_question_id).delete()

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def sync_mocktest_questions(self, instance):
        # Calculate current number of associated MocktestQuestions
        current_mocktest_questions = MocktestQuestion.objects.filter(
            mocktest_set_question_id=instance
        )

        total_expected_questions = instance.number_of_questions + instance.number_ai_questions
        current_count = current_mocktest_questions.count()

        if current_count > total_expected_questions:
            # Remove excess questions
            ai_questions = current_mocktest_questions.filter(question__isai=True)
            non_ai_questions = current_mocktest_questions.filter(question__isai=False)

            ai_current = ai_questions.count()
            non_ai_current = non_ai_questions.count()

            ai_to_remove = max(0, ai_current - instance.number_ai_questions)
            non_ai_to_remove = max(0, non_ai_current - instance.number_of_questions)

            for _ in range(ai_to_remove):
                question_to_delete = ai_questions.order_by('?').first()
                if question_to_delete:
                    question_to_delete.delete()

            for _ in range(non_ai_to_remove):
                question_to_delete = non_ai_questions.order_by('?').first()
                if question_to_delete:
                    question_to_delete.delete()

        elif current_count < total_expected_questions:
            # Find additional questions to add
            # First, get existing question IDs to avoid duplicates
            existing_question_ids = current_mocktest_questions.values_list('question_id', flat=True)

            # Determine question types to add
            regular_needed = instance.number_of_questions - current_mocktest_questions.filter(
                question__isai=False
            ).count()

            ai_needed = instance.number_ai_questions - current_mocktest_questions.filter(
                question__isai=True
            ).count()

            # Query for additional regular questions
            additional_regular_questions = Question.objects.filter(
                learning_objective=instance.learning_objective,
                difficulty=instance.difficulty,
                isai=False
            ).exclude(id__in=existing_question_ids).order_by('?')[:regular_needed]

            # Query for additional AI questions
            additional_ai_questions = Question.objects.filter(
                learning_objective=instance.learning_objective,
                difficulty=instance.difficulty,
                isai=True
            ).exclude(id__in=existing_question_ids).order_by('?')[:ai_needed]

            new_mocktest_questions = []
            for question in list(additional_regular_questions) + list(additional_ai_questions):
                MocktestQuestion.objects.create(
                    mocktest_set_question_id=instance,
                    question=question
                )

    def perform_update(self, serializer):
        """
        Override perform_update to synchronize MocktestQuestions after update
        """
        instance = serializer.save()
        self.sync_mocktest_questions(instance)
        return instance

    def perform_create(self, serializer):
        """
        Override perform_create to synchronize MocktestQuestions after creation
        """
        instance = serializer.save()
        self.sync_mocktest_questions(instance)
        return instance

class MocktestQuestionViewSet(viewsets.ModelViewSet):
    queryset = MocktestQuestion.objects.all()
    serializer_class = MocktestQuestionSerializer

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

    @action(detail=False, methods=['post'])
    def bulk(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=True)
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

        mocktest_set_question = instance.mocktest_set_question_id

        if instance.question.isai:
            mocktest_set_question.number_ai_questions -= 1
        else:
            mocktest_set_question.number_of_questions -= 1

        mocktest_set_question.save()

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'])
    def initialize(self, request, *args, **kwargs):
        # Get optional filters from request
        mocktest_set_id = request.data.get('mocktest_set_question_id')

        # Query MocktestSetQuestion with optional filters
        mocktest_set_questions = MocktestSetQuestion.objects.all()

        if mocktest_set_id:
            mocktest_set_questions = mocktest_set_questions.filter(id=mocktest_set_id)

        created_questions = []

        for mocktest_set_question in mocktest_set_questions:
            regular_questions_needed = mocktest_set_question.number_of_questions
            ai_questions_needed = mocktest_set_question.number_ai_questions

            # Find existing questions for this mocktest set
            existing_question_ids = MocktestQuestion.objects.filter(
                mocktest_set_question_id=mocktest_set_question
            ).values_list('question_id', flat=True)

            available_regular_questions = Question.objects.filter(
                learning_objective=mocktest_set_question.learning_objective,
                difficulty=mocktest_set_question.difficulty,
                isai=False  # Assuming there's a flag to identify AI-generated questions
            ).exclude(id__in=existing_question_ids)

            available_ai_questions = Question.objects.filter(
                learning_objective=mocktest_set_question.learning_objective,
                difficulty=mocktest_set_question.difficulty,
                isai=True  # Assuming there's a flag to identify AI-generated questions
            ).exclude(id__in=existing_question_ids)

            selected_regular_questions = available_regular_questions.order_by('?')[:regular_questions_needed]
            selected_ai_questions = available_ai_questions.order_by('?')[:ai_questions_needed]

            selected_questions = list(selected_regular_questions) + list(selected_ai_questions)

            for question in selected_questions:
                mocktest_question = MocktestQuestion.objects.create(
                    mocktest_set_question_id=mocktest_set_question,
                    question=question
                )
                created_questions.append(mocktest_question)


        serializer = self.get_serializer(created_questions, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def get_mocktest_questions(self, request, *args, **kwargs):
        mocktest_questions = MocktestQuestion.objects.all()

        question_ids = mocktest_questions.values_list('question_id', flat=True).distinct()

        questions = Question.objects.filter(id__in=question_ids)

        serializer = QuestionSerializer(questions, many=True)

        return Response(serializer.data)