from rest_framework import serializers
from Question.serializer import QuestionSerializer
from User.models import Student
from .models import Exam, StudentExamAttempt


class ExamSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True)

    class Meta:
        model = Exam
        fields = ['id', 'classID', 'course', 'title', 'questions']

    def create(self, validated_data):
        questions_data = validated_data.pop('questions', [])
        exam = Exam.objects.create(**validated_data)
        for question_data in questions_data:
            question_serializer = QuestionSerializer(data=question_data)
            if question_serializer.is_valid():
                question_instance = question_serializer.save()
                exam.questions.add(question_instance)
            else:
                raise serializers.ValidationError(question_serializer.errors)
        return exam


class StudentExamAttemptSerializer(serializers.ModelSerializer):
    exam = serializers.PrimaryKeyRelatedField(queryset=Exam.objects.all())
    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all())

    class Meta:
        model = StudentExamAttempt
        fields = ['id', 'student', 'exam', 'score', 'feedback', 'total_questions', 'start_time', 'end_time']
