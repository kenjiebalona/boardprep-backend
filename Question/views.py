from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Question, Choice, StudentAnswer
from .serializer import QuestionSerializer, ChoiceSerializer, StudentAnswerSerializer
from openai import OpenAI
import os, environ
import json


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

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
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'])
    def generate_question(self, request, *args, **kwargs):
        # Extract learning_objective and difficulty from the request body
        topic = request.data.get('topic')
        learning_objective = request.data.get('learning_objective')
        difficulty = request.data.get('difficulty')

        env = environ.Env(DEBUG=(bool, False))
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        environ.Env.read_env(os.path.join(BASE_DIR, '.env'))
        client = OpenAI(api_key=env('OPENAI_API_KEY'))

        if not learning_objective or not difficulty:
            return Response(
                {"error": "Both 'learning_objective' and 'difficulty' are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # GPT API call to generate the questions
        try:
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an AI designed to create educational questions."},
                    {"role": "user", "content": (
                        f"Generate 10 questions based on the following topic, and difficulty:\n\n"
                        f"Topic: {topic}\n"
                        f"Learning Objective: {learning_objective}\n"
                        f"Difficulty: {difficulty}.\n"
                        "The response should include multiple-choice options with one correct answer and others incorrect also the difficulty level is the equivalent : 1 = Easy , 2 = Advanced and 3 = Expert, and adhere to the following JSON format for the entire response,also dont give a code format just a text to avoid tripe ` and also just modify the format below because thats the expected output:\n\n"
                       '[{"learning_objective":"<learning_objective>","text":"<question_text>","difficulty":"<difficulty>","attachments":[],"isai":true,"choices":[{"text":"<option_1>","is_correct":true},{"text":"<option_2>","is_correct":false},{"text":"<option_3>","is_correct":false},{"text":"<option_4>","is_correct":false}]},{"learning_objective":"<learning_objective>","text":"<question_text>","difficulty":"<difficulty>","attachments":[],"isai":true,"choices":[{"text":"<option_1>","is_correct":true},{"text":"<option_2>","is_correct":false},{"text":"<option_3>","is_correct":false},{"text":"<option_4>","is_correct":false}]},{"learning_objective":"<learning_objective>","text":"<question_text>","difficulty":"<difficulty>","attachments":[],"isai":true,"choices":[{"text":"<option_1>","is_correct":true},{"text":"<option_2>","is_correct":false},{"text":"<option_3>","is_correct":false},{"text":"<option_4>","is_correct":false}]},{"learning_objective":"<learning_objective>","text":"<question_text>","difficulty":"<difficulty>","attachments":[],"isai":true,"choices":[{"text":"<option_1>","is_correct":true},{"text":"<option_2>","is_correct":false},{"text":"<option_3>","is_correct":false},{"text":"<option_4>","is_correct":false}]},{"learning_objective":"<learning_objective>","text":"<question_text>","difficulty":"<difficulty>","attachments":[],"isai":true,"choices":[{"text":"<option_1>","is_correct":true},{"text":"<option_2>","is_correct":false},{"text":"<option_3>","is_correct":false},{"text":"<option_4>","is_correct":false}]}]'
                    )}
                ]
            )

            # Extract the generated questions
            generated_questions = completion.choices[0].message.content.strip()

            return Response({
                "question": generated_questions
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to generate questions: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChoiceViewSet(viewsets.ModelViewSet):
    queryset = Choice.objects.all()
    serializer_class = ChoiceSerializer

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


class StudentAnswerViewSet(viewsets.ModelViewSet):
    queryset = StudentAnswer.objects.all()
    serializer_class = StudentAnswerSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        if isinstance(request.data, list):
            serializer = self.get_serializer(data=request.data, many=True)
        else:
            serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        serializer.save()

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
