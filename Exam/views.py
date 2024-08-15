from collections import defaultdict
from django.shortcuts import render
from Course.models import StudentLessonProgress
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from Question.models import Question, StudentAnswer, Choice
from Question.serializer import QuestionSerializer
from Quiz.models import StudentQuizAttempt
from User.models import Student
from .models import Exam, ExamQuestion, StudentExamAttempt
from .serializer import ExamSerializer, StudentExamAttemptSerializer
from openai import OpenAI
import os, environ
from django.db.models import Avg, Max, Min, Count


class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            num_easy = 3  # Example hardcoded values
            num_medium = 2
            num_hard = 1
            exam = serializer.save()
            try:
                questions = exam.generate_questions(num_easy, num_medium, num_hard)
            except ValueError as e:
                exam.delete()
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            exam.questions.set(questions)
            exam.save()
            response_serializer = self.get_serializer(exam)
            headers = self.get_success_headers(response_serializer.data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def generate_adaptive_exam(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            student_id = request.data.get('student')
            quiz_attempts = StudentQuizAttempt.objects.filter(quiz__student_id=student_id)

            if not quiz_attempts.exists():
                return Response({"detail": "No quiz attempts found for the student."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                # Create the exam
                exam = serializer.save()

                # Calculate question counts
                question_counts = self._calculate_question_counts(quiz_attempts)
                if not question_counts:
                    return Response({"detail": "No valid question counts calculated."}, status=status.HTTP_400_BAD_REQUEST)

                # Get difficulty distribution
                difficulty_distribution = self._get_difficulty_distribution()

                # Select and assign questions to the exam
                self._select_questions(exam, question_counts, difficulty_distribution)

                # Retrieve selected questions
                exam_questions = ExamQuestion.objects.filter(exam=exam)
                avg_difficulty = exam_questions.aggregate(Avg('question__difficulty'))['question__difficulty__avg']

                # Assign questions to the exam and save
                exam.questions.set([eq.question for eq in exam_questions])
                exam.save()

                # Prepare the response data
                response_data = self.get_serializer(exam).data
                response_data.update({
                    'exam_id': exam.id,
                    'status': 'Adaptive exam generated',
                    'question_distribution': question_counts,
                    'average_difficulty': avg_difficulty
                })
                headers = self.get_success_headers(response_data)
                return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

            except ValueError as e:
                exam.delete()
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _calculate_question_counts(self, quiz_attempts):
        total_lessons = quiz_attempts.values('quiz__lesson').distinct().count()
        if total_lessons == 0:
            return {}

        avg_questions_per_lesson = 100 / total_lessons
        question_counts = {}

        for attempt in quiz_attempts:
            lesson = attempt.quiz.lesson
            weight = self._get_weight(attempt.score)
            count = max(1, int(avg_questions_per_lesson * weight))
            question_counts[lesson.lesson_id] = count

        return self._adjust_question_counts(question_counts)

    def _get_weight(self, score):
        if score is None:
            score = 0  # Assign a default value if score is None
        if score < 60:
            return 1.5
        elif score < 70:
            return 1.0
        else:
            return 0.5

    def _adjust_question_counts(self, question_counts):
        total_questions = sum(question_counts.values())
        adjustment_factor = 100 / total_questions

        adjusted_counts = {lesson_id: max(1, int(count * adjustment_factor)) for lesson_id, count in question_counts.items()}

        # Ensure the total is exactly 100
        while sum(adjusted_counts.values()) != 100:
            if sum(adjusted_counts.values()) < 100:
                max_key = max(adjusted_counts, key=adjusted_counts.get)
                adjusted_counts[max_key] += 1
            else:
                min_key = min(adjusted_counts, key=adjusted_counts.get)
                adjusted_counts[min_key] -= 1

        return adjusted_counts

    def _get_difficulty_distribution(self):
        return defaultdict(lambda: {1: 0.33, 2: 0.33, 3: 0.34})

    def _select_questions(self, exam, question_counts, difficulty_distribution):
        for lesson_id, count in question_counts.items():
            lesson_questions = 0
            for difficulty, proportion in difficulty_distribution[lesson_id].items():
                diff_count = int(count * proportion)
                questions = Question.objects.filter(lesson_id=lesson_id, difficulty=difficulty).order_by('?')[:diff_count]
                for question in questions:
                    ExamQuestion.objects.create(exam=exam, question=question)
                lesson_questions += questions.count()

    @action(detail=True, methods=['post'])
    def submit_exam(self, request, pk=None):
        exam = self.get_object()
        student = request.data.get('student')
        # Process exam submission
        score = self.calculate_score(request.data['answers'])
        passed = score >= exam.passing_score
        if exam.student.user_name != student:
            return Response({"detail": "Student not authorized for this exam."}, status=status.HTTP_403_FORBIDDEN)
        
        # Create or update StudentExamAttempt
        attempt, created = StudentExamAttempt.objects.update_or_create(
            exam=exam,
            defaults={'score': score, 'passed': passed}
        )
        if not passed:
            failed_lessons = self.get_failed_lessons(request.data['answers'])
            StudentLessonProgress.objects.filter(
                student=student,
                lesson__in=failed_lessons
            ).update(is_completed=False)

        serializer = StudentExamAttemptSerializer(attempt)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def calculate_score(self, answers):
        correct_answers = sum(1 for answer in answers if answer['is_correct'])
        return correct_answers / len(answers)

    def get_failed_lessons(self, answers):
        lesson_scores = {}
        for answer in answers:
            lesson = answer['question'].lesson
            if lesson not in lesson_scores:
                lesson_scores[lesson] = {'correct': 0, 'total': 0}
            lesson_scores[lesson]['total'] += 1
            if answer['is_correct']:
                lesson_scores[lesson]['correct'] += 1

        failed_lessons = [
            lesson for lesson, scores in lesson_scores.items()
            if scores['correct'] / scores['total'] < 0.75
        ]
        return failed_lessons

    @action(detail=True, methods=['get'])
    def detailed_results(self, request, pk=None):
        exam = self.get_object()
        student = request.user.student
        attempt = StudentExamAttempt.objects.filter(exam=exam, student=student).latest('start_time')

        if not attempt:
            return Response({"detail": "No attempt found for this exam."}, status=status.HTTP_404_NOT_FOUND)

        questions = exam.questions.all()
        results = []

        for question in questions:
            answer = StudentAnswer.objects.filter(exam_attempt=attempt, question=question).first()
            question_data = QuestionSerializer(question).data
            question_data['student_answer'] = answer.selected_choice.text if answer else None
            question_data['is_correct'] = answer.is_correct if answer else False
            results.append(question_data)

        return Response({
            "exam_title": exam.title,
            "score": attempt.score,
            "total_questions": len(questions),
            "results": results
        })

    @action(detail=True, methods=['get'])
    def student_performance(self, request, pk=None):
        exam = self.get_object()
        student = request.user.student
        attempts = StudentExamAttempt.objects.filter(exam=exam, student=student)

        return Response({
            "exam_title": exam.title,
            "attempts_count": attempts.count(),
            "average_score": attempts.aggregate(Avg('score'))['score__avg'],
            "highest_score": attempts.aggregate(Max('score'))['score__max'],
            "lowest_score": attempts.aggregate(Min('score'))['score__min'],
        })

    @action(detail=True, methods=['get'])
    def overall_performance(self, request, pk=None):
        exam = self.get_object()
        attempts = StudentExamAttempt.objects.filter(exam=exam)

        return Response({
            "exam_title": exam.title,
            "total_attempts": attempts.count(),
            "average_score": attempts.aggregate(Avg('score'))['score__avg'],
            "highest_score": attempts.aggregate(Max('score'))['score__max'],
            "lowest_score": attempts.aggregate(Min('score'))['score__min'],
            "score_distribution": list(attempts.values('score').annotate(count=Count('score')).order_by('score')),
        })

    @action(detail=True, methods=['get'])
    def get_failed_lessons(self, request, pk=None):
        student_id = request.query_params.get('student_id')
        exam = self.get_object()

        attempt = StudentExamAttempt.objects.filter(student_id=student_id, exam=exam).order_by('-attempt_number').first()

        if not attempt or attempt.passed:
            return Response({"detail": "No failed lessons found."}, status=status.HTTP_404_NOT_FOUND)

        failed_lessons = attempt.failed_lessons.all()
        lesson_data = [{"lesson_id": lesson.id, "lesson_title": lesson.title} for lesson in failed_lessons]

        return Response({"failed_lessons": lesson_data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def get_exam_questions(self, request, pk=None):
        student_id = request.query_params.get('student_id')
        print(student_id)
        exam = self.get_object()
        if exam.student.user_name != student_id:
            return Response({"detail": "Student not authorized for this exam."}, status=status.HTTP_403_FORBIDDEN)
        attempt = StudentExamAttempt.objects.filter(exam=exam).order_by('-attempt_number').first()

        if not attempt:
            return Response({"detail": "No attempt found for this exam."}, status=status.HTTP_404_NOT_FOUND)

        questions = attempt.exam.questions.all()
        question_data = QuestionSerializer(questions, many=True).data

        return Response({
            "exam_title": exam.title,
            "attempt_number": attempt.attempt_number,
            "questions": question_data
        }, status=status.HTTP_200_OK)
        
    


class StudentExamAttemptViewSet(viewsets.ModelViewSet):
    queryset = StudentExamAttempt.objects.all()
    serializer_class = StudentExamAttemptSerializer

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
            score = serializer.validated_data.get('score', instance.score)

            student = instance.student
            student_name = f"{student.first_name} {student.last_name}"
            specialization_name = student.specialization.name

            correct_answers = StudentAnswer.objects.filter(student=student, exam_attempt=instance, is_correct=True)
            wrong_answers = StudentAnswer.objects.filter(student=student, exam_attempt=instance, is_correct=False)

            correct_answers_paragraph = self.create_answer_paragraph(correct_answers, "correct")
            wrong_answers_paragraph = self.create_answer_paragraph(wrong_answers, "wrong")

            feedback = self.generate_feedback(student_name, specialization_name, correct_answers_paragraph,
                                              wrong_answers_paragraph)
            serializer.save(feedback=feedback)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def create_answer_paragraph(self, answers, field):
        if answers.exists():
            paragraph = f"Here are the questions where I got the {field} answer:\n"
        else:
            paragraph = "I got all the questions wrong.\n" if field == 'wrong' else "I got all the questions correct.\n"

        for answer in answers:
            question_text = answer.question.text
            lesson = answer.question.lesson
            correct_choice = Choice.objects.filter(question=answer.question, is_correct=True).first()
            correct_answer_text = correct_choice.text if correct_choice else "Not available"
            selected_choice_text = answer.selected_choice.text
            paragraph += f"Question: {question_text}\n"
            if field == 'wrong':
                paragraph += f"Correct Answer: {correct_answer_text}"
            paragraph += f"Selected Answer: {selected_choice_text}\nLesson: {lesson}\n"
        return paragraph

    def generate_feedback(self, student_name, specialization_name, correct_answers_paragraph, wrong_answers_paragraph):
        env = environ.Env(DEBUG=(bool, False))
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        environ.Env.read_env(os.path.join(BASE_DIR, '.env'))
        client = OpenAI(api_key=env('OPENAI_API_KEY'))

        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system",
                 "content": "You are Preppy, BoardPrep's Engineering Companion and an excellent and critical engineer, tasked with providing constructive feedback on mock test performances of your students. In giving a feedback, you don't thank the student for sharing the details, instead you congratulate the student first for finishing the mock test, then you provide your feedbacks. After providing your feedbacks, you then put your signature at the end of your response"},
                {"role": "user",
                 "content": f"I am {student_name}, a {specialization_name} major, and here are the details of my test. {correct_answers_paragraph}\n\n{wrong_answers_paragraph}\n\nBased on these results, can you provide some feedback and suggestions for improvement, like what subjects to focus on, which field I excel, and some strategies? Address me directly, and don't put any placeholders as this will be displayed directly in unformatted text form."}
            ]
        )

        feedback = completion.choices[0].message.content.strip()
        return feedback

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def create_new_attempt(self, student, exam):
        last_attempt = StudentExamAttempt.objects.filter(student=student, exam=exam).order_by('-attempt_number').first()
        new_attempt_number = last_attempt.attempt_number + 1 if last_attempt else 1

        new_attempt = StudentExamAttempt.objects.create(
            student=student,
            exam=exam,
            attempt_number=new_attempt_number
        )
        return new_attempt
    
    @action(detail=False, methods=['post'])
    def retake_exam(self, request, *args, **kwargs):
        student_id = request.data.get('student_id')
        exam_id = request.data.get('exam_id')

        exam = get_object_or_404(Exam, id=exam_id)
        student = get_object_or_404(Student, id=student_id)

        last_attempt = StudentExamAttempt.objects.filter(student=student, exam=exam).order_by('-attempt_number').first()

        if last_attempt and not last_attempt.passed:
            new_attempt_number = (last_attempt.attempt_number or 0) + 1
            new_attempt = StudentExamAttempt.objects.create(
                student=student,
                exam=exam,
                attempt_number=new_attempt_number
            )
            return Response({"detail": "New exam attempt created.", "attempt_number": new_attempt.attempt_number})
        else:
            return Response({"detail": "Student has not failed any previous attempts."}, status=status.HTTP_400_BAD_REQUEST)

