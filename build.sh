#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

# Create migrations
python manage.py makemigrations
python manage.py makemigrations dashboard

# Apply migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --no-input

# Create superuser automatically (non-interactive)
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" | python manage.py shell

# Create test users
echo "
from django.contrib.auth.models import User
from dashboard.models import UserProfile

# Student
if not User.objects.filter(email='afnan.messaging@gmail.com').exists():
    student = User.objects.create_user(username='afnan', email='afnan.messaging@gmail.com', password='test123', first_name='Afnan')
    UserProfile.objects.create(user=student, user_type='student')
    print('Student created')

# Teacher
if not User.objects.filter(email='teacher@wellcheck.com').exists():
    teacher = User.objects.create_user(username='teacher', email='teacher@wellcheck.com', password='test123', first_name='Teacher')
    UserProfile.objects.create(user=teacher, user_type='teacher')
    print('Teacher created')
" | python manage.py shell