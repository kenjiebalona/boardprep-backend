from django.utils import timezone
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from User.models import Specialization

from Exam.models import Exam

class Objective(models.Model):
    text = models.CharField(max_length=500)

class Skill(models.Model):
    text = models.CharField(max_length=500)

class Course(models.Model):
    specializations = models.ManyToManyField(Specialization, related_name='courses')  
    course_id = models.CharField(max_length=10, primary_key=True)
    course_title = models.CharField(max_length=200)
    short_description = models.CharField(max_length=500)
    image = models.ImageField(upload_to='images/', default='default.png')
    is_published = models.BooleanField(default=False)  
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

        return objectives

class Syllabus(models.Model):
    course = models.OneToOneField(Course, on_delete=models.CASCADE, related_name='syllabus')
    syllabus_id = models.CharField(max_length=10, primary_key=True)

    def __str__(self):
        return f"Syllabus for {self.course.course_title}"

class Lesson(models.Model):
    syllabus = models.ForeignKey(Syllabus, on_delete=models.CASCADE, related_name='lessons')
    lesson_title = models.CharField(max_length=200)
    order = models.IntegerField()
    
    learning_objectives = models.ManyToManyField(Objective, related_name='lessons', blank=True)
    skills_to_acquire = models.ManyToManyField(Skill, related_name='lessons', blank=True)


    def __str__(self):
        return f"{self.lesson_title} - {self.syllabus.course.course_title}"
    
class Topic(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='topics')
    topic_title = models.CharField(max_length=200)
    order = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    
    learning_objectives = models.ManyToManyField(Objective, related_name='topics', blank=True)
    skills_to_acquire = models.ManyToManyField(Skill, related_name='topics', blank=True)

    def __str__(self):
        return f"{self.topic_title} - {self.lesson.lesson_title}"

class Subtopic(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='subtopics')
    subtopic_title = models.CharField(max_length=200)
    order = models.IntegerField()

    def __str__(self):
        return f"{self.subtopic_title} - {self.topic.topic_title}"
    
class LearningObjective(models.Model):
    text = models.CharField(max_length=500)
    subtopic = models.ForeignKey(Subtopic, on_delete=models.CASCADE, related_name='learning_objectives')

    def __str__(self):
        return self.text

class Page(models.Model):
    subtopic = models.ForeignKey(Subtopic, on_delete=models.CASCADE, related_name='pages')
    page_number = models.IntegerField()

    class Meta:
        ordering = ['page_number']

    def __str__(self):
        return f"Page {self.page_number} - {self.subtopic.subtopic_title}"
    
class ContentBlock(models.Model):
    BLOCK_TYPE_CHOICES = [
        ('lesson', 'Lesson Content'),
        ('example', 'Example'),
        ('case', 'Case Study'), 
        ('practice', 'Practice'), 
    ]

    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='content_blocks')
    block_type = models.CharField(max_length=50, choices=BLOCK_TYPE_CHOICES)
    difficulty = models.CharField(max_length=50, choices=DIFFICULTY_CHOICES)
    content = models.TextField()
    file = models.FileField(upload_to='content_blocks/files/', null=True, blank=True)

    def __str__(self):
        return f"{self.get_block_type_display()} ({self.get_difficulty_display()}) - {self.page.subtopic.subtopic_title}"
    def save(self, *args, **kwargs):
        if self.block_type == 'lesson':
            self.difficulty = None
        super().save(*args, **kwargs)

class FileUpload(models.Model):
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


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
            
