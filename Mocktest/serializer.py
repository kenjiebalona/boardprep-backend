from rest_framework import serializers

from Question.serializer import QuestionSerializer
from .models import Mocktest, StudentMocktestAttempt, MocktestSetQuestion, MocktestQuestion


class MocktestSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True)

    class Meta:
        model = Mocktest
        fields = '__all__'


class StudentMocktestAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentMocktestAttempt
        fields = '__all__'

class MocktestSetQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MocktestSetQuestion
        fields = '__all__'

    def update(self, instance, validated_data):
        # Update each field of the existing instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

class MocktestQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MocktestQuestion
        fields = '__all__'