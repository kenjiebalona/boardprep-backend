from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import routers
from django.conf import settings
from django.conf.urls.static import static

from Challenge.views import ChallengeViewSet, StudentChallengeAttemptViewSet
from Course.views import CourseViewSet, StudentCourseProgressViewSet, StudentLessonProgressViewSet, SyllabusViewSet, LessonViewSet, FileUploadViewSet, PageViewSet, ContentBlockViewSet, TopicViewSet, SubtopicViewSet
from Class.views import ClassViewSet, PostViewSet, CommentViewSet, JoinRequestViewSet, ActivityViewSet, SubmissionViewSet, AttachmentViewSet
from Exam.views import ExamViewSet, StudentExamAttemptViewSet
from Question.views import QuestionViewSet, ChoiceViewSet, StudentAnswerViewSet
from Quiz.views import QuizViewSet, StudentQuizAttemptViewSet
from User.views import StudentViewSet, TeacherViewSet, SpecializationViewSet
from Preassessment.views import QuestionViewSet, ChoiceViewSet, StudentAnswerViewSet
from Course import views



router = routers.DefaultRouter()
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'syllabi', SyllabusViewSet, basename='syllabus')
router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'pages', PageViewSet, basename='pages')
router.register(r'file-upload', FileUploadViewSet, basename='fileupload')
router.register(r'classes', ClassViewSet, basename='class')
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
router.register(r'studentAnswers', StudentAnswerViewSet, basename='studentAnswers')
router.register(r'quizzes', QuizViewSet, basename='quizzes')
router.register(r'studentQuizAttempt', StudentQuizAttemptViewSet, basename='studentQuizAttempt')
router.register(r'exams', ExamViewSet, basename='exams')
router.register(r'studentExamAttempt', StudentExamAttemptViewSet, basename='studentExamAttempt')
router.register(r'challenges', ChallengeViewSet, basename='challenges')
router.register(r'studentChallengeAttempt', StudentChallengeAttemptViewSet, basename='studentChallengeAttempt')
router.register(r'student-answers', StudentAnswerViewSet, basename='student-answers')
router.register(r'student-lesson-progress', StudentLessonProgressViewSet, basename='student-lesson-progress')
router.register(r'student-course-progress', StudentCourseProgressViewSet, basename='student-course-progress')
router.register(r'content-blocks', ContentBlockViewSet, basename='contentblock')
router.register(r'pages', PageViewSet, basename='page')
router.register(r'subtopics', SubtopicViewSet, basename='subtopic')
router.register(r'topics', TopicViewSet, basename='topic')
router.register(r'specializations', SpecializationViewSet, basename='specialization')
router.register(r'preassessment', QuestionViewSet, basename='preassessment-question')


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
    path('student-lesson-progress/by-student-and-course/', StudentLessonProgressViewSet.as_view({'get': 'by_student_and_course'}), name='student-lesson-progress-by-student-and-course'),
    path('student-course-progress/by-student/', StudentCourseProgressViewSet.as_view({'get': 'by_student'}), name='student-course-progress-by-student'),
    path('exams/generate_adaptive_exam/', ExamViewSet.as_view({'post': 'generate_adaptive_exam'}), name='exam-generate-adaptive-exam'),
    path('exams/<int:pk>/detailed-results/', ExamViewSet.as_view({'get': 'detailed_results'}), name='exam-detailed-results'),
    path('exams/<int:pk>/student-performance/', ExamViewSet.as_view({'get': 'student_performance'}), name='exam-student-performance'),
    path('exams/<int:pk>/overall-performance/', ExamViewSet.as_view({'get': 'overall_performance'}), name='exam-overall-performance'),
    path('exams/<int:pk>/submit/', ExamViewSet.as_view({'post': 'submit_exam'}), name='exam-submit'),
    path('exams/<int:pk>/get-failed-lessons/', ExamViewSet.as_view({'get': 'get_failed_lessons'}), name='exam-get-failed-lessons'),
    path('exams/<int:pk>/get-exam-questions/', ExamViewSet.as_view({'get': 'get_exam_questions'}), name='exam-get-exam-questions'),
    path('studentExamAttempt/retake/', StudentExamAttemptViewSet.as_view({'post': 'retake_exam'}), name='student-exam-attempt-retake'),
    path('exams/<int:pk>/current-attempt-number/', ExamViewSet.as_view({'get': 'get_current_attempt_number'}), name='exam-current-attempt-number'),
    path('api/exams/student-info/', ExamViewSet.as_view({'get': 'get_student_exam_info'}), name='exam-student-info'),



]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
