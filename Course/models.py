from django.utils import timezone
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from User.models import Specialization

from Exam.models import Exam

class Course(models.Model):
    specializations = models.ManyToManyField(Specialization, related_name='courses', default=1)  # Many-to-many relationship
    course_id = models.CharField(max_length=10, primary_key=True)
    course_title = models.CharField(max_length=200)
    short_description = models.CharField(max_length=500)
    long_description = models.TextField()
    image = models.ImageField(upload_to='images/', default='default.png')
    is_published = models.BooleanField(default=False)  # New field

    def save(self, *args, **kwargs):
        is_new = self._state.adding  
        super().save(*args, **kwargs)
        
        if is_new:  
            Exam.objects.create(course=self, title=f"{self.course_title} Exam")

    def __str__(self):
        return self.course_title

    def get_all_objectives(self):
        objectives = []

        # Gather objectives from lessons
        lessons = self.lessons.all()
        for lesson in lessons:
            if lesson.learning_objectives:
                objectives.append(f"Lesson {lesson.order}: {lesson.learning_objectives}")

            # Gather objectives from topics
            for topic in lesson.topics.all():
                if topic.learning_objectives:
                    objectives.append(f"Topic {topic.order}: {topic.learning_objectives}")

                # Gather objectives from concepts
                for concept in topic.concepts.all():
                    if concept.learning_objectives:
                        objectives.append(f"Concept {concept.concept_title}: {concept.learning_objectives}")

        return objectives


class Syllabus(models.Model):
    course = models.OneToOneField(Course, on_delete=models.CASCADE, related_name='syllabus')
    syllabus_id = models.CharField(max_length=10, primary_key=True)

    def __str__(self):
        return f"Syllabus for {self.course.course_title}"

class Lesson(models.Model):
    syllabus = models.ForeignKey(Syllabus, on_delete=models.CASCADE, related_name='lessons')
    lesson_id = models.CharField(max_length=10, primary_key=True)
    lesson_title = models.CharField(max_length=200)
    order = models.IntegerField(help_text="Order of the lesson in the syllabus")
    
    learning_objectives = models.TextField(help_text="Objectives students should achieve in this lesson", null=True, blank=True)
    skills_to_acquire = models.TextField(help_text="Skills students should develop in this lesson", null=True, blank=True)

    def __str__(self):
        return f"{self.lesson_title} - {self.syllabus.course.course_title}"
    
class Topic(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='topics')
    topic_id = models.CharField(max_length=10, primary_key=True)
    topic_title = models.CharField(max_length=200)
    order = models.IntegerField(help_text="Order of the topic within the lesson")
    description = models.TextField(blank=True, null=True)
    
    learning_objectives = models.TextField(help_text="Objectives for this topic", null=True, blank=True)
    skills_to_acquire = models.TextField(help_text="Skills to acquire in this topic", null=True, blank=True)


    def __str__(self):
        return f"{self.topic_title} - {self.lesson.lesson_title}"

class Subtopic(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='subtopics')
    subtopic_id = models.CharField(max_length=10, primary_key=True)
    subtopic_title = models.CharField(max_length=200)
    order = models.IntegerField(help_text="Subtopic order within the topic")

    def __str__(self):
        return f"{self.subtopic_title} - {self.topic.topic_title}"

class Concept(models.Model):
    subtopic = models.ForeignKey(Subtopic, on_delete=models.CASCADE, related_name='concepts', null=True, blank=True)  # Optional subtopic connection
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='concepts', null=True, blank=True)  # Fallback to topic
    concept_id = models.CharField(max_length=10, primary_key=True)
    concept_title = models.CharField(max_length=200)
    description = models.TextField()
    difficulty = models.CharField(max_length=50, choices=[('Easy', 'Easy'), ('Medium', 'Medium'), ('Hard', 'Hard')])
    
    learning_objectives = models.TextField(help_text="Objectives for this concept", null=True, blank=True)
    skills_to_acquire = models.TextField(help_text="Skills to acquire in this concept", null=True, blank=True)


    def __str__(self):
        return self.concept_title


    
class StudentLessonProgress(models.Model):
    student = models.ForeignKey('User.Student', on_delete=models.CASCADE)  # Assuming you have a Student model
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('student', 'lesson')

class StudentCourseProgress(models.Model):
    student = models.ForeignKey('User.Student', on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    completion_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'course')

    def __str__(self):
        return f"{self.student} - {self.course} - {'Completed' if self.is_completed else 'In Progress'}"

    def update_progress(self):
        if self.course.all_lessons_completed(self.student):
            self.is_completed = True
            self.completion_date = timezone.now()
            self.save()

class Page(models.Model):
    syllabus = models.ForeignKey(Syllabus, on_delete=models.CASCADE, related_name='pages_by_syllabus')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='pages')
    page_number = models.IntegerField(help_text="Page number within the lesson")
    content = CKEditor5Field('Content', config_name='extends')

    class Meta:
        ordering = ['page_number']
        unique_together = ('lesson', 'page_number')

    def __str__(self):
        return f"Page {self.page_number} - {self.lesson.lesson_title}"

class FileUpload(models.Model):
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

