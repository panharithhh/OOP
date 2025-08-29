# backend/main.py
from pathlib import Path
import os
from dotenv import load_dotenv

DEFAULT_ENV_PATH = "/Users/cheapanharith/developer/OOPproject/password.env"

def _load_env():
    env_file = os.getenv("ENV_FILE", DEFAULT_ENV_PATH)
    candidates = [Path(env_file).expanduser().resolve()]
    here = Path(__file__).resolve().parent
    candidates += [here / ".env", here.parent / ".env", Path.cwd() / ".env"]
    for up in list(here.parents)[:6]:
        candidates.append(up / ".env")
    tried = []
    for p in candidates:
        try:
            tried.append(str(p))
            if p.exists():
                load_dotenv(dotenv_path=p, override=True)
                print(f"[ENV] Loaded {p}")
                break
        except Exception:
            pass
    else:
        load_dotenv(override=True)
        print(f"[ENV] .env not found. Tried: {tried}")

_load_env()

print(
    "[MAIL CFG]",
    "SMTP_USER=", os.getenv("SMTP_USER"),
    "EMAIL_FROM=", os.getenv("EMAIL_FROM"),
    "HOST=", os.getenv("SMTP_HOST"),
    "PORT=", os.getenv("SMTP_PORT"),
)

from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    import secrets as _secrets
    SECRET_KEY = _secrets.token_urlsafe(32)
    print("WARNING: Using ephemeral SECRET_KEY. Set SECRET_KEY in .env for persistent sessions.")

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="nb_session",
    max_age=60 * 60 * 24,
    same_site="lax",
    https_only=False,
)

origins_env = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
allow_origins = [o.strip() for o in origins_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = (BASE_DIR / ".." / "frontend").resolve()
STATIC_DIR = FRONTEND_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

from routes.public.index import router as index_router
from routes.public.userdb import router as userdb_router
from routes.public.booking import router as booking_router, rating_router as booking_rating_router

from routes.admin.auth import router as auth_router
from routes.admin.dashboard import router as dashboard_router
from routes.admin.events import router as events_router
from routes.admin.restaurants import router as restaurants_router
from routes.admin.menu import router as menu_router
from routes.admin.bookings import router as admin_bookings_router

app.include_router(index_router)
app.include_router(userdb_router)
app.include_router(booking_router)
app.include_router(booking_rating_router)

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(events_router)
app.include_router(restaurants_router)
app.include_router(menu_router)
app.include_router(admin_bookings_router)

try:
    from routes.admin.smtp_helper import send_email as _smtp_send
except Exception:
    _smtp_send = None

@app.post("/_smtp/test")
async def _smtp_test(to: str = Form(...)):
    if _smtp_send is None:
        return {"ok": False, "error": "smtp_helper_unavailable"}
    _smtp_send(to, "SMTP Test", "SMTP OK", "<b>SMTP OK</b>")
    return {"ok": True}

@app.on_event("startup")
async def startup():
    print("Server starting up")

@app.get("/healthz")
def healthz():
    return {"ok": True}
