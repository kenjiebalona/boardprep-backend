from rest_framework import serializers

from Question.serializer import QuestionSerializer
from .models import Challenge, StudentChallengeAttempt


class ChallengeSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True)

    class Meta:
        model = Challenge
        fields = '__all__'


class StudentChallengeAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentChallengeAttempt
        fields = '__all__'
