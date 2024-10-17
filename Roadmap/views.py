from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import CourseRoadmap, RoadmapStep,  SpecializationRoadmap
from .serializer import CourseRoadmapSerializer, RoadmapStepSerializer, SpecializationRoadmapSerializer

class CourseRoadmapViewSet(viewsets.ModelViewSet):
    queryset = CourseRoadmap.objects.all()
    serializer_class = CourseRoadmapSerializer

    # Get roadmap for a specific course
    @action(detail=False, methods=['get'], url_path='by_course/(?P<course_id>[^/.]+)')
    def by_course(self, request, course_id=None):
        """
        Retrieve the roadmap for a given course.
        """
        roadmap = self.queryset.filter(course_id=course_id).first()
        if not roadmap:
            return Response({"error": "Roadmap not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(roadmap)
        return Response(serializer.data)

    # Update aggregated objectives for a roadmap
    @action(detail=True, methods=['put'], url_path='update_objectives')
    def update_objectives(self, request, pk=None):
        roadmap = self.get_object()
        roadmap.update_aggregated_objectives()
        return Response({'status': 'Objectives updated', 'aggregated_objectives': roadmap.aggregated_objectives})

class RoadmapStepViewSet(viewsets.ModelViewSet):
    queryset = RoadmapStep.objects.all()
    serializer_class = RoadmapStepSerializer

    # Get all steps for a specific course roadmap
    @action(detail=False, methods=['get'], url_path='by_course/(?P<course_id>[^/.]+)')
    def by_course(self, request, course_id=None):
        steps = self.queryset.filter(roadmap__course_id=course_id)
        serializer = self.get_serializer(steps, many=True)
        return Response(serializer.data)

    # Mark a roadmap step as completed
    @action(detail=True, methods=['put'], url_path='mark_completed')
    def mark_completed(self, request, pk=None):
        step = self.get_object()
        step.is_completed = True
        step.save()
        return Response({'status': 'Step marked as completed', 'step': step.id})
    
class SpecializationRoadmapViewSet(viewsets.ModelViewSet):
    queryset = SpecializationRoadmap.objects.all()
    serializer_class = SpecializationRoadmapSerializer

    # Get roadmap for a specific specialization
    @action(detail=False, methods=['get'], url_path='by_specialization/(?P<specialization_id>[^/.]+)')
    def by_specialization(self, request, specialization_id=None):
        roadmap = self.queryset.filter(specialization_id=specialization_id).first()
        if not roadmap:
            return Response({"error": "Specialization roadmap not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(roadmap)
        return Response(serializer.data)