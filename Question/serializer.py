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
        choices_data = validated_data.pop('choices', [])
        attachments_data = validated_data.pop('attachments', [])
        question = Question.objects.create(**validated_data)

        for choice_data in choices_data:
            Choice.objects.create(question=question, **choice_data)

        for attachment_data in attachments_data:
            attachment = Attachment.objects.create(**attachment_data)
            question.attachments.add(attachment)

        return question

    def update(self, instance, validated_data):
        choices_data = validated_data.pop('choices', [])
        attachments_data = validated_data.pop('attachments', [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if choices_data:
            instance.choices.all().delete()
            for choice_data in choices_data:
                Choice.objects.create(question=instance, **choice_data)

        if attachments_data:
            instance.attachments.clear()
            for attachment_data in attachments_data:
                attachment = Attachment.objects.create(**attachment_data)
                instance.attachments.add(attachment)

        return instance


class StudentAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAnswer
        fields = '__all__'
