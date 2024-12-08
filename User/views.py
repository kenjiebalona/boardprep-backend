from django.db import connection
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.hashers import check_password
from django.contrib.auth import login, logout
from django.contrib.sessions.models import Session
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed

from Course.models import Course, LearningObjective
from .serializers import StudentSerializer, TeacherSerializer, UserSerializer, ContentCreatorSerializer, SpecializationSerializer, StudentMasterySerializer
from .models import Student, Teacher, User, Specialization, ContentCreator, StudentMastery
import jwt, datetime

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)  # Successful creation
        return Response(serializer.errors, status=400)

class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)  # Successful creation
        return Response(serializer.errors, status=400)

class UserLogin(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        try:
            user = User.objects.get(user_name=username)
        except User.DoesNotExist:
            return Response({'message': 'Invalid Credentials'}, status=status.HTTP_404_NOT_FOUND)

        if password == user.password:
            payload = {
                'id': user.user_name,
                'type': user.user_type,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
                'iat': datetime.datetime.utcnow()
            }
            token = jwt.encode(payload, 'secret', algorithm='HS256')
            response = Response()
            response.set_cookie(key='jwt', value=token, httponly=True)
            response.data = {
                'jwt': token
            }
            return response
        else:
            return Response({'message': 'Invalid Credentials'}, status=status.HTTP_404_NOT_FOUND)

class UserLogout(APIView):
    def post(self, request):
        response = Response()
        response.delete_cookie('jwt')
        response.data = {
            'message': 'success'
        }
        return response

class StudentLogin(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        try:
            student = Student.objects.get(user_name=username)
        except Student.DoesNotExist:
            return Response({'message': 'Invalid Credentials'}, status=status.HTTP_404_NOT_FOUND)

        if password == student.password:
            response_data = {'message': 'Login Successfully', **StudentSerializer(student).data}
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'Invalid Credentials'}, status=status.HTTP_404_NOT_FOUND)

class TeacherLogin(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        try:
            teacher = Teacher.objects.get(user_name=username)
        except Teacher.DoesNotExist:
            return Response({'message': 'Invalid Credentials'}, status=status.HTTP_404_NOT_FOUND)

        if password == teacher.password:
            # Correctly combine the message and the serialized data into one response
            response_data = {'message': 'Login Successfully', **TeacherSerializer(teacher).data}
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'Invalid Credentials'}, status=status.HTTP_404_NOT_FOUND)

class StudentRegister(APIView):
    def post(self, request):
        print(request.data)
        serializer = StudentSerializer(data=request.data)
        if serializer.is_valid():
            student = serializer.save()
            payload = {
                'id': student.user_name,
                'type': 'S',
                'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
                'iat': datetime.datetime.utcnow()
            }
            token = jwt.encode(payload, 'secret', algorithm='HS256')
            response = Response()
            response.set_cookie(key='jwt', value=token, httponly=True)
            response.data = {
                'jwt': token
            }
            return response
        else:
            print(serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TeacherRegister(APIView):
    def post(self, request):
        print(request.data)
        serializer = TeacherSerializer(data=request.data)
        if serializer.is_valid():
            teacher = serializer.save()
            payload = {
                'id': teacher.user_name,
                'type': 'T',
                'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
                'iat': datetime.datetime.utcnow()
            }
            token = jwt.encode(payload, 'secret', algorithm='HS256')
            response = Response()
            response.set_cookie(key='jwt', value=token, httponly=True)
            response.data = {
                'jwt': token
            }
            return response
        else:
            print(serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserView(APIView):
    def get(self, request):
        user_id = request.query_params.get('user_id')

        try:
            user = User.objects.get(user_name=user_id)
        except User.DoesNotExist:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ContentCreatorLogin(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        try:
            content_creator = ContentCreator.objects.get(user_name=username)
        except ContentCreator.DoesNotExist:
            return Response({'message': 'Invalid Credentials'}, status=status.HTTP_404_NOT_FOUND)

        if password == content_creator.password:
            # Correctly combine the message and the serialized data into one response
            response_data = {'message': 'Login Successfully', **ContentCreatorSerializer(content_creator).data}
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'Invalid Credentials'}, status=status.HTTP_404_NOT_FOUND)

class ContentCreatorRegister(APIView):
    def post(self, request):
        print(request.data)
        serializer = ContentCreatorSerializer(data=request.data)
        if serializer.is_valid():
            content_creator = serializer.save()
            payload = {
                'id': content_creator.user_name,
                'type': 'C',
                'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
                'iat': datetime.datetime.utcnow()
            }
            token = jwt.encode(payload, 'secret', algorithm='HS256')
            response = Response()
            response.set_cookie(key='jwt', value=token, httponly=True)
            response.data = {
                'jwt': token
            }
            return response
        else:
            print(serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GetUser(APIView):
    def get(self, request):
        user_id = request.query_params.get('username')
        try:
            user = User.objects.get(user_name=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

class UpdateUser(APIView):
    def put(self, request):
        user_id = request.data.get('username')
        if user_id is None:
            return Response({"error": "Username parameter is missing"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(user_name=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=404)

class SpecializationViewSet(viewsets.ModelViewSet):
    queryset = Specialization.objects.all()
    serializer_class = SpecializationSerializer

class StudentMasteryView(viewsets.ModelViewSet):
    serializer_class = StudentMasterySerializer

    def get_queryset(self):
        student_id = self.request.query_params.get('student_id')

        if student_id:
            return StudentMastery.objects.filter(student_id=student_id)

        return StudentMastery.objects.none()
    


    def list(self, request, *args, **kwargs):
        student_id = self.request.query_params.get('student_id')
        course_id = self.request.query_params.get('course_id')

        if not student_id:
            return Response({'error': 'student_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        masteries = StudentMastery.objects.filter(student_id=student_id)
        if not masteries.exists():
            return Response({'error': 'No mastery data found for this student'}, status=status.HTTP_404_NOT_FOUND)

        if course_id:
            course = get_object_or_404(Course, course_id=course_id)
            syllabus = course.syllabus
            if not syllabus:
                return Response({'error': 'No syllabus found for this course'}, status=status.HTTP_404_NOT_FOUND)

            syllabus_data = self._build_syllabus_data(syllabus, masteries)
            return Response({
                "masteries": {
                    "course_id": course.course_id,
                    "course_mastery": self._calculate_mastery_for_course(course, masteries),
                    "course_title": course.course_title,
                    "syllabus": syllabus_data
                }
            }, status=status.HTTP_200_OK)

        serializer = self.get_serializer(masteries, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    def _build_syllabus_data(self, syllabus, masteries):
        syllabus_data = []
        for lesson in syllabus.lessons.all():
            lesson_data = {
                "lesson_id": lesson.id,
                "lesson_title": lesson.lesson_title,
                "mastery": self._calculate_mastery_for_lesson(lesson, masteries),
                "topics": []
            }

            for topic in lesson.topics.all():
                topic_data = {
                    "topic_id": topic.id,
                    "topic_title": topic.topic_title,
                    "mastery": self._calculate_mastery_for_topic(topic, masteries),
                    "subtopics": []
                }

                for subtopic in topic.subtopics.all():
                    subtopic_data = {
                        "subtopic_id": subtopic.id,
                        "subtopic_title": subtopic.subtopic_title,
                        "mastery": self._calculate_mastery_for_subtopic(subtopic, masteries),
                        "learning_objectives": []
                    }

                    for learning_objective in subtopic.learning_objectives.all():
                        mastery = masteries.filter(learning_objective=learning_objective).first()
                        lo_mastery = mastery.mastery_level if mastery else 0.0

                        learning_objective_data = {
                            "objective_id": learning_objective.id,
                            "objective_text": learning_objective.text,
                            "mastery": lo_mastery
                        }
                        subtopic_data['learning_objectives'].append(learning_objective_data)
                    topic_data['subtopics'].append(subtopic_data)
                lesson_data['topics'].append(topic_data)
            syllabus_data.append(lesson_data)
        return syllabus_data

        
    def _calculate_mastery_for_course(self, course, masteries):
        objectives = LearningObjective.objects.filter(subtopic__topic__lesson__syllabus__course=course)
        return self._calculate_mastery(objectives, masteries)

    def _calculate_mastery_for_lesson(self, lesson, masteries):
        objectives = LearningObjective.objects.filter(subtopic__topic__lesson=lesson)
        return self._calculate_mastery(objectives, masteries)

    def _calculate_mastery_for_topic(self, topic, masteries):
        objectives = LearningObjective.objects.filter(subtopic__topic=topic)
        return self._calculate_mastery(objectives, masteries)

    def _calculate_mastery_for_subtopic(self, subtopic, masteries):
        objectives = LearningObjective.objects.filter(subtopic=subtopic)
        return self._calculate_mastery(objectives, masteries)

    def _calculate_mastery(self, objectives, masteries):
        relevant_masteries = masteries.filter(learning_objective__in=objectives)
        if not relevant_masteries.exists():
            return 0.0
        total_mastery = sum(mastery.mastery_level for mastery in relevant_masteries)
        return total_mastery / relevant_masteries.count()