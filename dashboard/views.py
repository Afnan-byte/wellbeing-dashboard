import os
import csv
from datetime import datetime, timedelta

from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Count
from django.http import HttpResponse

from .models import UserProfile, MoodEntry


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user_type = request.POST.get('user_type', '')

        if not email or '@' not in email:
            return render(request, 'login.html', {'error': 'Please enter a valid email.'})

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            return render(request, 'login.html', {'error': 'No account found with this email'})

        user = authenticate(request, username=user_obj.username, password=password)
        if user is None:
            return render(request, 'login.html', {'error': 'Invalid password'})

        try:
            profile = UserProfile.objects.get(user=user)
            if profile.user_type != user_type:
                return render(request, 'login.html', {
                    'error': f"Account is registered as {profile.user_type}, not {user_type}"
                })
        except UserProfile.DoesNotExist:
            return render(request, 'login.html', {'error': 'Profile missing for this account'})

        login(request, user)

        return redirect('student_checkin' if user_type == 'student' else 'teacher_dashboard')

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def student_checkin(request):
    profile = UserProfile.objects.get(user=request.user)
    if profile.user_type != 'student':
        return redirect('teacher_dashboard')

    today = datetime.now().date()
    has_checked = MoodEntry.objects.filter(user=request.user, date=today).exists()

    if request.method == 'POST':
        mood = request.POST.get('mood')
        comment = request.POST.get('comment', '')

        MoodEntry.objects.update_or_create(
            user=request.user,
            date=today,
            defaults={'mood': mood, 'comment': comment}
        )

        return render(request, 'student_checkin.html', {'success': True})

    return render(request, 'student_checkin.html', {'already_checked': has_checked})


@login_required
def student_history(request):
    profile = UserProfile.objects.get(user=request.user)
    if profile.user_type != 'student':
        return redirect('teacher_dashboard')

    entries = MoodEntry.objects.filter(user=request.user).order_by('-date')[:30]

    chart_data = [
        {
            'date': entry.date.strftime('%b %d'),
            'mood': entry.mood,
            'emoji': entry.get_emoji() if hasattr(entry, 'get_emoji') else ''
        }
        for entry in reversed(entries)
    ]

    return render(request, 'student_history.html', {
        'entries': entries,
        'chart_data': chart_data
    })


@login_required
def teacher_dashboard(request):
    profile = UserProfile.objects.get(user=request.user)
    if profile.user_type != 'teacher':
        return redirect('student_checkin')

    today = datetime.now().date()
    week_ago = today - timedelta(days=7)

    students = User.objects.filter(userprofile__user_type='student')
    total_students = students.count()

    checked_today = MoodEntry.objects.filter(date=today).values('user').distinct().count()
    mood_counts = MoodEntry.objects.filter(date=today).values('mood').annotate(count=Count('mood'))

    mood_data = {m['mood']: m['count'] for m in mood_counts}
    total = sum(mood_data.values())

    mood_percentages = {
        mood: round((count / total * 100), 1) if total > 0 else 0
        for mood, count in mood_data.items()
    }

    low_moods = ['sad', 'stressed', 'angry', 'worried']
    low_entries = MoodEntry.objects.filter(date=today, mood__in=low_moods).select_related('user')

    weekly_moods = MoodEntry.objects.filter(date__gte=week_ago).values('mood').annotate(count=Count('mood'))

    context = {
        'total_students': total_students,
        'checked_in_today': checked_today,
        'engagement_percent': round((checked_today / total_students * 100)) if total_students else 0,
        'mood_data': mood_data,
        'mood_percentages': mood_percentages,
        'low_mood_entries': low_entries,
        'low_mood_count': low_entries.count(),
        'weekly_moods': weekly_moods[:3],
    }

    return render(request, 'teacher_dashboard.html', context)


@login_required
def teacher_results(request):
    profile = UserProfile.objects.get(user=request.user)
    if profile.user_type != 'teacher':
        return redirect('student_checkin')

    week_ago = datetime.now().date() - timedelta(days=7)
    entries = MoodEntry.objects.filter(date__gte=week_ago).select_related('user')

    return render(request, 'teacher_results.html', {'entries': entries})


@login_required
def teacher_students(request):
    profile = UserProfile.objects.get(user=request.user)
    if profile.user_type != 'teacher':
        return redirect('student_checkin')

    students = User.objects.filter(userprofile__user_type='student')

    student_list = []
    for s in students:
        latest = MoodEntry.objects.filter(user=s).order_by('-date').first()
        student_list.append({
            'name': s.get_full_name() or s.username,
            'latest_mood': latest.mood if latest else "No data",
            'emoji': latest.get_emoji() if latest else "❓",
            'date': latest.date if latest else None
        })

    return render(request, 'teacher_students.html', {'students': student_list})


@login_required
def teacher_settings(request):
    profile = UserProfile.objects.get(user=request.user)
    if profile.user_type != 'teacher':
        return redirect('student_checkin')

    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.email = request.POST.get('email', user.email)
        user.save()

        if request.POST.get('new_password'):
            user.set_password(request.POST['new_password'])
            user.save()

        return render(request, 'teacher_settings.html', {'success': True})

    return render(request, 'teacher_settings.html')


@login_required
def moods_csv(request):
    response = HttpResponse(content_type='text/csv')
    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Date', 'Mood', 'Comment', 'Timestamp'])

    entries = MoodEntry.objects.filter(
        date__gte=datetime.now().date() - timedelta(days=30)
    ).select_related('user')

    for e in entries:
        writer.writerow([
            e.user.get_full_name() or e.user.username,
            e.date,
            e.mood,
            e.comment or '',
            e.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return response


def home(request):
    return HttpResponse("Wellbeing Dashboard running")
