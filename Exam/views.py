from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response

from Question.models import StudentAnswer, Choice
from .models import Exam, StudentExamAttempt
from .serializer import ExamSerializer, StudentExamAttemptSerializer
from openai import OpenAI
import os, environ


# Create your views here.
class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer

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
        if answers.__len__() > 0:
            paragraph = f"Here are the questions where I got the {field} answer:\n"
        else:
            if field == 'correct':
                paragraph = "I got all the questions wrong.\n"
            else:
                paragraph = "I got all the questions correct.\n"
        for answer in answers:
            question_text = answer.question.text
            topic = answer.question.topic
            correct_choice = Choice.objects.filter(question=answer.question, is_correct=True).first()
            correct_answer_text = correct_choice.text if correct_choice else "Not available"
            selected_choice_text = answer.selected_choice.text
            paragraph += f"Question: {question_text}\n"
            if field == 'wrong':
                paragraph += f"Correct Answer: {correct_answer_text}"
            paragraph += f"Selected Answer: {selected_choice_text}\nTopic: {topic}\n"
        return paragraph

    def generate_feedback(self, student_name, specialization_name, correct_answers_paragraph, wrong_answers_paragraph):
        env = environ.Env(DEBUG=(bool, False))
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        environ.Env.read_env(os.path.join(BASE_DIR, '.env'))
        client = OpenAI(
            api_key=env('OPENAI_API_KEY'),
        )

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
