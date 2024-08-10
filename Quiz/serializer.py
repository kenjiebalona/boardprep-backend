from rest_framework import serializers
from Question.serializer import QuestionSerializer
from User.models import Student
from .models import Quiz, StudentQuizAttempt


class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ['id', 'student', 'lesson', 'title', 'questions']


class StudentQuizAttemptSerializer(serializers.ModelSerializer):
    quiz = serializers.PrimaryKeyRelatedField(queryset=Quiz.objects.all())

    class Meta:
        model = StudentQuizAttempt
        fields = ['id', 'quiz', 'score', 'total_questions', 'start_time', 'end_time']

    def validate(self, data):
        return data
