from django.shortcuts import render
from django.http import Http404

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import AppSettings
from .serializers import AppSettingsSerializer

class AppSettingsListsView(generics.ListCreateAPIView):
    queryset = AppSettings.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = AppSettingsSerializer

    def get_queryset(self):
        # Return all AppSettings ordered by setting_key
        return AppSettings.objects.all().order_by('setting_key')
    
class AppSettingsDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View to retrieve, update or delete a specific app setting"""
    queryset = AppSettings.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = AppSettingsSerializer
    lookup_field = 'id' 



