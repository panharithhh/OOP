from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    Form,
    Request,
    status,
    UploadFile
)
from fastapi.templating import Jinja2Templates
from models.database import get_db_connection
import mysql.connector
from fastapi.responses import RedirectResponse
from config.settings import settings
import os
import shutil
from typing import List, Annotated
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import smtplib


router = APIRouter(
    tags=["dashboard"]
)

templates = Jinja2Templates(directory="../frontend/templates")



@router.get("/dashboard")
async def dashboard(
    request: Request,
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    cursor = db.cursor(dictionary=True)
    
    q = "select * from newestone.restaurants"
    cursor.execute(q)
    restaurant_data = cursor.fetchall()
    
    q2 = "select * from newestone.menu_items"
    cursor.execute(q2)
    menu_data = cursor.fetchall()
    
    cursor.execute("select * from newestone.events")
    events = cursor.fetchall()
    
    cursor.execute("select * from newestone.bookings") 
    bookings = cursor.fetchall()
    cursor.close() 
    return templates.TemplateResponse(
        "db.html",
        {
            "request": request,
            "restaurants": restaurant_data,
            "menu_data": menu_data,
            "bookings": bookings,
            "events" : events
         
        },
    )