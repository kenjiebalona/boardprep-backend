# views.py
from django.db.models import Exists, OuterRef, F
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action, parser_classes
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from .models import Course, Lesson, StudentCourseProgress, StudentLessonProgress, Syllabus, Page, FileUpload, Topic, Subtopic, ContentBlock
from Course.serializer import CourseSerializer, StudentCourseProgressSerializer, StudentLessonProgressSerializer, SyllabusSerializer, LessonSerializer, FileUploadSerializer, PageSerializer, SubtopicSerializer, TopicSerializer, ContentBlockSerializer
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db import transaction, models
from storages.backends.azure_storage import AzureStorage

from openai import OpenAI
import environ
import os




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

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    @action(detail=False, methods=['get'], url_path='check_id/(?P<course_id>[^/.]+)')
    def check_course_id(self, request, course_id=None):
        """
        Check if a course with the given ID exists.
        """
        course_exists = Course.objects.filter(course_id=course_id).exists()
        return Response({'exists': course_exists})

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

    @action(detail=False, methods=['get', 'post', 'put'], url_path='by_subtopic/(?P<subtopic_id>[^/.]+)')
    def by_subtopic(self, request, subtopic_id=None):
        student_id = request.query_params.get('student_id', None) # optional ra ni for mastery

        if request.method == 'GET':
            pages = self.queryset.filter(subtopic_id=subtopic_id)

            if student_id:
                try:
                    mastery = StudentMastery.objects.get(student_id=student_id, subtopic_id=subtopic_id).mastery_level
                    
                    # Pwede pani mamodify kung asa ka na sa mastery level
                    if mastery < 50.0:
                        difficulty_level = 'beginner'
                    elif mastery < 80.0:
                        difficulty_level = 'intermediate'
                    else:
                        difficulty_level = 'advanced'

                    # Filter sa pages based sa mastery level
                    pages = pages.prefetch_related(
                        models.Prefetch(
                            'content_blocks',
                            queryset=ContentBlock.objects.filter(difficulty=difficulty_level)
                        )
                    )

                except StudentMastery.DoesNotExist:
                    return Response({"detail": "Mastery record not found for the student."}, status=status.HTTP_404_NOT_FOUND)

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
        
    @action(detail=True, methods=['get'], url_path='content_blocks')
    def content_blocks(self, request, pk=None):
        try:
            page = get_object_or_404(Page, pk=pk)  
            content_blocks = ContentBlock.objects.filter(page=page)
            serializer = ContentBlockSerializer(content_blocks, many=True)
            return Response(serializer.data)
        except Page.DoesNotExist:
            return Response({"error": "Page not found."}, status=status.HTTP_404_NOT_FOUND)
        
    @action(detail=True, methods=['get'])
    def get_page_by_id(self, request, pk=None):
        page = get_object_or_404(Page, pk=pk)
        serializer = self.get_serializer(page)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='summarize_lesson_content')
    def summarize_lesson_content(self, request):
        lesson_id = request.data.get("lesson_id")
        
        if not lesson_id:
            return Response({"detail": "Lesson ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        lesson_content_blocks = ContentBlock.objects.filter(lesson_id=lesson_id, label="lesson-content")

        if not lesson_content_blocks.exists():
            return Response({"detail": "No content blocks found with the label 'lesson-content'."}, status=status.HTTP_404_NOT_FOUND)

        full_content = " ".join([block.content for block in lesson_content_blocks])

        env = environ.Env(DEBUG=(bool, False))
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        environ.Env.read_env(os.path.join(BASE_DIR, '.env'))
        client = OpenAI(api_key=env('OPENAI_API_KEY'))

        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful summarizer for educational content. Provide a concise summary for students based on the given content, highlighting key concepts and important points."},
                {"role": "user", "content": full_content}
            ]
        )
        summary = completion.choices[0].message.content.strip()

        return Response({"summary": summary}, status=status.HTTP_200_OK)

class ContentBlockViewSet(viewsets.ModelViewSet):
    queryset = ContentBlock.objects.all()
    serializer_class = ContentBlockSerializer

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            content_blocks = request.data.get("blocks", [])
            created_blocks = []
            for block_data in content_blocks:
                page_id = block_data.get("page")
                page = get_object_or_404(Page, pk=page_id)
                block_serializer = self.get_serializer(data=block_data)
                if block_serializer.is_valid():
                    block = block_serializer.save(page=page)
                    created_blocks.append(block)
                else:
                    return Response(block_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({"blocks": self.get_serializer(created_blocks, many=True).data}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            content_blocks = request.data.get("blocks", [])
            print("Received content_blocks payload:", content_blocks)
            page_id = request.data.get("page")

            page = get_object_or_404(Page, pk=page_id)

            for block_data in content_blocks:
                block_id = block_data.get("block_id") 
                block = get_object_or_404(ContentBlock, id=block_id)
                serializer = self.get_serializer(block, data=block_data, partial=True)
                if serializer.is_valid():
                    serializer.save()  
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            return Response({"status": "Blocks updated successfully"}, status=status.HTTP_200_OK)
        
    @action(detail=False, methods=['post', 'put'], url_path='by_page/(?P<page_id>[^/.]+)')
    def by_page(self, request, page_id=None):
        page = get_object_or_404(Page, id=page_id)
        content_blocks_data = request.data.get("content_blocks", [])
        print(content_blocks_data )
        for block_data in content_blocks_data:
            block_id = block_data.get("block_id")
            if block_id:
                content_block = get_object_or_404(ContentBlock, id=block_id, page=page)
                serializer = ContentBlockSerializer(content_block, data=block_data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                ContentBlock.objects.create(page=page, **block_data)
        
        return Response({"status": "Content blocks updated successfully"}, status=status.HTTP_200_OK)



    def destroy(self, request, *args, **kwargs):

        block_id = kwargs.get('pk')
        content_block = get_object_or_404(ContentBlock, pk=block_id)
        content_block.delete()
        return Response({"status": "Block deleted"}, status=status.HTTP_204_NO_CONTENT)


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

class UploadFileView(APIView):
    def post(self, request):
        if 'upload' not in request.FILES:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        upload = request.FILES['upload']
        try:
            fs = FileSystemStorage()  
            filename = fs.save(upload.name, upload)
            uploaded_file_url = fs.url(filename)  
            return Response({'url': uploaded_file_url}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': f'Failed to upload file: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
