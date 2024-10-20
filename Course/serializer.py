from bs4 import BeautifulSoup
from django.conf import settings
from rest_framework import serializers

from Quiz.models import Quiz
from .models import Course, StudentCourseProgress, StudentLessonProgress, Syllabus, Lesson, Page, Topic, Subtopic, ContentBlock,FileUpload
from Exam.models import Exam
from datetime import datetime
import time

class ContentBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentBlock
        fields = '__all__'

class PageSerializer(serializers.ModelSerializer):
    content_blocks = ContentBlockSerializer(many=True, read_only=True)
    class Meta:
        model = Page
        fields = ['subtopic', 'page_number', 'content_blocks']
        
class SubtopicSerializer(serializers.ModelSerializer):
    pages = PageSerializer(many=True, read_only=True)

    class Meta:
        model = Subtopic
        fields = ['topic', 'subtopic_title', 'order', 'pages']


class TopicSerializer(serializers.ModelSerializer):
    subtopics = SubtopicSerializer(many=True, read_only=True)

    class Meta:
        model = Topic
        fields = ['lesson', 'topic_title', 'order', 'learning_objectives', 'skills_to_acquire', 'subtopics']


class LessonSerializer(serializers.ModelSerializer):
    topics = TopicSerializer(many=True, read_only=True)

    class Meta:
        model = Lesson
        fields = ['syllabus',  'lesson_title', 'order', 'learning_objectives', 'skills_to_acquire', 'topics']
        
class FileUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileUpload
        fields = ['file', 'uploaded_at']
        
class SyllabusSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Syllabus
        fields = '__all__'

    def create(self, validated_data):
        course = Course.objects.create(**validated_data)
        syllabus_id = generate_syllabus_id(course) 
        Syllabus.objects.create(course=course, syllabus_id=syllabus_id)
        return course

def generate_syllabus_id(course):
    timestamp = datetime.now().strftime("%H%M%S") 
    syllabus_id = (course.course_id[:4] + timestamp)[:10]  
    return syllabus_id

class CourseDetailSerializer(serializers.ModelSerializer):
    syllabus = SyllabusSerializer(read_only=True)

    class Meta:
        model = Course
        fields = '__all__'

    def create(self, validated_data):
        course = Course.objects.create(**validated_data)
        syllabus_id = generate_syllabus_id(course)  # Use the function
        Syllabus.objects.create(course=course, syllabus_id=syllabus_id)
        return course

class StudentLessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentLessonProgress
        fields = ['id', 'student', 'lesson', 'is_completed']

class StudentCourseProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentCourseProgress
        fields = ['id', 'student', 'course', 'is_completed', 'completion_date']

class CourseListSerializer(serializers.ModelSerializer):
    syllabus = SyllabusSerializer(read_only=True)

    class Meta:
        model = Course
        fields = ['course_id', 'course_title', 'short_description', 'image', 'syllabus', 'is_published']

    def create(self, validated_data):
        course = Course.objects.create(**validated_data)
        syllabus_id = generate_syllabus_id(course)  # Use the function
        Syllabus.objects.create(course=course, syllabus_id=syllabus_id)
        return course