from rest_framework import serializers

from Mocktest.serializer import MockQuestionsSerializer
from .models import DailyChallenge, DailyChallengeQuestion, DailyChallengeLeaderboard


class DailyChallengeQuestionSerializer(serializers.ModelSerializer):
    question = MockQuestionsSerializer()

    class Meta:
        model = DailyChallengeQuestion
        fields = ['id', 'question']


class DailyChallengeLeaderboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyChallengeLeaderboard
        fields = '__all__'


class DailyChallengeSerializer(serializers.ModelSerializer):
    daily_challenge_questions = DailyChallengeQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = DailyChallenge
        fields = ['challengeID', 'date', 'daily_challenge_questions']
