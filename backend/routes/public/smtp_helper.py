# routes/admin/smtp_helper.py
import os, smtplib, ssl
from email.message import EmailMessage
from pathlib import Path
from dotenv import load_dotenv

def _load_env():
    env_file = os.getenv("ENV_FILE")
    if env_file:
        p = Path(env_file).expanduser()
        if p.exists():
            load_dotenv(dotenv_path=p, override=True)
    here = Path(__file__).resolve()
    for p in (here.parents[3]/".env", here.parents[2]/".env", here.parents[1]/".env", here.parent/".env", Path.cwd()/".env"):
        if p.exists():
            load_dotenv(dotenv_path=p, override=True)
            break
    else:
        load_dotenv(override=True)

def send_email(to: str, subject: str, text: str, html: str | None = None) -> None:
    _load_env()
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    pwd = os.getenv("SMTP_PASS", "")
    from_ = os.getenv("SMTP_FROM", user or "no-reply@example.com")
    use_ssl = os.getenv("SMTP_USE_SSL", "0") == "1"
    use_starttls = os.getenv("SMTP_STARTTLS", "1") == "1"
    debug = os.getenv("SMTP_DEBUG", "0") == "1"
    if not (host and port and user and pwd):
        raise RuntimeError("SMTP config missing")
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
