from rest_framework import serializers
from Question.serializer import QuestionSerializer
from User.models import Student
from .models import Exam, StudentExamAttempt


class ExamSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Exam
        fields = ['id', 'classID', 'course', 'title', 'questions']


class StudentExamAttemptSerializer(serializers.ModelSerializer):
    exam = serializers.PrimaryKeyRelatedField(queryset=Exam.objects.all())
    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all())

    class Meta:
        model = StudentExamAttempt
        fields = ['id', 'student', 'exam', 'score', 'feedback', 'total_questions', 'start_time', 'end_time']
