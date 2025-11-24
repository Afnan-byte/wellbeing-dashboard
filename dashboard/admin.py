from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import UserProfile, MoodEntry


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_type', 'class_group']
    list_filter = ['user_type']
    search_fields = ['user__username', 'class_group']


class MoodEntryResource(resources.ModelResource):
    class Meta:
        model = MoodEntry
        fields = (
            'user__username',
            'user__email',
            'mood',
            'comment',
            'date',
            'timestamp'
        )


@admin.register(MoodEntry)
class MoodEntryAdmin(ImportExportModelAdmin):   
    resource_class = MoodEntryResource

    list_display = ['user', 'mood', 'mood_emoji', 'date', 'timestamp']
    list_filter = ['mood', 'date']
    search_fields = ['user__username', 'comment']
    readonly_fields = ['timestamp', 'date']
    ordering = ['-timestamp']

    def mood_emoji(self, obj):
        return obj.get_emoji()
    mood_emoji.short_description = "Emoji"
