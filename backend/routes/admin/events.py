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
    tags=["index"]
)

templates = Jinja2Templates(directory="../frontend/templates")


@router.post("/add-event")
async def add_event(
    restaurant_id: Annotated[int, Form()],
    name: Annotated[str, Form()],
    event_description: Annotated[str, Form()],
    datetime: Annotated[str, Form()],
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    cursor = db.cursor()
    update_query = "insert into newestone.events (event_name,event_description,event_datetime, restaurant_id) values (%s,%s,%s,%s) "
    cursor.execute(update_query, (name, event_description, datetime, restaurant_id))
    db.commit()
    cursor.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/clear-event")
async def clear_event(
    id: Annotated[int, Form()],
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    cursor = db.cursor()
    clear_query = "delete from newestone.events WHERE id = %s"
    cursor.execute(clear_query, (id,))
    db.commit()
    cursor.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    