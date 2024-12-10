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
import os, environ
from openai import OpenAI

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

        feedback = StudentQuizAttemptViewSet().generate_feedback(attempt)
        attempt.feedback = feedback
        attempt.save()

        return Response({
            'score': attempt.score,
            'total_questions': attempt.total_questions,
            'passed': attempt.passed,
            'time_taken': str(time_taken),
            'feedback': feedback
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

        student = attempt.quiz.student
        student_name = f"{student.first_name} {student.last_name}"
        specialization_name = "Computer Science"  # Placeholder for specialization name

        correct_answers = StudentAnswer.objects.filter(quiz_attempt=attempt, is_correct=True)
        wrong_answers = StudentAnswer.objects.filter(quiz_attempt=attempt, is_correct=False)

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
                {"role": "system", "content": "You are Preppy, BoardPrep's Engineering Companion and an excellent and critical engineer, tasked with providing constructive feedback on quiz performances of your students. In giving feedback, you don't thank the student for sharing the details, instead you congratulate the student first for finishing the quiz, then you provide your feedbacks. Be critical about your feedback expecially if the student failed the quiz so that they will know more where and how to improve. After providing your feedbacks, you then put your signature at the end of your response"},
                {"role": "user", "content": f"I am {student_name}, a {specialization_name} major, and here are the details of my test. Score: {attempt.score}, Total Questions: {total_questions}, Perecentage: {score_percentage:.2f}%), Passed: {attempt.passed}\n\n{answers_paragraph}\n\nHere's an initial assessment of your performance:\n\n{score_feedback}\n\nBased on these results, can you provide some detailed feedback and suggestions for improvement if needed, like what subjects to focus on, which field I excel in, and some strategies? Address me directly, and don't put any placeholders as this will be displayed directly in unformatted text form."}
            ]
        )

        print(completion)

        ai_feedback = completion.choices[0].message.content.strip()
        final_feedback = f"{ai_feedback}\n\nAdditional Performance Summary:\n{score_feedback}"
        print(f"Feedback generated: {final_feedback[:100]}...")
        return final_feedback

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

    @action(detail=False, methods=['get'], url_path='by-id')
    def get_attempts_by_id(self, request):
        student_id = request.query_params.get('id')

        if not student_id:
            return Response({"detail": "Student ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(self.queryset.filter(quiz__student_id=student_id).values())