# views.py
from django.db.models import Exists, OuterRef, F
from rest_framework import viewsets, status
from rest_framework.decorators import action, parser_classes
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from .models import Course, Lesson, StudentCourseProgress, StudentLessonProgress, Syllabus, Page, FileUpload, Topic, Subtopic, ContentBlock
from Course.serializer import CourseListSerializer, CourseDetailSerializer, StudentCourseProgressSerializer, StudentLessonProgressSerializer, SyllabusSerializer, LessonSerializer, FileUploadSerializer, PageSerializer, SubtopicSerializer, TopicSerializer, ContentBlockSerializer
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db import transaction, models
from storages.backends.azure_storage import AzureStorage


@api_view(['POST'])
@csrf_exempt
def upload_image(request):
    if request.method == 'POST' and request.FILES['upload']:
        upload = request.FILES['upload']
        azure_storage = AzureStorage()
        filename = azure_storage.save(upload.name, upload)
        uploaded_file_url = azure_storage.url(filename)
        return JsonResponse({'url': uploaded_file_url})
    return JsonResponse({'error': 'Failed to upload file'}, status=400)

class CourseListViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseListSerializer

    @action(detail=False, methods=['get'], url_path='check_id/(?P<course_id>[^/.]+)')
    def check_course_id(self, request, course_id=None):
        """
        Check if a course with the given ID exists.
        """
        course_exists = Course.objects.filter(course_id=course_id).exists()
        return Response({'exists': course_exists})

    @action(detail=True, methods=['put'])
    def publish(self, request, pk=None):
        course = self.get_object()
        course.is_published = True
        course.save()
        return Response({'status': 'course published'}, status=status.HTTP_200_OK)

class CourseDetailViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all().prefetch_related('syllabus__lessons')
    serializer_class = CourseDetailSerializer

    @action(detail=True, methods=['put'], url_path='publish')
    def publish_course(self, request, pk=None):
        course = self.get_object()
        course.is_published = True
        course.save()
        return Response({'status': 'course published'}, status=status.HTTP_200_OK)

class SyllabusViewSet(viewsets.ModelViewSet):
    queryset = Syllabus.objects.all()
    serializer_class = SyllabusSerializer
    @action(detail=False, methods=['get'], url_path='(?P<course_id>[^/.]+)')
    def by_course(self, request, course_id=None):
        queryset = self.get_queryset().filter(course=course_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all().prefetch_related('topics')
    serializer_class = LessonSerializer
    
    @action(detail=True, methods=['get'], url_path='topics')
    def get_lesson_topics(self, request, pk=None):
        lesson = self.get_object()
        topics = lesson.topics.all()
        serializer = TopicSerializer(topics, many=True)
        return Response(serializer.data)

    def by_syllabus(self, request, syllabus_id=None):
        queryset = self.get_queryset().filter(syllabus=syllabus_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['put'], url_path='update_lesson')
    def update_lesson(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        serializer = self.get_serializer(lesson, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'lesson updated'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class TopicViewSet(viewsets.ModelViewSet):
    queryset = Topic.objects.all().prefetch_related('subtopics')
    serializer_class = TopicSerializer

    @action(detail=True, methods=['get'], url_path='subtopics')
    def get_topic_subtopics(self, request, pk=None):
        topic = self.get_object()
        subtopics = topic.subtopics.all()
        serializer = SubtopicSerializer(subtopics, many=True)
        return Response(serializer.data)

class SubtopicViewSet(viewsets.ModelViewSet):
    queryset = Subtopic.objects.all().prefetch_related('pages')
    serializer_class = SubtopicSerializer

    @action(detail=True, methods=['get'], url_path='pages')
    def get_subtopic_pages(self, request, pk=None):
        subtopic = self.get_object()
        pages = subtopic.pages.all()
        serializer = PageSerializer(pages, many=True)
        return Response(serializer.data)

class PageViewSet(viewsets.ModelViewSet):
    queryset = Page.objects.all()
    serializer_class = PageSerializer
    lookup_field = 'page_number'  # Specify the lookup field

    @action(detail=False, methods=['get', 'post', 'put'], url_path='(?P<subtopic_id>[^/.]+)')
    def by_subtopic(self, request, subtopic_id=None):
        if request.method == 'GET':
            pages = self.queryset.filter(subtopic_id=subtopic_id)
            serializer = self.get_serializer(pages, many=True)
            return Response(serializer.data)
        elif request.method == 'POST':
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save(subtopic_id=subtopic_id)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'PUT':
            page_number = request.data.get('page_number')
            page = Page.objects.filter(subtopic_id=subtopic_id, page_number=page_number).first()
            if page:
                serializer = self.get_serializer(page, data=request.data)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            return Response({"detail": "Page not found."}, status=status.HTTP_404_NOT_FOUND)

class ContentBlockViewSet(viewsets.ModelViewSet):
    queryset = ContentBlock.objects.all()
    serializer_class = ContentBlockSerializer

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

class FileUploadViewSet(viewsets.ModelViewSet):
    queryset = FileUpload.objects.all()
    serializer_class = FileUploadSerializer

class StudentLessonProgressViewSet(viewsets.ModelViewSet):
    queryset = StudentLessonProgress.objects.all()
    serializer_class = StudentLessonProgressSerializer

    @action(detail=False, methods=['get'])
    def by_student_and_course(self, request):
        student_id = request.query_params.get('student_id')
        course_id = request.query_params.get('course_id')
        if student_id and course_id:
            progress = self.queryset.filter(student_id=student_id, lesson__syllabus__course_id=course_id)
            serializer = self.get_serializer(progress, many=True)
            return Response(serializer.data)
        return Response({"error": "Both student_id and course_id are required"}, status=400)

class StudentCourseProgressViewSet(viewsets.ModelViewSet):
    queryset = StudentCourseProgress.objects.all()
    serializer_class = StudentCourseProgressSerializer

    @action(detail=False, methods=['get'])
    def by_student(self, request):
        student_id = request.query_params.get('student_id')
        if student_id:
            progress = self.queryset.filter(student_id=student_id)
            serializer = self.get_serializer(progress, many=True)
            return Response(serializer.data)
        return Response({"error": "student_id is required"}, status=400)
