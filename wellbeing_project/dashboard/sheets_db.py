import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
from datetime import datetime
import hashlib

class SheetsDB:
    def __init__(self):
        # Get credentials from environment variable
        creds_json = os.environ.get('GOOGLE_SHEETS_CREDS')
        if creds_json:
            creds_dict = json.loads(creds_json)
            scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            self.client = gspread.authorize(creds)
            sheet_id = os.environ.get('SHEET_ID')
            self.sheet = self.client.open_by_key(sheet_id)
        else:
            self.client = None
            self.sheet = None
    
    def get_user_by_email(self, email):
        if not self.sheet:
            return None
        users = self.sheet.worksheet('Users')
        try:
            cell = users.find(email)
            row = users.row_values(cell.row)
            return {
                'username': row[0],
                'email': row[1],
                'password': row[2],
                'user_type': row[3],
                'first_name': row[4] if len(row) > 4 else ''
            }
        except:
            return None
    
    def create_user(self, username, email, password, user_type, first_name=''):
        if not self.sheet:
            return False
        users = self.sheet.worksheet('Users')
        # Hash password
        hashed = hashlib.sha256(password.encode()).hexdigest()
        users.append_row([username, email, hashed, user_type, first_name])
        return True
    
    def verify_password(self, stored_password, provided_password):
        hashed = hashlib.sha256(provided_password.encode()).hexdigest()
        return stored_password == hashed
    
    def add_mood_entry(self, username, mood, comment=''):
        if not self.sheet:
            return False
        moods = self.sheet.worksheet('MoodEntries')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        date = datetime.now().strftime('%Y-%m-%d')
        moods.append_row([username, date, mood, comment, timestamp])
        return True
    
    def get_mood_entries(self, username=None, days=30):
        if not self.sheet:
            return []
        moods = self.sheet.worksheet('MoodEntries')
        all_records = moods.get_all_records()
        
        if username:
            all_records = [r for r in all_records if r['username'] == username]
        
        # Sort by timestamp descending
        all_records.sort(key=lambda x: x['timestamp'], reverse=True)
        return all_records[:days]
    
    def get_todays_mood_summary(self):
        if not self.sheet:
            return {}
        moods = self.sheet.worksheet('MoodEntries')
        all_records = moods.get_all_records()
        today = datetime.now().strftime('%Y-%m-%d')
        
        today_moods = [r for r in all_records if r['date'] == today]
        
        summary = {}
        for record in today_moods:
            mood = record['mood']
            summary[mood] = summary.get(mood, 0) + 1
        
        return summary
    
    def get_all_users(self, user_type='student'):
        if not self.sheet:
            return []
        users = self.sheet.worksheet('Users')
        all_records = users.get_all_records()
        return [r for r in all_records if r['user_type'] == user_type]

# Global instance
db = SheetsDB()