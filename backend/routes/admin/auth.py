# auth_routes.py
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated
from pathlib import Path
import os, random, time
import mysql.connector

from models.database import get_db_connection
from .smtp_helper import send_email

router = APIRouter()

# Resolve templates as <project-root>/frontend/templates
PROJECT_ROOT = Path(__file__).resolve().parents[2].parent
TEMPLATES_DIR = (PROJECT_ROOT / "frontend" / "templates").resolve()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

PRINT_OTP = os.getenv("PRINT_OTP", "1") == "1"

@router.get("/admin")
async def admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@router.post("/login-otp")
async def login_user(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    # Validate credentials (plain-text compare with encrypted_password)
    cur = db.cursor()
    cur.execute(
        "SELECT 1 FROM newestone.users WHERE email=%s AND encrypted_password=%s LIMIT 1",
        (email, password),
    )
    ok = cur.fetchone()
    cur.close()

    if not ok:
        return RedirectResponse(url="/admin?err=badcreds", status_code=status.HTTP_303_SEE_OTHER)

    # Generate/store OTP in session
    code = f"{random.randint(0, 999999):06d}"
    request.session["otp"] = code
    request.session["otp_exp"] = int(time.time()) + 300  # 5 minutes
    request.session["otp_email"] = email

    if PRINT_OTP:
        print(f"[DEV OTP] {code} -> {email}")

    # Send email (do not clear OTP if it fails)
    try:
        send_email(
            to=email,
            subject="Your login code",
            text=f"Your OTP is {code}. It expires in 5 minutes."
        )
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")

    return RedirectResponse(url="/auth", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/auth")
async def to_auth_page(request: Request):
    return templates.TemplateResponse("authentication.html", {"request": request})

@router.post("/otp-verify")
async def otp_verify(
    request: Request,
    auth_code: Annotated[str, Form(alias="auth_code")]
):
    otp = request.session.get("otp")
    otp_exp = request.session.get("otp_exp")
    otp_email = request.session.get("otp_email")
    now = int(time.time())

    if not otp or not otp_exp or now > otp_exp:
        request.session.pop("otp", None)
        request.session.pop("otp_exp", None)
        request.session.pop("otp_email", None)
        return RedirectResponse(url="/admin?err=expired", status_code=status.HTTP_303_SEE_OTHER)

    if auth_code.strip() != str(otp):
        return RedirectResponse(url="/auth?err=badotp", status_code=status.HTTP_303_SEE_OTHER)

    # Success
    request.session.pop("otp", None)
    request.session.pop("otp_exp", None)
    request.session["user_email"] = otp_email
    request.session.pop("otp_email", None)

    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/mail-debug")
async def mail_debug():
    import os
    return {
        "SMTP_USER": os.getenv("SMTP_USER"),
        "EMAIL_FROM": os.getenv("EMAIL_FROM"),
        "SMTP_HOST": os.getenv("SMTP_HOST"),
        "SMTP_PORT": os.getenv("SMTP_PORT"),
        "SMTP_SECURITY": os.getenv("SMTP_SECURITY"),
    }
 