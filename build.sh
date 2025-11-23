#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
```

## **Step 3: Add to Google Sheet**

Manually add test users to your Google Sheet:

**Users sheet:**
```
username | email | password | user_type | first_name
afnan | afnan.messaging@gmail.com | 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 | student | Afnan
teacher | teacher@wellcheck.com | 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08 | teacher | Teacher