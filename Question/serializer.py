from rest_framework import serializers

from Course.models import Lesson
from .models import Question, Choice, StudentAnswer


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'is_correct']


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True)
    topic = serializers.CharField()

    class Meta:
        model = Question
        fields = ['id', 'topic', 'text', 'difficulty', 'choices']

    def create(self, validated_data):
        choices_data = validated_data.pop('choices', [])
        topic_id = validated_data.pop('topic', None)

        if not topic_id:
            raise serializers.ValidationError({"topic": "This field is required."})

        try:
            topic_instance = Lesson.objects.get(lesson_id=topic_id)
        except Lesson.DoesNotExist:
            raise serializers.ValidationError({"topic": "Invalid Lesson ID"})

        question = Question.objects.create(topic=topic_instance, **validated_data)

        for choice_data in choices_data:
            Choice.objects.create(question=question, **choice_data)

        return question


class StudentAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAnswer
        fields = '__all__'
