# NightBite — Quick Start

## 1) Create & activate a virtual environment
**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

**Windows (PowerShell)**
```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

## 2) Install dependencies
```bash
pip install -r requirements.txt
```

## 3) Create your env file
Create a file named **`password.env`** (or `.env`) in the project root with the following **placeholders** (replace with your own values):

```env
# ---------- Database ----------
DB_HOST=localhost
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password
DB_NAME=your_database_name
EMAIL=your_public_contact_email@example.com

# ---------- Sessions ----------
# Generate a long random string (example): python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=replace_with_long_random_string
SESSION_SECRET=replace_with_long_random_string

# ---------- SMTP (Gmail over STARTTLS on 587) ----------
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURITY=starttls
SMTP_USER=your_gmail_address@example.com
# Use a Gmail *App Password* (not your normal password)
SMTP_PASS=your_16_char_gmail_app_password
EMAIL_FROM="NightBite <your_gmail_address@example.com>"
SMTP_DEBUG=0
```

## 4) Run the server
```bash
# Option A: point to your env file
ENV_FILE=./password.env uvicorn backend.main:app --reload

# Option B: if you named it .env, just:
uvicorn backend.main:app --reload
```

Open: http://127.0.0.1:8000
