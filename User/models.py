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
    subtopic = models.ForeignKey("Course.Subtopic", on_delete=models.CASCADE, related_name='mastery')
    mastery_level = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)  # Mastery as a percentage
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.user_name} - {self.subtopic.subtopic_title} - Mastery: {self.mastery_level}%"

    def update_mastery(self):
        # todo
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