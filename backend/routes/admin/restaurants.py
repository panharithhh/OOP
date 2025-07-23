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
    tags=["restaurants"]
)

templates = Jinja2Templates(directory="../frontend/templates")


@router.post("/send")
async def send_data_of_restaurant(
    name: Annotated[str, Form()],
    description: Annotated[str, Form()],
    address: Annotated[str, Form()],
    pictures: Annotated[List[UploadFile], File()],
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    upload_folder = "../frontend/uploads"
    cursor = db.cursor()

    cursor.execute("SELECT id FROM newestone.restaurants WHERE name = %s AND address = %s", (name, address))
    existing = cursor.fetchone()
    if existing:
        restaurant_id = existing[0]
    else:
        cursor.execute(
            "INSERT INTO newestone.restaurants (user_id, name, description, address) VALUES (%s, %s, %s, %s)",
            (2, name, description, address)
        )
        restaurant_id = cursor.lastrowid

    image_query = "INSERT INTO newestone.image_for_restaurant (restaurant_id, image_url) VALUES (%s, %s)"
    for picture in pictures:
        file_location = os.path.join(upload_folder, picture.filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(picture.file, buffer)
        cursor.execute(image_query, (restaurant_id, f"/uploads/{picture.filename}"))

    db.commit()
    cursor.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/editrestaurant")
async def edit_restaurant(
    id: Annotated[int, Form()],
    name: Annotated[str, Form()],
    description: Annotated[str, Form()],
    address: Annotated[str, Form()],
    pictures: Annotated[List[UploadFile], File()],
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    upload_folder = "../frontend/uploads"
    cursor = db.cursor()

    cursor.execute("DELETE FROM newestone.image_for_restaurant WHERE restaurant_id = %s", (id,))
    cursor.execute(
        "UPDATE newestone.restaurants SET name = %s, description = %s, address = %s WHERE id = %s",
        (name, description, address, id)
    )

    image_query = "INSERT INTO newestone.image_for_restaurant (restaurant_id, image_url) VALUES (%s, %s)"
    for picture in pictures:
        file_location = os.path.join(upload_folder, picture.filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(picture.file, buffer)
        cursor.execute(image_query, (id, f"/uploads/{picture.filename}"))

    db.commit()
    cursor.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/delete-restaurant")
async def delete_by_id(
    id: Annotated[int, Form()],
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    cursor = db.cursor()
    cursor.execute("DELETE FROM newestone.restaurants WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

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