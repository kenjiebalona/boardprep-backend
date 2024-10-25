from rest_framework import serializers
from .models import Question, Choice, StudentAnswer


class ChoiceSerializer(serializers.ModelSerializer):
    is_correct = serializers.BooleanField(write_only=True)

    class Meta:
        model = Choice
        fields = ['id', 'text', 'is_correct']

    def __init__(self, *args, **kwargs):
        super(ChoiceSerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.method in ['GET']:
            self.fields.pop('is_correct')


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'choices']

    def create(self, validated_data):
        choices_data = validated_data.pop('choices')
        question = Question.objects.create(**validated_data)
        for choice_data in choices_data:
            Choice.objects.create(question=question, **choice_data)
        return question

    def update(self, instance, validated_data):
        choices_data = validated_data.pop('choices', None)
        instance.text = validated_data.get('text', instance.text)
        instance.save()

        if choices_data is not None:
            existing_choice_ids = {choice.id for choice in instance.choices.all()}
            new_choice_ids = set()

            for choice_data in choices_data:
                choice_id = choice_data.get('id')
                if choice_id and choice_id in existing_choice_ids:
                    choice = Choice.objects.get(id=choice_id, question=instance)
                    choice.text = choice_data.get('text', choice.text)
                    choice.is_correct = choice_data.get('is_correct', choice.is_correct)
                    choice.save()
                    new_choice_ids.add(choice_id)
                elif not choice_id:
                    new_choice = Choice.objects.create(question=instance, **choice_data)
                    new_choice_ids.add(new_choice.id)

            for choice_id in existing_choice_ids - new_choice_ids:
                Choice.objects.filter(id=choice_id, question=instance).delete()

        return instance


class StudentAnswerSerializer(serializers.ModelSerializer):
    is_correct = serializers.BooleanField(read_only=True)

    class Meta:
        model = StudentAnswer
        fields = '__all__'

    def create(self, validated_data):
        selected_choice = validated_data.get('selected_choice')
        question = validated_data.get('question')
        is_correct = selected_choice.is_correct
        student_answer = StudentAnswer.objects.create(is_correct=is_correct, **validated_data)
        return student_answer
