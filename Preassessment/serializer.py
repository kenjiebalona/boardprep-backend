from rest_framework import serializers

from Question.serializer import QuestionSerializer
from .models import Preassessment, StudentPreassessmentAttempt


class PreassessmentSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True)

    class Meta:
        model = Preassessment
        fields = '__all__'


class StudentPreassessmentAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentPreassessmentAttempt
        fields = '__all__'
