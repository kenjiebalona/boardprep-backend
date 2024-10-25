from bs4 import BeautifulSoup
from django.conf import settings
from rest_framework import serializers

from Quiz.models import Quiz
from .models import Course, StudentCourseProgress, StudentLessonProgress, Syllabus, Lesson, Page, Topic, Subtopic, ContentBlock,FileUpload
from Exam.models import Exam
from datetime import datetime
import time

from User.models import Specialization

class ContentBlockSerializer(serializers.ModelSerializer):
    block_id = serializers.ReadOnlyField(source='id')
    class Meta:
        model = ContentBlock
        fields = ['block_id', 'block_type', 'difficulty', 'content', 'file', 'page'] 
    
    def create(self, validated_data):
        return ContentBlock.objects.create(**validated_data)

class PageSerializer(serializers.ModelSerializer):
    page_id = serializers.ReadOnlyField(source='id')
    content_blocks = ContentBlockSerializer(many=True, read_only=True)
    class Meta:
        model = Page
        fields = ['subtopic', 'page_id', 'page_number', 'content_blocks']
    
    def create(self, validated_data):
        content_blocks_data = validated_data.pop('content_blocks', [])
        page = Page.objects.create(**validated_data)
        
        for block_data in content_blocks_data:
            ContentBlock.objects.create(page=page, **block_data)
        
        return page
    
    def update(self, instance, validated_data):
        content_blocks_data = validated_data.pop('content_blocks', [])
        instance.subtopic = validated_data.get('subtopic', instance.subtopic)
        instance.page_number = validated_data.get('page_number', instance.page_number)
        instance.save()

        for block_data in content_blocks_data:
            block_id = block_data.get('block_id')
            if block_id:
                content_block = ContentBlock.objects.get(id=block_id, page=instance)
                for attr, value in block_data.items():
                    setattr(content_block, attr, value)
                content_block.save()
            else:
                ContentBlock.objects.create(page=instance, **block_data)
        
        return instance
        
class SubtopicSerializer(serializers.ModelSerializer):
    pages = PageSerializer(many=True, read_only=True)
    subtopic_id = serializers.ReadOnlyField(source='id')

    class Meta:
        model = Subtopic
        fields = ['topic', 'subtopic_id', 'subtopic_title', 'order', 'pages']


class TopicSerializer(serializers.ModelSerializer):
    subtopics = SubtopicSerializer(many=True, read_only=True)
    topic_id = serializers.ReadOnlyField(source='id')

    class Meta:
        model = Topic
        fields = ['lesson', 'topic_id', 'topic_title', 'order', 'learning_objectives', 'skills_to_acquire', 'subtopics']


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

class CourseSerializer(serializers.ModelSerializer):
    syllabus = SyllabusSerializer(read_only=True)
    specializations = serializers.PrimaryKeyRelatedField(
        queryset=Specialization.objects.all(), many=True
    )

    class Meta:
        model = Course
        fields = [
            'course_id', 
            'course_title', 
            'short_description', 
            'image', 
            'syllabus', 
            'is_published', 
            'specializations'
        ]

    def create(self, validated_data):
        specializations = validated_data.pop('specializations', [])
        course = Course.objects.create(**validated_data)
        syllabus_id = generate_syllabus_id(course)  
        Syllabus.objects.create(course=course, syllabus_id=syllabus_id)
        
        course.specializations.set(specializations)
        return course

    def update(self, instance, validated_data):
        specializations = validated_data.pop('specializations', None)
        instance = super().update(instance, validated_data)
        
        if specializations is not None:
            instance.specializations.set(specializations)
        return instance


class StudentLessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentLessonProgress
        fields = ['id', 'student', 'lesson', 'is_completed']

class StudentCourseProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentCourseProgress
        fields = ['id', 'student', 'course', 'is_completed', 'completion_date']

