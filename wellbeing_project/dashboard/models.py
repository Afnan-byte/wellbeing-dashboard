# from django.db import models
# from django.contrib.auth.models import User

# class UserProfile(models.Model):
#     USER_TYPE_CHOICES = [
#         ('student', 'Student'),
#         ('teacher', 'Teacher'),
#     ]
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
#     class_group = models.CharField(max_length=50, blank=True)
    
#     def __str__(self):
#         return f"{self.user.username} - {self.user_type}"

# class MoodEntry(models.Model):
#     MOOD_CHOICES = [
#         ('happy', 'Happy'),
#         ('ecstatic', 'Ecstatic'),
#         ('inspired', 'Inspired'),
#         ('calm', 'Calm'),
#         ('good', 'Good'),
#         ('numb', 'Numb'),
#         ('worried', 'Worried'),
#         ('lethargic', 'Lethargic'),
#         ('grumpy', 'Grumpy'),
#         ('sad', 'Sad'),
#         ('stressed', 'Stressed'),
#         ('angry', 'Angry'),
#     ]
    
#     MOOD_EMOJI = {
#         'happy': '😊',
#         'ecstatic': '😄',
#         'inspired': '✨',
#         'calm': '😌',
#         'good': '👍',
#         'numb': '😐',
#         'worried': '😟',
#         'lethargic': '😴',
#         'grumpy': '😠',
#         'sad': '😢',
#         'stressed': '😰',
#         'angry': '😡',
#     }
    
#     user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
#     date = models.DateField(auto_now_add=True)
#     mood = models.CharField(max_length=20, choices=MOOD_CHOICES)
#     comment = models.TextField(blank=True, null=True)
#     timestamp = models.DateTimeField(auto_now_add=True)
    
#     class Meta:
#         ordering = ['-timestamp']
    
#     def __str__(self):
#         return f"{self.user.username if self.user else 'Unknown'} - {self.mood} - {self.date}"
    
#     def get_emoji(self):
#         return self.MOOD_EMOJI.get(self.mood, '😊')

