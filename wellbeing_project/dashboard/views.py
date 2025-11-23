# views.py (full file - copy & replace)
import os
import json
from datetime import datetime, timedelta

from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.http import HttpResponse

import csv
import gspread
from google.oauth2.service_account import Credentials  # used internally by gspread.service_account_*

from .models import UserProfile, MoodEntry

# ---------- Google Sheets config ----------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
SHEET_ID = "1Q-cL9MfNygceQxKaGkgeq1Y77L9b3MA-Zk2xQSaCIUQ"
# ------------------------------------------

def _get_credentials_path():
    """
    Return credentials path relative to BASE_DIR
    Works whether BASE_DIR is pathlib.Path or string.
    """
    base = settings.BASE_DIR
    # If BASE_DIR is a Path, use / ; else join as strings
    try:
        # pathlib.Path supports division
        return str(base / "credentials" / "service_account.json")
    except TypeError:
        return os.path.join(base, "credentials", "service_account.json")


def load_gspread_client():
    """
    Returns a gspread client using either:
      - GOOGLE_SERVICE_ACCOUNT_JSON env var (preferred on Render)
      - credentials/service_account.json file (local)
    Raises an Exception if neither is found or there's an auth error.
    """
    # 1) Try environment variable (Render-friendly)
    env_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") or os.environ.get("SERVICE_ACCOUNT_JSON")
    if env_json:
        try:
            info = json.loads(env_json)
        except Exception as e:
            raise Exception(f"Invalid GOOGLE_SERVICE_ACCOUNT_JSON contents: {e}")

        # gspread helper: create client from dict
        try:
            client = gspread.service_account_from_dict(info)
            return client
        except Exception as e:
            # If using google auth directly, you could also do:
            # creds = Credentials.from_service_account_info(info, scopes=SCOPES)
            # client = gspread.Client(auth=creds); client.login()
            raise Exception(f"Failed to create gspread client from environment JSON: {e}")

    # 2) Try local file
    cred_path = _get_credentials_path()
    if os.path.exists(cred_path):
        try:
            client = gspread.service_account(filename=cred_path)
            return client
        except Exception as e:
            raise Exception(f"Failed to create gspread client from file {cred_path}: {e}")

    # 3) Not found
    raise Exception("Google service account credentials not found. Set GOOGLE_SERVICE_ACCOUNT_JSON env var or place credentials/service_account.json file.")


# ----------------- Authentication views -----------------
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user_type = request.POST.get('user_type', '')

        # Basic email validation
        if not email or '@' not in email:
            return render(request, 'login.html', {'error': 'Please enter a valid email address'})

        # Find user by email
        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            return render(request, 'login.html', {'error': 'No account found with this email'})

        # Authenticate using username
        user = authenticate(request, username=user_obj.username, password=password)
        if user is None:
            return render(request, 'login.html', {'error': 'Invalid password'})

        # Check profile user_type
        try:
            profile = UserProfile.objects.get(user=user)
            if profile.user_type != user_type:
                return render(request, 'login.html', {'error': f'This account is registered as {profile.user_type}, not {user_type}'})
        except UserProfile.DoesNotExist:
            return render(request, 'login.html', {'error': 'Account profile not found. Please contact admin.'})

        # All good - log in
        login(request, user)
        if user_type == 'student':
            return redirect('student_checkin')
        else:
            return redirect('teacher_dashboard')

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


# ----------------- Student Views -----------------
@login_required
def student_checkin(request):
    profile = UserProfile.objects.get(user=request.user)

    if profile.user_type != 'student':
        return redirect('teacher_dashboard')

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

    chart_data = []
    for entry in reversed(entries):
        chart_data.append({
            'date': entry.date.strftime('%b %d'),
            'mood': entry.mood,
            'emoji': entry.get_emoji() if hasattr(entry, 'get_emoji') else '',
        })

    context = {
        'entries': entries,
        'chart_data': chart_data,
    }

    return render(request, 'student_history.html', context)


# ----------------- Teacher Views -----------------
@login_required
def teacher_dashboard(request):
    profile = UserProfile.objects.get(user=request.user)

    if profile.user_type != 'teacher':
        return redirect('student_checkin')

    today = datetime.now().date()
    week_ago = today - timedelta(days=7)

    all_students = User.objects.filter(userprofile__user_type='student')
    total_students = all_students.count()

    checked_in_today = MoodEntry.objects.filter(date=today).values('user').distinct().count()

    mood_counts = MoodEntry.objects.filter(date=today).values('mood').annotate(count=Count('mood'))
    mood_data = {item['mood']: item['count'] for item in mood_counts}

    total_checkins = sum(mood_data.values())
    mood_percentages = {}
    for mood, count in mood_data.items():
        mood_percentages[mood] = round((count / total_checkins * 100) if total_checkins > 0 else 0, 1)

    low_moods = ['sad', 'stressed', 'angry', 'worried']
    low_mood_entries = MoodEntry.objects.filter(date=today, mood__in=low_moods).select_related('user')

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


# ----------------- CSV export -----------------
@login_required
def moods_csv(request):
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


# ----------------- Google Sheets functions -----------------
def push_to_google_sheet():
    """
    Push all MoodEntry rows to the configured Google Sheet.
    Returns (True, message) on success else (False, error_message)
    """
    try:
        client = load_gspread_client()
    except Exception as e:
        return False, f"Credentials error: {e}"

    try:
        sheet = client.open_by_key(SHEET_ID)
        worksheet = sheet.sheet1

        # Clear existing content (optional)
        worksheet.clear()

        # Header + rows
        header = ["Student Name", "Date", "Mood", "Comment", "Timestamp"]
        # Collect all rows first (so we can do a single update)
        entries = MoodEntry.objects.select_related('user').order_by('-timestamp')
        data_rows = []
        for entry in entries:
            data_rows.append([
                entry.user.get_full_name() or entry.user.username,
                str(entry.date),
                entry.mood,
                entry.comment or '',
                entry.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            ])

        # Write header + rows (batch update)
        if data_rows:
            worksheet.update('A1:E1', [header])
            worksheet.update(f'A2:E{len(data_rows) + 1}', data_rows)
        else:
            # Only header if no data
            worksheet.update('A1:E1', [header])

        return True, "Google Sheet updated successfully"
    except Exception as e:
        return False, f"Google API error: {e}"


@login_required
def update_google_sheet(request):
    success, msg = push_to_google_sheet()
    if success:
        return HttpResponse(msg)
    else:
        return HttpResponse(f"Error updating sheet: {msg}", status=500)


# A simple home/health endpoint if you want to wire it to the root
def home(request):
    return HttpResponse("Wellbeing Dashboard running")
