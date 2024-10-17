from django.db import models

from User.models import Specialization
from Course.models import Course, Lesson, Topic, Concept


class SpecializationRoadmap(models.Model):
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE, related_name='roadmaps')
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Roadmap for {self.specialization.name}"

class SpecializationRoadmapStep(models.Model):
    roadmap = models.ForeignKey(SpecializationRoadmap, on_delete=models.CASCADE, related_name='steps')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='specialization_steps')
    order = models.IntegerField(help_text="Order of this course in the specialization roadmap")
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Specialization Step: {self.course.course_title} - Order {self.order}"

class CourseRoadmap(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='roadmaps')
    aggregated_objectives = models.TextField(help_text="All learning objectives for the course", blank=True, null=True)  # Optional cached objectives
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Roadmap for {self.course.course_title}"

    def update_aggregated_objectives(self):
        objectives = []

        lessons = self.course.lessons.all()
        for lesson in lessons:
            if lesson.learning_objectives:
                objectives.append(f"Lesson {lesson.order}: {lesson.learning_objectives}")
            for topic in lesson.topics.all():
                if topic.learning_objectives:
                    objectives.append(f"Topic {topic.order}: {topic.learning_objectives}")
                for concept in topic.concepts.all():
                    if concept.learning_objectives:
                        objectives.append(f"Concept {concept.concept_title}: {concept.learning_objectives}")

        self.aggregated_objectives = "\n".join(objectives)
        self.save()

class RoadmapStep(models.Model):
    roadmap = models.ForeignKey(CourseRoadmap, on_delete=models.CASCADE, related_name='steps')
    
    # Links to lessons, topics, or concepts
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, null=True, blank=True, related_name='roadmap_steps')
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, null=True, blank=True, related_name='roadmap_steps')
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, null=True, blank=True, related_name='roadmap_steps')

    order = models.IntegerField(help_text="Order of this step in the roadmap")
    
    def __str__(self):
        if self.concept:
            return f"Roadmap Step for Concept: {self.concept.concept_title}"
        elif self.topic:
            return f"Roadmap Step for Topic: {self.topic.topic_title}"
        return f"Roadmap Step for Lesson: {self.lesson.lesson_title}"

    @property
    def learning_objectives(self):
        if self.concept:
            return self.concept.learning_objectives
        elif self.topic:
            return self.topic.learning_objectives
        elif self.lesson:
            return self.lesson.learning_objectives
        return None

    @property
    def skills_to_acquire(self):
        if self.concept:
            return self.concept.skills_to_acquire
        elif self.topic:
            return self.topic.skills_to_acquire
        elif self.lesson:
            return self.lesson.skills_to_acquire
        return None

