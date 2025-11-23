import os
import json
import csv
import hashlib
from datetime import datetime, timedelta

from django.shortcuts import render, redirect
from django.http import HttpResponse
import gspread


# ---------- Google Sheets Config ----------
SHEET_ID = "1Q-cL9MfNygceQxKaGkgeq1Y77L9b3MA-Zk2xQSaCIUQ"


def load_gspread_client():
    """Load gspread client from environment variable or local file."""
    env_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    
    if env_json:
        try:
            info = json.loads(env_json)
            client = gspread.service_account_from_dict(info)
            return client
        except Exception as e:
            raise Exception(f"Failed to load from env: {e}")
    
    raise Exception("GOOGLE_SERVICE_ACCOUNT_JSON not found in environment")


def get_sheet():
    """Get the Google Sheet workbook."""
    client = load_gspread_client()
    return client.open_by_key(SHEET_ID)


def hash_password(password):
    """Hash password with SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(stored_hash, password):
    """Verify password against stored hash."""
    return stored_hash == hash_password(password)


# ----------------- Authentication Views -----------------
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user_type = request.POST.get('user_type', '')

        if not email or '@' not in email:
            return render(request, 'login.html', {'error': 'Please enter a valid email.'})

        try:
            sheet = get_sheet()
            users_ws = sheet.worksheet('Users')
            all_users = users_ws.get_all_records()
            
            # Find user by email
            user = None
            for u in all_users:
                if u['email'] == email:
                    user = u
                    break
            
            if not user:
                return render(request, 'login.html', {'error': 'No account found with this email'})
            
            # Verify password
            if not verify_password(user['password'], password):
                return render(request, 'login.html', {'error': 'Invalid password'})
            
            # Check user type
            if user['user_type'] != user_type:
                return render(request, 'login.html', {
                    'error': f"Account is registered as {user['user_type']}, not {user_type}"
                })
            
            # Store in session
            request.session['user_email'] = user['email']
            request.session['username'] = user['username']
            request.session['user_name'] = user['first_name']
            request.session['user_type'] = user['user_type']
            
            return redirect('student_checkin' if user_type == 'student' else 'teacher_dashboard')
            
        except Exception as e:
            return render(request, 'login.html', {'error': f'Error: {str(e)}'})

    return render(request, 'login.html')


def logout_view(request):
    request.session.flush()
    return redirect('login')


# ----------------- Student Views -----------------
def student_checkin(request):
    if 'user_email' not in request.session:
        return redirect('login')
    
    if request.session.get('user_type') != 'student':
        return redirect('teacher_dashboard')

    if request.method == 'POST':
        mood = request.POST.get('mood')
        comment = request.POST.get('comment', '')
        username = request.session.get('username')
        
        try:
            sheet = get_sheet()
            moods_ws = sheet.worksheet('MoodEntries')
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            date = datetime.now().strftime('%Y-%m-%d')
            
            moods_ws.append_row([username, date, mood, comment, timestamp])
            
            return render(request, 'student_checkin.html', {'success': True})
        except Exception as e:
            return render(request, 'student_checkin.html', {'error': str(e)})

    return render(request, 'student_checkin.html')


def student_history(request):
    if 'user_email' not in request.session:
        return redirect('login')
    
    username = request.session.get('username')
    
    try:
        sheet = get_sheet()
        moods_ws = sheet.worksheet('MoodEntries')
        all_records = moods_ws.get_all_records()
        
        # Filter by username and sort by date
        user_entries = [r for r in all_records if r['username'] == username]
        user_entries.sort(key=lambda x: x['timestamp'], reverse=True)
        
        entries = user_entries[:30]
        
        return render(request, 'student_history.html', {'entries': entries})
    except Exception as e:
        return render(request, 'student_history.html', {'entries': [], 'error': str(e)})


# ----------------- Teacher Views -----------------
def teacher_dashboard(request):
    if 'user_email' not in request.session:
        return redirect('login')
    
    if request.session.get('user_type') != 'teacher':
        return redirect('student_checkin')

    try:
        sheet = get_sheet()
        users_ws = sheet.worksheet('Users')
        moods_ws = sheet.worksheet('MoodEntries')
        
        all_users = users_ws.get_all_records()
        all_moods = moods_ws.get_all_records()
        
        # Count students
        students = [u for u in all_users if u['user_type'] == 'student']
        total_students = len(students)
        
        # Today's data
        today = datetime.now().strftime('%Y-%m-%d')
        today_moods = [m for m in all_moods if m['date'] == today]
        
        # Mood counts
        mood_data = {}
        for mood_entry in today_moods:
            mood = mood_entry['mood']
            mood_data[mood] = mood_data.get(mood, 0) + 1
        
        # Students checked in today
        checked_usernames = set([m['username'] for m in today_moods])
        checked_in_today = len(checked_usernames)
        
        # Low mood students
        low_moods = ['sad', 'stressed', 'angry', 'worried']
        low_mood_entries = [m for m in today_moods if m['mood'] in low_moods]
        
        engagement_percent = round((checked_in_today / total_students * 100)) if total_students else 0
        
        context = {
            'teacher_name': request.session.get('user_name', 'Teacher'),
            'total_students': total_students,
            'checked_in_today': checked_in_today,
            'engagement_percent': engagement_percent,
            'mood_data': mood_data,
            'low_mood_entries': low_mood_entries,
            'low_mood_count': len(low_mood_entries),
        }
        
        return render(request, 'teacher_dashboard.html', context)
    except Exception as e:
        return render(request, 'teacher_dashboard.html', {'error': str(e)})


def teacher_results(request):
    if 'user_email' not in request.session:
        return redirect('login')
    
    try:
        sheet = get_sheet()
        moods_ws = sheet.worksheet('MoodEntries')
        all_records = moods_ws.get_all_records()
        
        # Last 7 days
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        entries = [r for r in all_records if r['date'] >= week_ago]
        entries.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return render(request, 'teacher_results.html', {'entries': entries})
    except Exception as e:
        return render(request, 'teacher_results.html', {'entries': [], 'error': str(e)})


def teacher_students(request):
    if 'user_email' not in request.session:
        return redirect('login')
    
    try:
        sheet = get_sheet()
        users_ws = sheet.worksheet('Users')
        moods_ws = sheet.worksheet('MoodEntries')
        
        all_users = users_ws.get_all_records()
        all_moods = moods_ws.get_all_records()
        
        students = [u for u in all_users if u['user_type'] == 'student']
        
        student_list = []
        for student in students:
            username = student['username']
            user_moods = [m for m in all_moods if m['username'] == username]
            
            if user_moods:
                user_moods.sort(key=lambda x: x['timestamp'], reverse=True)
                latest = user_moods[0]
                student_list.append({
                    'name': student['first_name'] or username,
                    'latest_mood': latest['mood'],
                    'emoji': get_mood_emoji(latest['mood']),
                    'date': latest['date']
                })
            else:
                student_list.append({
                    'name': student['first_name'] or username,
                    'latest_mood': 'No data',
                    'emoji': '❓',
                    'date': None
                })
        
        return render(request, 'teacher_students.html', {'students': student_list})
    except Exception as e:
        return render(request, 'teacher_students.html', {'students': [], 'error': str(e)})


def teacher_settings(request):
    if 'user_email' not in request.session:
        return redirect('login')
    
    if request.method == 'POST':
        # Update session data
        request.session['user_name'] = request.POST.get('first_name', request.session.get('user_name'))
        return render(request, 'teacher_settings.html', {'success': True})
    
    return render(request, 'teacher_settings.html')


# ----------------- CSV Download -----------------
def download_csv(request):
    if 'user_email' not in request.session:
        return redirect('login')
    
    try:
        sheet = get_sheet()
        moods_ws = sheet.worksheet('MoodEntries')
        all_records = moods_ws.get_all_records()
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="moods_{datetime.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Student', 'Date', 'Mood', 'Comment', 'Timestamp'])
        
        for entry in all_records:
            writer.writerow([
                entry['username'],
                entry['date'],
                entry['mood'],
                entry.get('comment', ''),
                entry['timestamp']
            ])
        
        return response
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)


def get_mood_emoji(mood):
    """Get emoji for mood."""
    emojis = {
        'happy': '😊', 'ecstatic': '😄', 'inspired': '✨',
        'calm': '😌', 'good': '👍', 'numb': '😐',
        'worried': '😟', 'lethargic': '😴', 'grumpy': '😠',
        'sad': '😢', 'stressed': '😰', 'angry': '😡'
    }
    return emojis.get(mood, '😊')


# ----------------- Home -----------------
def home(request):
    return HttpResponse("Wellbeing Dashboard running")