from fastapi import FastAPI
from routes.public import index, userdb
from routes.admin import auth, dashboard, events, restaurants, menu, bookings
from config.settings import settings
from models.database import get_db_connection
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path


app = FastAPI()

app.include_router(auth.router)
app.include_router(dashboard.router,  tags= ["dashboard"])
app.include_router(events.router, tags=["events"])
app.include_router(restaurants.router,  tags=["restaurants"])
app.include_router(menu.router, tags=["menu"])
app.include_router(bookings.router, tags=["bookings"])

app.include_router(index.router, tags =["index"])
app.include_router(userdb.router, tags= ["userdb"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR   = Path(__file__).resolve().parent
STATIC_DIR = (BASE_DIR / ".." / "frontend" / "static").resolve()

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.on_event("startup")
async def startup():
    print("Server starting up")