from rest_framework import serializers

from Question.serializer import QuestionSerializer
from .models import Mocktest, StudentMocktesttAttempt


class MocktestSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True)

    class Meta:
        model = Mocktest
        fields = '__all__'


class StudentMocktestAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentMocktesttAttempt
        fields = '__all__'
