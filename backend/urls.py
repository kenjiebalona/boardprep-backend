from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import routers
from django.conf import settings
from django.conf.urls.static import static
from Course.views import CourseListViewSet, CourseDetailViewSet, SyllabusViewSet, LessonViewSet, FileUploadViewSet, PageViewSet
from Class.views import ClassViewSet, PostViewSet, CommentViewSet, JoinRequestViewSet, ActivityViewSet, SubmissionViewSet, AttachmentViewSet
from Question.views import QuestionViewSet, ChoiceViewSet, StudentAnswerViewSet
#from DailyChallenge.views import DailyChallengeViewSet, DailyChallengeQuestionViewSet, DailyChallengeLeaderboardViewSet
from User.views import StudentViewSet, TeacherViewSet
from Course import views



router = routers.DefaultRouter()
router.register(r'courses', CourseListViewSet, basename='course')
router.register(r'course/details', CourseDetailViewSet, basename='coursedetail')
router.register(r'syllabi', SyllabusViewSet, basename='syllabus')
router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'pages', PageViewSet, basename='pages')
router.register(r'file-upload', FileUploadViewSet, basename='fileupload')
router.register(r'classes', ClassViewSet, basename='class')
# Other viewsets that need basename
router.register(r'posts', PostViewSet, basename='posts')
router.register(r'comments', CommentViewSet, basename='comments')
router.register(r'student', StudentViewSet, basename='student')
router.register(r'teacher', TeacherViewSet, basename='teacher')
router.register(r'join-requests', JoinRequestViewSet, basename='join-requests')
router.register(r'activities', ActivityViewSet, basename='activities')
router.register(r'submissions', SubmissionViewSet, basename='submissions')
router.register(r'attachments', AttachmentViewSet)
router.register(r'pages', PageViewSet, basename='page')
router.register(r'questions', QuestionViewSet, basename='questions')
router.register(r'choices', ChoiceViewSet, basename='choices')
router.register(r'student-answers', StudentAnswerViewSet, basename='student-answers')
# router.register(r'daily-challenges', DailyChallengeViewSet, basename='daily-challenges')
# router.register(r'daily-challenge-questions', DailyChallengeQuestionViewSet, basename='daily-challenge-questions')
# router.register(r'leaderboards', DailyChallengeLeaderboardViewSet, basename='leaderboards')


#pagkuha og indibidwal nga mga kurso

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
    path('lessons/by_syllabus/<str:syllabus_id>/', LessonViewSet.as_view({'get': 'by_syllabus'}), name='lessons-by-syllabus'),
    path("ckeditor5/", include('django_ckeditor_5.urls')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('', include('User.urls')),
    path('', include('Discussion.urls')),
    re_path(r'^syllabi/(?P<course_id>[^/.]+)/$', SyllabusViewSet.as_view({'get': 'by_course'})),

    #path for payment and subscriptions
    path('', include('Subscription.urls')),
    path('lessons/<str:lesson_id>/pages/', LessonViewSet.as_view({'get': 'get_lesson_pages'}), name='lesson-pages'),
    path('media/uploads/', views.upload_image, name='upload_image'),
    path('pages/<str:lesson_id>/<int:page_number>/', PageViewSet.as_view({'get': 'by_lesson_and_page', 'put': 'by_lesson_and_page', 'delete': 'by_lesson_and_page'}), name='page-detail'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
