from rest_framework import serializers
from Question.serializer import QuestionSerializer
from User.models import Student
from .models import Exam, StudentExamAttempt


class ExamSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Exam
        fields = ['id', 'student', 'class_instance', 'course', 'title', 'questions']


class StudentExamAttemptSerializer(serializers.ModelSerializer):
    exam = serializers.PrimaryKeyRelatedField(queryset=Exam.objects.all())

    class Meta:
        model = StudentExamAttempt
        fields = '__all__' 
