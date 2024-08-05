from rest_framework import serializers
from Question.serializer import QuestionSerializer
from User.models import Student
from .models import Quiz, StudentQuizAttempt


class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True)

    class Meta:
        model = Quiz
        fields = ['id', 'topic', 'title', 'questions']

    def create(self, validated_data):
        questions_data = validated_data.pop('questions', [])
        quiz = Quiz.objects.create(**validated_data)
        for question_data in questions_data:
            print(question_data)
            question_serializer = QuestionSerializer(data=question_data)
            if question_serializer.is_valid():
                question_instance = question_serializer.save()
                quiz.questions.add(question_instance)
            else:
                raise serializers.ValidationError(question_serializer.errors)
        return quiz


class StudentQuizAttemptSerializer(serializers.ModelSerializer):
    quiz = serializers.PrimaryKeyRelatedField(queryset=Quiz.objects.all())
    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all())

    class Meta:
        model = StudentQuizAttempt
        fields = ['id', 'student', 'quiz', 'score', 'total_questions', 'start_time', 'end_time']

    def validate(self, data):
        return data
