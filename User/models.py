from django.db import models

from Subscription.models import Subscription


# Create your models here.
class User(models.Model):
    USER_TYPE = [
        ('S', 'Student'),
        ('T', 'Teacher'),
        ('C', 'Content Creator'),
    ]

    user_name = models.CharField(primary_key=True, null=False, max_length=255, blank=False)
    password = models.CharField(null=False, max_length=255, blank=False)
    first_name = models.CharField(null=False, max_length=255, blank=False)
    last_name = models.CharField(null=False, max_length=255, blank=False)
    email = models.CharField(null=False, max_length=255, blank=False)
    registration_date = models.DateField(auto_now_add=True)
    last_login = models.DateField(auto_now=True)
    user_type = models.CharField(max_length=1, choices=USER_TYPE)
    is_premium = models.BooleanField(default=False)

    @property
    def is_authenticated(self):
        return True

class Specialization(models.Model):
    CHOICES = [
        ('1', 'Chemical Engineering'),
        ('2', 'Mechanical Engineering'),
        ('3', 'Electrical Engineering'),
        ('4', 'Civil Engineering'),
    ]
    name = models.CharField(max_length=255, choices=CHOICES, unique=True)

    def __str__(self):
        return self.name


class Student(User):
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE)
    institution_id = models.ForeignKey('Institution.Institution', on_delete=models.SET_NULL, blank=True, null=True, related_name='institutionID_student')
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return self.user_name

    def save(self, *args, **kwargs):
        self.user_type = 'S'
        super(Student, self).save(*args, **kwargs)

class StudentMastery(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    learning_objective = models.ForeignKey("Course.LearningObjective", on_delete=models.CASCADE, related_name='mastery')
    mastery_level = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)  # Mastery as a percentage
    questions_attempted = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.user_name} - {self.objective} - Mastery: {self.mastery_level}%"

    def update_mastery(self, answers):
        student_mastery = 0
        total_mastery = 0
        weights = { # weights for each difficulty pwede pa ma adjust
            1: 0.5,
            2: 0.75,
            3: 1
        }

        for answer in answers:
            student_mastery += weights[answer['question'].difficulty] * answer['is_correct']
            total_mastery += weights[answer['question'].difficulty]

        avg_mastery = (student_mastery / total_mastery) * 100

        self.questions_attempted += len(answers)
        if self.mastery_level:
            self.mastery_level = (float(self.mastery_level) * float(self.questions_attempted - len(answers)) + avg_mastery) / self.questions_attempted
        else:
            self.mastery_level = avg_mastery

        self.save()

class Teacher(User):
    name = models.CharField(null=False, max_length=255, blank=False)
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE)
    institution_id = models.ForeignKey('Institution.Institution', on_delete=models.SET_NULL, blank=True, null=True, related_name='institutionID_teacher')

    def __str__(self):
        return self.user_name

    def save(self, *args, **kwargs):
        self.user_type = 'T'
        super(Teacher, self).save(*args, **kwargs)

class ContentCreator(User):
    name = models.CharField(null=False, max_length=255, blank=False)

    def __str__(self):
        return self.user_name

    def save(self, *args, **kwargs):
        self.user_type = 'C'
        super(ContentCreator, self).save(*args, **kwargs)