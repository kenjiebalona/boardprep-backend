from collections import defaultdict
from django.utils import timezone
from django.shortcuts import get_object_or_404, render
from Course.models import Lesson, StudentLessonProgress
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request

from Question.models import Question, StudentAnswer, Choice
from Question.serializer import QuestionSerializer
from Quiz.models import StudentQuizAttempt
from User.models import Student, StudentMastery
from .models import Exam, ExamQuestion, StudentExamAttempt
from .serializer import ExamSerializer, StudentExamAttemptSerializer
from openai import OpenAI
import os, environ
from django.db.models import Avg, Max, Min, Count
import random



class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            num_easy = 20  # Example hardcoded values
            num_medium = 20
            num_hard = 10
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
                exam = serializer.save()
                question_counts = self._calculate_question_counts(quiz_attempts)
                if not question_counts:
                    return Response({"detail": "No valid question counts calculated."}, status=status.HTTP_400_BAD_REQUEST)
                difficulty_distribution = self._get_difficulty_distribution()
                attempt_number =  1
                selected_questions = self._select_questions(exam, question_counts, difficulty_distribution)
                total_questions = len(selected_questions)
                attempt = StudentExamAttempt.objects.create(
                    exam=exam,
                    attempt_number=attempt_number,
                    total_questions=total_questions
                )
                for question in selected_questions:
                    ExamQuestion.objects.create(exam=exam, question=question, attempt=attempt)
                exam_questions = ExamQuestion.objects.filter(exam=exam)
                avg_difficulty = exam_questions.aggregate(Avg('question__difficulty'))['question__difficulty__avg']
                exam.questions.set([eq.question for eq in exam_questions])
                print("Exam questions: ", exam.questions)
                exam.save()
                response_data = self.get_serializer(exam).data
                response_data.update({
                    'status': 'Adaptive exam generated',
                    'attempt_number': attempt_number,
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

        avg_questions_per_lesson = 25/ total_lessons
        question_counts = {
            24: 4,
            25: 4,
            26: 4,
            27: 4,
            28: 4,
        }

        # for attempt in quiz_attempts:
        #     lesson = attempt.quiz.lesson
        #     weight = self._get_weight(attempt.score)
        #     count = max(1, int(avg_questions_per_lesson * weight))
        #     question_counts[lesson.id] = count

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
        print(f"Total questions before adjustment: {total_questions}")  # Debug statement
        adjustment_factor = 25 / total_questions

        adjusted_counts = {learning_objective_id: max(1, int(count * adjustment_factor)) for learning_objective_id, count in question_counts.items()}

        print(f"Adjusted question counts: {adjusted_counts}")  # Debug statement

        while sum(adjusted_counts.values()) != 25:
            if sum(adjusted_counts.values()) < 25:
                max_key = max(adjusted_counts, key=adjusted_counts.get)
                adjusted_counts[max_key] += 1
            else:
                min_key = min(adjusted_counts, key=adjusted_counts.get)
                adjusted_counts[min_key] -= 1

        print(f"Total questions after adjustment: {sum(adjusted_counts.values())}")  # Debug statement

        return adjusted_counts


    def _get_difficulty_distribution(self):
        return defaultdict(lambda: {1: 0.33, 2: 0.33, 3: 0.34})

    def _select_questions(self, exam, question_counts, difficulty_distribution):
        selected_questions = []
        for learning_objective_id, count in question_counts.items():
            print(f"Selecting questions for learning objective: {learning_objective_id}")  # Debug print
            for difficulty, proportion in difficulty_distribution[learning_objective_id].items():
                diff_count = int(count * proportion)
                questions = Question.objects.filter(learning_objective_id=learning_objective_id, difficulty=difficulty).order_by('?')[:diff_count]
                selected_questions.extend(questions)
        return selected_questions

    def submit_exam(self, request, pk=None):
        exam = self.get_object()
        student = exam.student
        student_id = request.data.get('student_id')
        attempt_number = request.data.get('attempt_number')
        if exam.student.user_name != student_id:
            return Response({"detail": "Student not authorized for this exam."}, status=status.HTTP_403_FORBIDDEN)

        attempt = StudentExamAttempt.objects.filter(
        exam=exam,
        attempt_number=attempt_number
        ).first()


        if not attempt:
            return Response({"detail": "Invalid attempt."}, status=status.HTTP_400_BAD_REQUEST)

        if attempt.end_time:
            attempt = StudentExamAttempt.objects.create(
                exam=attempt.exam,
                attempt_number=attempt.attempt_number + 1,
                total_questions=attempt.total_questions
            )
            print(attempt.attempt_number + 1)  # Debug print
            # return Response({"detail": "This attempt has already been submitted."}, status=status.HTTP_400_BAD_REQUEST)

        # if attempt:
        #     attempt = StudentExamAttempt.objects.create(
        #         exam=attempt.exam,
        #         attempt_number=attempt.attempt_number + 1,
        #         total_questions=attempt.total_questions
        #     )

        score = self.calculate_score(request.data['answers'], exam, attempt)
        passed = (score / attempt.total_questions) >= exam.passing_score

        attempt.score = score
        attempt.passed = passed
        attempt.end_time = timezone.now()

        feedback = StudentExamAttemptViewSet().generate_feedback(attempt)
        attempt.feedback = feedback
        attempt.save()
        analytics = StudentExamAttemptViewSet().generate_analytics(attempt)

        if not passed:
            failed_learning_objectives = self.calculate_failed_subtopics(request.data['answers'])
            failed_learning_objective_ids = [learning_objective.id for learning_objective in failed_learning_objectives]
            attempt.failed_lessons.set(failed_learning_objective_ids)
            StudentLessonProgress.objects.filter(
                student=student,
                lesson__in=failed_learning_objective_ids
            ).update(is_completed=False)

            print(f"Failed learning_objectives set: {failed_learning_objectives}")  # Debug print

        return Response({
            "detail": "Exam submitted successfully.",
            "score": score,
            "passed": passed,
            "feedback": feedback,
            "analytics": analytics
        })

    def calculate_score(self, answers, exam, attempt):
        correct_answers = 0
        for answer in answers:
            question_id = answer.get('question_id')
            selected_choice_id = answer.get('selected_choice_id')
            try:
                question = Question.objects.get(id=question_id)
                correct_choice = Choice.objects.get(question=question, is_correct=True)
                is_correct = (selected_choice_id == correct_choice.id)
                if is_correct:
                    correct_answers += 1
                StudentAnswer.objects.update_or_create(
                    exam_attempt=attempt,
                    question=question,
                    selected_choice_id=selected_choice_id,
                    is_correct=is_correct,
                    student=exam.student
                )
            except Question.DoesNotExist:
                continue
            except Choice.DoesNotExist:
                continue

        answers = StudentAnswer.objects.filter(exam_attempt=attempt)

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
            student_mastery, created = StudentMastery.objects.get_or_create(student=attempt.exam.student, learning_objective=learning_objective)
            student_mastery.update_mastery(answers)

        return correct_answers

    def calculate_failed_subtopics(self, answers):
        learning_objective_scores = {}
        for answer in answers:
            question_id = answer.get('question_id')
            if not question_id:
                continue
            try:
                question = Question.objects.get(id=question_id)
                learning_objective = question.learning_objective
            except Question.DoesNotExist:
                continue

            if learning_objective not in learning_objective_scores:
                learning_objective_scores[learning_objective] = {'correct': 0, 'total': 0}
            learning_objective_scores[learning_objective]['total'] += 1
            if answer.get('is_correct'):
                learning_objective_scores[learning_objective]['correct'] += 1

        failed_learning_objectives = [
            learning_objective for learning_objective, scores in learning_objective_scores.items()
            if scores['correct'] / scores['total'] < 0.75
        ]

        return failed_learning_objectives

    @action(detail=True, methods=['get'])
    def detailed_results(self, request, pk=None):
        exam = self.get_object()
        student_id = request.query_params.get('student_id')
        attempt_number = request.query_params.get('attempt_number')
        if exam.student.user_name != student_id:
            return Response({"detail": "Student not authorized for this exam."}, status=status.HTTP_403_FORBIDDEN)
        if attempt_number is None:
            return Response({"detail": "Attempt number must be provided."}, status=status.HTTP_400_BAD_REQUEST)

        attempt = StudentExamAttempt.objects.filter(exam=exam, attempt_number=attempt_number).first()
        questions = exam.questions.all()
        results = []

        for question in questions:
            answer = StudentAnswer.objects.filter(exam_attempt=attempt, question=question).first()
            question_data = QuestionSerializer(question).data
            question_data['student_answer'] = answer.selected_choice.text if answer else None
            question_data['is_correct'] = answer.is_correct if answer else False
            results.append(question_data)

        feedback = attempt.feedback

        return Response({
            "exam_title": exam.title,
            "score": attempt.score,
            "total_questions": len(questions),
            "results": results,
            "feedback": feedback
        })

    @action(detail=True, methods=['get'])
    def student_performance(self, request, pk=None):
        exam = self.get_object()
        student_id = request.query_params.get('student_id')
        if exam.student.user_name != student_id:
            return Response({"detail": "Student not authorized for this exam."}, status=status.HTTP_403_FORBIDDEN)
        attempts = StudentExamAttempt.objects.filter(exam=exam)
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
        exam = self.get_object()
        student_id = request.query_params.get('student_id')
        if exam.student.user_name != student_id:
            return Response({"detail": "Student not authorized for this exam."}, status=status.HTTP_403_FORBIDDEN)
        attempt = StudentExamAttempt.objects.filter(exam=exam).order_by('-attempt_number').last()

        if not attempt or attempt.passed:
            return Response({"detail": "No failed learning_objectives found."}, status=status.HTTP_404_NOT_FOUND)

        failed_learning_objectives = attempt.failed_lessons.all()
        learning_objective_data = [{"learning_objective_id": learning_objective.learning_objective_id, "learning_objective_title": learning_objective.learning_objective_title} for learning_objective in failed_learning_objectives]

        return Response({"failed_learning_objectives": learning_objective_data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def get_exam_questions(self, request, pk=None):
        student_id = request.query_params.get('student_id')
        attempt_number = request.query_params.get('attempt_number')
        print(student_id)
        exam = self.get_object()
        if exam.student.user_name != student_id:
            return Response({"detail": "Student not authorized for this exam."}, status=status.HTTP_403_FORBIDDEN)
        attempt = StudentExamAttempt.objects.filter(
            exam=exam,
            attempt_number=attempt_number
        ).first()
        if not attempt:
            return Response({"detail": "No attempt found for this exam."}, status=status.HTTP_404_NOT_FOUND)
        exam_questions = ExamQuestion.objects.filter(exam=exam, attempt=attempt)
        question_data = QuestionSerializer([eq.question for eq in exam_questions], many=True).data
        return Response({
            "exam_title": exam.title,
            "attempt_number": attempt.attempt_number,
            "questions": question_data,
            "total_questions": len(question_data)
        }, status=status.HTTP_200_OK)

    def generate_questions_for_attempt(self, exam, student, attempt_number):
        questions = []
        failed_learning_objectives = []

        if attempt_number > 1:
            previous_attempt = StudentExamAttempt.objects.filter(
                exam=exam,
                attempt_number=attempt_number-1
            ).first()
            if previous_attempt:
                failed_learning_objectives = previous_attempt.failed_lessons.all()

        available_questions = Question.objects.filter(learning_objective__syllabus__course=exam.course)
        difficulty_distribution = self._get_difficulty_distribution()

        total_learning_objectives = Lesson.objects.filter(syllabus__course=exam.course).count()
        questions_per_learning_objective = 25 // total_learning_objectives

        for learning_objective in failed_learning_objectives:
            learning_objective_questions = self._select_questions_for_learning_objective(
                learning_objective.learning_objective_id, questions_per_learning_objective, difficulty_distribution,
                available_questions.filter(learning_objective=learning_objective)
            )
            questions.extend(learning_objective_questions)

        remaining_count = 35 - len(questions)
        other_learning_objectives = Lesson.objects.filter(syllabus__course=exam.course).exclude(lesson_id__in=[lesson.lesson_id for lesson in failed_learning_objectives])
        for learning_objective in other_learning_objectives:
            if len(questions) >= 35:
                break
            count = min(questions_per_learning_objective, remaining_count)
            learning_objective_questions = self._select_questions_for_learning_objective(
                learning_objective.lesson_id, count, difficulty_distribution,
                available_questions.filter(learning_objective=learning_objective)
            )
            questions.extend(learning_objective_questions)

        questions = questions[:35]
        random.shuffle(questions)
        return questions

    def _select_questions_for_lesson(self, learning_objective_id, count, difficulty_distribution, question_queryset):
        selected_questions = []
        for difficulty, proportion in difficulty_distribution[learning_objective_id].items():
            diff_count = int(count * proportion)
            questions = question_queryset.filter(difficulty=difficulty).order_by('?')[:diff_count]
            selected_questions.extend(questions)
        return selected_questions[:count]

    def _get_difficulty_distribution(self):
        return defaultdict(lambda: {1: 0.3, 2: 0.4, 3: 0.3})

    @action(detail=False, methods=['get'])
    def get_student_exam_info(self, request, *args, **kwargs):
        student_id = request.query_params.get('student_id')
        class_instance_id = request.query_params.get('class_instance_id')
        course_id = request.query_params.get('course_id')

        if not student_id or not class_instance_id or not course_id:
            return Response({"detail": "Missing required parameters."}, status=status.HTTP_400_BAD_REQUEST)

        student = get_object_or_404(Student, user_name=student_id)
        exams = Exam.objects.filter(student=student, course_id=course_id, class_instance_id=class_instance_id)

        exam_data = []
        for exam in exams:
            last_attempt = StudentExamAttempt.objects.filter(exam=exam).order_by('-attempt_number').first()
            if last_attempt:
                exam_info = {
                    "exam_id": exam.id,
                    "current_score": last_attempt.score,
                    "passed": last_attempt.passed,
                    "current_attempt": last_attempt.attempt_number,
                    "current_feedback": last_attempt.feedback,
                }
                exam_data.append(exam_info)

        return Response({
            "student_id": student_id,
            "class_instance_id": class_instance_id,
            "course_id": course_id,
            "exams": exam_data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='current-attempt-number')
    def get_current_attempt_number(self, request, pk=None):
        exam = self.get_object()
        student_id = request.query_params.get('student_id')

        if not student_id:
            return Response({"detail": "Student ID must be provided."}, status=status.HTTP_400_BAD_REQUEST)

        last_attempt = StudentExamAttempt.objects.filter(exam=exam).order_by('-attempt_number').first()
        if last_attempt:
              next_attempt_number = last_attempt.attempt_number + 1
              last_attempt_serialized = StudentExamAttemptSerializer(last_attempt).data
        else:
            next_attempt_number = 1
            last_attempt_serialized = None

        return Response({"exam_id": exam.id, "student_id": student_id, "last_attempt": last_attempt_serialized, "next_attempt_number": next_attempt_number}, status=status.HTTP_200_OK)



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

            feedback = self.generate_feedback(student_name, specialization_name, correct_answers_paragraph,wrong_answers_paragraph)

            # Save the instance along with the generated feedback
            serializer.save(feedback=feedback)
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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

        student = attempt.exam.student
        student_name = f"{student.first_name} {student.last_name}"
        specialization_name = student.specialization.name

        correct_answers = StudentAnswer.objects.filter(exam_attempt=attempt, is_correct=True)
        wrong_answers = StudentAnswer.objects.filter(exam_attempt=attempt, is_correct=False)

        print(correct_answers)
        print(wrong_answers)

        answers_paragraph = self.create_answer_paragraph(correct_answers, wrong_answers)
        print(answers_paragraph)

        total_questions = attempt.total_questions
        correct_count = correct_answers.count()
        score_percentage = (attempt.score / total_questions) * 100 if total_questions > 0 else 0

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
                {"role": "system", "content": "You are Preppy, BoardPrep's Engineering Companion and an excellent and critical engineer, tasked with providing constructive feedback on exam performances of your students. In giving feedback, you don't thank the student for sharing the details, instead you congratulate the student first for finishing the exam, then you provide your feedbacks. Be critical about your feedback expecially if the student failed the exam so that they will know more where and how to improve. After providing your feedbacks, you then put your signature at the end of your response"},
                {"role": "user", "content": f"I am {student_name}, a {specialization_name} major, and here are the details of my test. Score: {attempt.score}, Total Questions: {total_questions}, Perecentage: {score_percentage:.2f}%), Passed: {attempt.passed}\n\n{answers_paragraph}\n\nHere's an initial assessment of your performance:\n\n{score_feedback}\n\nBased on these results, can you provide some detailed feedback and suggestions for improvement if needed, like what subjects to focus on, which field I excel in, and some strategies? Address me directly, and don't put any placeholders as this will be displayed directly in unformatted text form."}
            ]
        )

        print(completion)

        ai_feedback = completion.choices[0].message.content.strip()
        final_feedback = f"{ai_feedback}\n\nAdditional Performance Summary:\n{score_feedback}"
        print(f"Feedback generated: {final_feedback[:100]}...")
        return final_feedback

    def generate_analytics(self, attempt):
        print("Starting analytics generation")

        correct_answers = StudentAnswer.objects.filter(exam_attempt=attempt, is_correct=True)
        wrong_answers = StudentAnswer.objects.filter(exam_attempt=attempt, is_correct=False)

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

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def create_new_attempt(self, student, exam):
        last_attempt = StudentExamAttempt.objects.filter(exam=exam).order_by('-attempt_number').first()
        new_attempt_number = last_attempt.attempt_number + 1 if last_attempt else 1

        exam_viewset = ExamViewSet()
        questions = exam_viewset.generate_questions_for_attempt(exam, student, new_attempt_number)
        new_attempt = StudentExamAttempt.objects.create(
            exam=exam,
            attempt_number=new_attempt_number,
            total_questions=len(questions)
        )
        for order, question in enumerate(questions, start=1):
            ExamQuestion.objects.create(
                exam=exam,
                question=question,
                order=order,
                attempt=new_attempt
            )
        return new_attempt

    @action(detail=False, methods=['post'])
    def retake_exam(self, request, *args, **kwargs):
        student_id = request.data.get('student_id')
        exam_id = request.data.get('exam_id')
        exam = get_object_or_404(Exam, id=exam_id)
        if not isinstance(exam, Exam):
            return Response({"detail": "Invalid exam object."}, status=status.HTTP_400_BAD_REQUEST)

        if exam.student.user_name != student_id:
            return Response({"detail": "Student not authorized for this exam."}, status=status.HTTP_403_FORBIDDEN)

        new_attempt = self.create_new_attempt(exam.student, exam, )
        exam_questions = ExamQuestion.objects.filter(attempt=new_attempt)
        question_data = QuestionSerializer([eq.question for eq in exam_questions], many=True).data
        return Response({
            "attempt_number": new_attempt.attempt_number,
            "total_questions": len(question_data),
            "questions": question_data,
            "status": "New exam attempt created."
        }, status=status.HTTP_201_CREATED)
