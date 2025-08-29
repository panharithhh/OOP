# routes/public/booking.py
from __future__ import annotations
from typing import Optional, Dict, Any
from pathlib import Path
import os, random, time, smtplib, ssl, inspect
from email.message import EmailMessage

import mysql.connector
from fastapi import APIRouter, Request, Depends, Form, BackgroundTasks, status, Body, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from models.database import get_db_connection

try:
    from ..admin.smtp_helper import send_email  # flexible helper (may not match our call sig)
except Exception:
    send_email = None  # type: ignore

# ---------- templates ----------
BACKEND_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
TEMPLATES_DIR = FRONTEND_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ---------- routers ----------
router = APIRouter(prefix="/booking", tags=["booking"])
rating_router = APIRouter(tags=["booking"])  # root-level /rate-restaurant

# ---------- utils ----------
def _now_ts() -> int:
    return int(time.time())

def _gen_otp() -> str:
    return f"{random.randint(0, 999999):06d}"

def _get_session_payload(request: Request) -> Optional[Dict[str, Any]]:
    return request.session.get("pending_booking")

def _set_session_payload(request: Request, payload: Dict[str, Any]) -> None:
    request.session["pending_booking"] = payload

def _clear_session_payload(request: Request) -> None:
    for k in ("pending_booking", "booking_otp", "booking_otp_exp"):
        request.session.pop(k, None)

def _first_non_empty(*values, default=None):
    for v in values:
        if v is not None and str(v).strip() != "":
            return v
    return default

def _compose_when(date_str: Optional[str], time_str: Optional[str], fallback: Optional[str]) -> Optional[str]:
    d = (date_str or "").strip() if date_str else ""
    t = (time_str or "").strip() if time_str else ""
    if d and t:
        suf = ":00" if len(t) <= 5 else ""
        return f"{d} {t}{suf}"
    return (fallback or "").strip() or None

# ---------- DB helpers ----------
def _fetch_restaurant(db: mysql.connector.MySQLConnection, rid: Any) -> Optional[Dict[str, Any]]:
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT id, name, COALESCE(ratings,0) AS ratings FROM newestone.restaurants WHERE id=%s", (rid,))
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    return {"restaurant_id": row["id"], "name": row["name"], "ratings": row["ratings"]}

def _update_restaurant_rating(db: mysql.connector.MySQLConnection, rid: Any, rating: float) -> bool:
    cur = db.cursor()
    try:
        cur.execute("UPDATE newestone.restaurants SET ratings=%s WHERE id=%s", (rating, rid))
        db.commit()
        return True
    except mysql.connector.Error:
        db.rollback()
        return False
    finally:
        cur.close()

def _insert_booking(db: mysql.connector.MySQLConnection, payload: Dict[str, Any]) -> None:
    cur = db.cursor()
    try:
        order_id = f"NB{_now_ts()}{random.randint(100,999)}"
        cur.execute(
            """
            INSERT INTO newestone.bookings
              (order_id, restaurant_id, number_of_guests, booking_datetime, status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (order_id, payload["restaurant_id"], int(payload["people"]), payload["booking_datetime"], "confirmed"),
        )
        db.commit()
    finally:
        cur.close()

# ---------- SMTP (robust: helper OR direct smtplib) ----------
def _smtp_send_direct(to: str, subject: str, text: str, html: Optional[str]) -> None:
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    pwd = os.getenv("SMTP_PASS", "")
    from_ = os.getenv("SMTP_FROM") or os.getenv("EMAIL_FROM") or user or "no-reply@example.com"
    use_ssl = os.getenv("SMTP_USE_SSL", "0") == "1"
    use_starttls = os.getenv("SMTP_STARTTLS", "1") == "1"
    debug = os.getenv("SMTP_DEBUG", "0") == "1"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_
    msg["To"] = to
    msg.set_content(text or "")
    if html:
        msg.add_alternative(html, subtype="html")

    if use_ssl:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=20) as s:
            s.set_debuglevel(1 if debug else 0)
            s.login(user, pwd)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=20) as s:
            s.set_debuglevel(1 if debug else 0)
            if use_starttls:
                s.starttls(context=ssl.create_default_context())
            s.login(user, pwd)
            s.send_message(msg)

def _try_helper(background: BackgroundTasks, to: str, subject: str, text: str, html: str) -> bool:
    if not send_email:
        return False
    try:
        sig = inspect.signature(send_email)
        params = list(sig.parameters.keys())
        # Prefer kwargs if possible (handles most variants)
        bound = {}
        if "to" in params: bound["to"] = to
        if "email" in params and "to" not in params: bound["email"] = to
        if "subject" in params: bound["subject"] = subject
        if "text" in params or "body" in params:
            key = "text" if "text" in params else "body"
            bound[key] = text
        if "html" in params:
            bound["html"] = html
        # Fallback to positional based on arity
        if not bound:
            arity = len(params)
            if arity >= 4:
                background.add_task(send_email, to, subject, text, html)
            elif arity == 3:
                background.add_task(send_email, to, subject, html)
            else:
                background.add_task(send_email, to, subject)
        else:
            background.add_task(send_email, **bound)
        return True
    except Exception as e:
        print(f"[SMTP helper failed] {type(e).__name__}: {e}")
        return False

def _send_otp_email(background: BackgroundTasks, email: str, code: str) -> None:
    subject = "Your NIGHTBITE booking code"
    text = f"Your verification code is {code}. It expires in 5 minutes."
    html = f"Your verification code is <b>{code}</b>. It expires in 5 minutes."
    if not _try_helper(background, email, subject, text, html):
        background.add_task(_smtp_send_direct, email, subject, text, html)
        print(f"[SMTP direct queued] to={email}")

# ---------- Routes ----------
@router.post("/start")
async def start_booking(
    request: Request,
    email: Optional[str] = Form(None),
    email_form: Optional[str] = Form(None),
    restaurant_id: Optional[str] = Form(None),
    people: Optional[int] = Form(None),
    booking_datetime: Optional[str] = Form(None),
    date: Optional[str] = Form(None),
    time_: Optional[str] = Form(None, alias="time"),
    body: Optional[Dict[str, Any]] = Body(None),
    q_email: Optional[str] = Query(None, alias="email"),
    q_restaurant_id: Optional[str] = Query(None, alias="restaurant_id"),
    q_people: Optional[int] = Query(None, alias="people"),
    q_when: Optional[str] = Query(None, alias="when"),
    q_date: Optional[str] = Query(None, alias="date"),
    q_time: Optional[str] = Query(None, alias="time"),
    background: BackgroundTasks = None,
):
    json_data = body if isinstance(body, dict) else {}
    merged_email = _first_non_empty(email, email_form, json_data.get("email_form"), json_data.get("email"), q_email)
    merged_rid = _first_non_empty(restaurant_id, json_data.get("restaurant_id"), q_restaurant_id)
    merged_people = _first_non_empty(people, json_data.get("people"), q_people, default=1)
    merged_when = _compose_when(
        date or q_date or json_data.get("date"),
        time_ or q_time or json_data.get("time"),
        _first_non_empty(booking_datetime, json_data.get("booking_datetime"), q_when),
    )

    try:
        merged_people = int(merged_people) if merged_people is not None else 1
    except Exception:
        merged_people = 1

    payload = {
        "email": (merged_email or "").strip() if merged_email else None,
        "restaurant_id": merged_rid,
        "people": merged_people,
        "booking_datetime": merged_when,
    }

    if not payload["email"] or not payload["restaurant_id"] or not payload["booking_datetime"]:
        _set_session_payload(request, {k: v for k, v in payload.items() if v is not None})
        return RedirectResponse(url="/booking/confirm", status_code=status.HTTP_303_SEE_OTHER)

    _set_session_payload(request, payload)
    code = _gen_otp()
    request.session["booking_otp"] = code
    request.session["booking_otp_exp"] = _now_ts() + 300
    _send_otp_email(background, payload["email"], code)
    return RedirectResponse(url="/booking/confirm", status_code=status.HTTP_303_SEE_OTHER, background=background)

@router.get("/confirm")
async def confirm_page(request: Request, db: mysql.connector.MySQLConnection = Depends(get_db_connection)):
    pending = _get_session_payload(request)
    if not pending:
        return RedirectResponse(url="/userdash", status_code=status.HTTP_303_SEE_OTHER)
    rid = pending.get("restaurant_id")
    restaurant = _fetch_restaurant(db, rid) if rid is not None else None
    if not restaurant and rid is not None:
        restaurant = {"restaurant_id": rid, "ratings": None, "name": None}
    dev_otp = request.session.get("booking_otp") if os.getenv("DEBUG_SHOW_OTP", "0") == "1" else None
    return templates.TemplateResponse("booking_confirm.html", {"request": request, "payload": pending, "restaurant": restaurant, "dev_otp": dev_otp})

@router.post("/verify")
async def verify_code(request: Request, code: str = Form(...), db: mysql.connector.MySQLConnection = Depends(get_db_connection)):
    pending = _get_session_payload(request)
    if not pending:
        return RedirectResponse(url="/userdash", status_code=status.HTTP_303_SEE_OTHER)
    saved = request.session.get("booking_otp")
    exp = int(request.session.get("booking_otp_exp", 0))
    now = _now_ts()
    if not saved or now > exp:
        return RedirectResponse(url="/booking/confirm?err=expired", status_code=status.HTTP_303_SEE_OTHER)
    if code.strip() != str(saved):
        return RedirectResponse(url="/booking/confirm?err=badcode", status_code=status.HTTP_303_SEE_OTHER)
    try:
        _insert_booking(db, pending)
    finally:
        _clear_session_payload(request)
    return RedirectResponse(url="/dashboard?msg=booked", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/resend")
async def resend_code(request: Request, background: BackgroundTasks):
    pending = _get_session_payload(request)
    if not pending or not pending.get("email"):
        return RedirectResponse(url="/booking/confirm", status_code=status.HTTP_303_SEE_OTHER)
    code = _gen_otp()
    request.session["booking_otp"] = code
    request.session["booking_otp_exp"] = _now_ts() + 300
    _send_otp_email(background, pending["email"], code)
    return RedirectResponse(url="/booking/confirm?msg=resent", status_code=status.HTTP_303_SEE_OTHER, background=background)

@router.post("/cancel")
async def cancel_booking(request: Request):
    _clear_session_payload(request)
    return RedirectResponse(url="/userdash?msg=cancelled", status_code=status.HTTP_303_SEE_OTHER)

@rating_router.post("/rate-restaurant")
async def rate_restaurant(
    request: Request,
    restaurant_id: str = Form(...),
    rating: float = Form(...),
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    try:
        rating = float(rating)
        if rating < 0 or rating > 5:
            raise ValueError
    except Exception:
        return RedirectResponse(url="/booking/confirm?err=rating", status_code=status.HTTP_303_SEE_OTHER)

    ok = _update_restaurant_rating(db, restaurant_id, rating)
    if not ok:
        return RedirectResponse(url="/booking/confirm?err=rating", status_code=status.HTTP_303_SEE_OTHER)

    return RedirectResponse(url="/booking/confirm?msg=rated", status_code=status.HTTP_303_SEE_OTHER)
