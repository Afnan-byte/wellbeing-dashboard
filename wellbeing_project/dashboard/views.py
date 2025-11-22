from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.http import HttpResponse
from datetime import datetime, timedelta
import csv
from .models import UserProfile, MoodEntry
import gspread
from google.oauth2.service_account import Credentials


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user_type = request.POST.get('user_type', '')
        
        print(f"DEBUG: Email={email}, UserType={user_type}")  # Debug
        
        # Validate email format
        if not email or '@' not in email:
            return render(request, 'login.html', {'error': 'Please enter a valid email address'})
        
        # Find user by email
        try:
            user_obj = User.objects.get(email=email)
            print(f"DEBUG: Found user={user_obj.username}")  # Debug
        except User.DoesNotExist:
            print(f"DEBUG: No user found with email={email}")  # Debug
            return render(request, 'login.html', {'error': 'No account found with this email'})
        
        # Authenticate with username
        user = authenticate(request, username=user_obj.username, password=password)
        print(f"DEBUG: Authentication result={user}")  # Debug
        
        if user is None:
            return render(request, 'login.html', {'error': 'Invalid password'})
        
        # Check profile exists and matches user type
        try:
            profile = UserProfile.objects.get(user=user)
            print(f"DEBUG: Profile found, type={profile.user_type}")  # Debug
            if profile.user_type != user_type:
                return render(request, 'login.html', {'error': f'This account is registered as {profile.user_type}, not {user_type}'})
        except UserProfile.DoesNotExist:
            print(f"DEBUG: No profile found")  # Debug
            return render(request, 'login.html', {'error': 'Account profile not found. Please contact admin.'})
        
        # Login successful
        login(request, user)
        print(f"DEBUG: Login successful, redirecting to {user_type}")  # Debug
        
        if user_type == 'student':
            return redirect('student_checkin')
        else:
            return redirect('teacher_dashboard')
    
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def student_checkin(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.user_type != 'student':
        return redirect('teacher_dashboard')
    
    # Check if already checked in today
    today = datetime.now().date()
    already_checked = MoodEntry.objects.filter(user=request.user, date=today).exists()
    
    if request.method == 'POST':
        mood = request.POST.get('mood')
        comment = request.POST.get('comment', '')
        
        MoodEntry.objects.update_or_create(
            user=request.user,
            date=today,
            defaults={'mood': mood, 'comment': comment}
        )
        
        return render(request, 'student_checkin.html', {'success': True})
    
    return render(request, 'student_checkin.html', {'already_checked': already_checked})

@login_required
def student_history(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.user_type != 'student':
        return redirect('teacher_dashboard')
    
    entries = MoodEntry.objects.filter(user=request.user).order_by('-date')[:30]
    
    # Prepare data for chart
    chart_data = []
    for entry in reversed(entries):
        chart_data.append({
            'date': entry.date.strftime('%b %d'),
            'mood': entry.mood,
            'emoji': entry.get_emoji()
        })
    
    context = {
        'entries': entries,
        'chart_data': chart_data,
    }
    
    return render(request, 'student_history.html', context)

@login_required
def teacher_dashboard(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.user_type != 'teacher':
        return redirect('student_checkin')
    
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    # Get all students
    all_students = User.objects.filter(userprofile__user_type='student')
    total_students = all_students.count()
    
    # Students who checked in today
    checked_in_today = MoodEntry.objects.filter(date=today).values('user').distinct().count()
    
    # Mood breakdown for today
    mood_counts = MoodEntry.objects.filter(date=today).values('mood').annotate(count=Count('mood'))
    mood_data = {item['mood']: item['count'] for item in mood_counts}
    
    # Calculate percentages
    total_checkins = sum(mood_data.values())
    mood_percentages = {}
    for mood, count in mood_data.items():
        mood_percentages[mood] = round((count / total_checkins * 100) if total_checkins > 0 else 0, 1)
    
    # Low mood students
    low_moods = ['sad', 'stressed', 'angry', 'worried']
    low_mood_entries = MoodEntry.objects.filter(
        date=today,
        mood__in=low_moods
    ).select_related('user')
    
    # Mood trend (last 7 days)
    weekly_moods = MoodEntry.objects.filter(date__gte=week_ago).values('mood').annotate(count=Count('mood')).order_by('-count')
    
    context = {
        'total_students': total_students,
        'checked_in_today': checked_in_today,
        'engagement_percent': round((checked_in_today / total_students * 100) if total_students > 0 else 0),
        'mood_data': mood_data,
        'mood_percentages': mood_percentages,
        'low_mood_entries': low_mood_entries,
        'low_mood_count': low_mood_entries.count(),
        'weekly_moods': weekly_moods[:3],
    }
    
    return render(request, 'teacher_dashboard.html', context)

@login_required
def teacher_results(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.user_type != 'teacher':
        return redirect('student_checkin')
    
    week_ago = datetime.now().date() - timedelta(days=7)
    entries = MoodEntry.objects.filter(date__gte=week_ago).select_related('user').order_by('-date')
    
    return render(request, 'teacher_results.html', {'entries': entries})

@login_required
def teacher_students(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.user_type != 'teacher':
        return redirect('student_checkin')
    
    # Get all students with their latest mood
    students = User.objects.filter(userprofile__user_type='student')
    
    student_data = []
    for student in students:
        latest_entry = MoodEntry.objects.filter(user=student).order_by('-date').first()
        student_data.append({
            'name': student.get_full_name() or student.username,
            'latest_mood': latest_entry.mood if latest_entry else 'No data',
            'emoji': latest_entry.get_emoji() if latest_entry else '❓',
            'date': latest_entry.date if latest_entry else None,
        })
    
    return render(request, 'teacher_students.html', {'students': student_data})

@login_required
def teacher_settings(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if profile.user_type != 'teacher':
        return redirect('student_checkin')
    
    if request.method == 'POST':
        # Handle profile updates
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        
        new_password = request.POST.get('new_password')
        if new_password:
            user.set_password(new_password)
            user.save()
        
        return render(request, 'teacher_settings.html', {'success': True})
    
    return render(request, 'teacher_settings.html')

@login_required
def moods_csv(request):
    # No Content-Disposition → Google Sheets can read it
    response = HttpResponse(content_type='text/csv')

    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Date', 'Mood', 'Comment', 'Timestamp'])

    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    entries = MoodEntry.objects.filter(date__gte=thirty_days_ago).select_related('user')

    for entry in entries:
        writer.writerow([
            entry.user.get_full_name() or entry.user.username,
            entry.date,
            entry.mood,
            entry.comment or '',
            entry.timestamp
        ])
    return response
def push_to_google_sheet():
    # Path to your JSON key
    creds = Credentials.from_service_account_file(
        'credentials/service_account.json',
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )

    client = gspread.authorize(creds)

    # OPEN GOOGLE SHEET
    sheet = client.open_by_key("1Q-cL9MfNygceQxKaGkgeq1Y77L9b3MA-Zk2xQSaCIUQ").sheet1

    # WRITE HEADER
    sheet.update('A1:E1', [['Student Name', 'Date', 'Mood', 'Comment', 'Timestamp']])

    # FETCH DATABASE DATA
    entries = MoodEntry.objects.select_related('user').all()

    data = []
    for entry in entries:
        data.append([
            entry.user.get_full_name() or entry.user.username,
            str(entry.date),
            entry.mood,
            entry.comment or '',
            entry.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    # WRITE ALL ROWS
    sheet.update(f'A2:E{len(data)+1}', data)

@login_required
def update_google_sheet(request):
    push_to_google_sheet()
    return HttpResponse("Google Sheet updated successfully!")
