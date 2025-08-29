# routes/admin/smtp_helper.py
import os, smtplib
from email.message import EmailMessage
from pathlib import Path
from dotenv import load_dotenv

def _load_env_for_mail():
    # 1) Honor ENV_FILE or default to your real path
    env_file = os.getenv("ENV_FILE", "/Users/cheapanharith/developer/OOPproject/password.env")  # <-- your real path
    ef = Path(env_file).expanduser()
    if ef.exists():
        load_dotenv(dotenv_path=ef, override=True)
        print(f"[SMTP] Loaded {ef}")
        return

    # 2) Fallbacks
    here = Path(__file__).resolve()
    for p in (here.parents[3]/".env", here.parents[2]/".env", here.parents[1]/".env", here.parent/".env", Path.cwd()/".env"):
        if p.exists():
            load_dotenv(dotenv_path=p, override=True)
            print(f"[SMTP] Loaded {p}")
            return
    load_dotenv(override=True)
    print("[SMTP] .env not found by helper; using process env")

def _cfg():
    _load_env_for_mail()
    host       = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port       = int(os.getenv("SMTP_PORT", "587"))
    security   = os.getenv("SMTP_SECURITY", "starttls").lower()
    user       = os.getenv("SMTP_USER")
    pwd        = os.getenv("SMTP_PASS")
    email_from = os.getenv("EMAIL_FROM") or user
    debug      = os.getenv("SMTP_DEBUG", "0") == "1"
    return host, port, security, user, pwd, email_from, debug

def send_email(to: str, subject: str, text: str):
    host, port, security, user, pwd, email_from, debug = _cfg()
    print(f"[SMTP CONFIG] host={host} port={port} sec={security} user={user} from={email_from}")

    if not user or not pwd:
        raise RuntimeError("SMTP_USER/SMTP_PASS not set (Gmail requires auth)")
    if not email_from:
        raise RuntimeError("EMAIL_FROM not set (or SMTP_USER missing)")
    if user and user.lower() not in (email_from or "").lower():
        raise RuntimeError("EMAIL_FROM must include SMTP_USER (or be a verified Gmail alias)")

    msg = EmailMessage()
    msg["From"] = email_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)

    server = smtplib.SMTP_SSL(host, port, timeout=20) if security == "ssl" else smtplib.SMTP(host, port, timeout=20)
    try:
        if debug: server.set_debuglevel(1)
        server.ehlo()
        if security == "starttls":
            server.starttls(); server.ehlo()
        server.login(user, pwd)
        server.send_message(msg)
    finally:
        try: server.quit()
        except Exception: pass
