from rest_framework import serializers

from Class.models import Attachment
from Class.serializers import AttachmentSerializer
from Course.models import Lesson
from .models import Question, Choice, StudentAnswer


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'is_correct']


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True)
    attachments = AttachmentSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ['id', 'lesson', 'text', 'difficulty', 'choices', 'attachments']

    def create(self, validated_data):
        choices_data = validated_data.pop('choices')
        attachments_data = validated_data.pop('attachments', [])
        question = Question.objects.create(**validated_data)
        for choice_data in choices_data:
            Choice.objects.create(question=question, **choice_data)
        for attachment_data in attachments_data:
            attachment = Attachment.objects.create(**attachment_data)
            question.attachments.add(attachment)
        return question


class StudentAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAnswer
        fields = '__all__'
