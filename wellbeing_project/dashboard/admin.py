from django.contrib import admin
from .models import UserProfile, MoodEntry

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_type', 'class_group']
    list_filter = ['user_type']

@admin.register(MoodEntry)
class MoodEntryAdmin(admin.ModelAdmin):
    list_display = ['user', 'mood', 'date', 'timestamp']
    list_filter = ['mood', 'date']
    search_fields = ['user__username']