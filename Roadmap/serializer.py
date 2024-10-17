from rest_framework import serializers
from .models import CourseRoadmap, RoadmapStep, SpecializationRoadmap, SpecializationRoadmapStep

class CourseRoadmapSerializer(serializers.ModelSerializer):
    aggregated_objectives = serializers.CharField(read_only=True)

    class Meta:
        model = CourseRoadmap
        fields = ['course', 'aggregated_objectives', 'created_at', 'last_updated']
        
class RoadmapStepSerializer(serializers.ModelSerializer):
    learning_objectives = serializers.CharField(source='get_learning_objectives', read_only=True)
    skills_to_acquire = serializers.CharField(source='get_skills_to_acquire', read_only=True)

    class Meta:
        model = RoadmapStep
        fields = ['roadmap', 'lesson', 'topic', 'concept', 'order', 'is_completed', 'learning_objectives', 'skills_to_acquire']
        
class SpecializationRoadmapStepSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.course_title', read_only=True)

    class Meta:
        model = SpecializationRoadmapStep
        fields = ['roadmap', 'course', 'course_title', 'order', 'is_completed']

class SpecializationRoadmapSerializer(serializers.ModelSerializer):
    steps = SpecializationRoadmapStepSerializer(many=True, read_only=True)

    class Meta:
        model = SpecializationRoadmap
        fields = ['specialization', 'created_at', 'last_updated', 'steps']
