from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from User.models import User, Student
from .models import DailyChallenge, DailyChallengeQuestion, DailyChallengeLeaderboard
from .serializer import DailyChallengeSerializer, DailyChallengeQuestionSerializer, DailyChallengeLeaderboardSerializer


class DailyChallengeViewSet(viewsets.ModelViewSet):
    queryset = DailyChallenge.objects.all()
    serializer_class = DailyChallengeSerializer

    @action(detail=False, methods=['get'])
    def get_today_challenge(self, request):
        today = timezone.now().date()
        daily_challenge, created = DailyChallenge.objects.get_or_create(date=today)
        if created:
            daily_challenge.generate_challenge(num_easy=5, num_medium=3, num_hard=2)

        serializer = self.get_serializer(daily_challenge)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def submit_challenge(self, request):
        student_id = request.data.get('student')
        challenge_id = request.data.get('challenge')
        answers = request.data.get('answers')

        try:
            daily_challenge = DailyChallenge.objects.get(challengeID=challenge_id)
            student = Student.objects.get(user_ptr_id=student_id)

            correct_answers = 0
            total_questions = 0

            # Calculate the score
            for answer_data in answers:
                question_id = answer_data.get('question_id')
                answer = answer_data.get('answer')

                try:
                    question = DailyChallengeQuestion.objects.get(id=question_id, daily_challenge=daily_challenge)
                    mock_question = question.question
                    if mock_question.correctAnswer == answer:
                        correct_answers += 1
                    total_questions += 1
                except DailyChallengeQuestion.DoesNotExist:
                    continue

            completion_time = timezone.now()

            DailyChallengeLeaderboard.objects.create(
                daily_challenge=daily_challenge,
                student=student,
                score=correct_answers,
                completion_time=completion_time,
                totalQuestions=total_questions
            )
            return Response({"status": "success", "score": correct_answers}, status=status.HTTP_201_CREATED)
        except DailyChallenge.DoesNotExist:
            return Response({"error": "DailyChallenge not found"}, status=status.HTTP_404_NOT_FOUND)
        except User.DoesNotExist:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DailyChallengeQuestionViewSet(viewsets.ModelViewSet):
    queryset = DailyChallengeQuestion.objects.all()
    serializer_class = DailyChallengeQuestionSerializer


class DailyChallengeLeaderboardViewSet(viewsets.ModelViewSet):
    queryset = DailyChallengeLeaderboard.objects.all()
    serializer_class = DailyChallengeLeaderboardSerializer
