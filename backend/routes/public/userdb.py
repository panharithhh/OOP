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
import datetime
router = APIRouter(
    tags=["userdb"]
)

templates = Jinja2Templates(directory="../frontend/templates")

@router.get("/userdash")
async def userdb( 
    request: Request,
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
        ):
    
    cursor = db.cursor(dictionary= True)
    
    client_data_restaurant = "select id,name,description,address,ratings from newestone.restaurants" 
    cursor.execute(client_data_restaurant)
    
    restaurant_client_data = cursor.fetchall()
 
     
    restaurant_id = cursor.lastrowid
    print()
    pic_query = "select * from newestone.image_for_restaurant where restaurant_id = %s"
    
    cursor.execute(pic_query, (restaurant_id, ))
    
    picture = cursor.fetchone()
    
    print(restaurant_client_data) 
    

    
    return templates.TemplateResponse("userdash.html", { 
        "request" : request,
        "restaurant_client_data" : restaurant_client_data,
        "picture" : picture
    })

@router.get("/details/{restaurant_id}")
async def details(
    request: Request,
    restaurant_id: int,
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name, description, address, ratings FROM newestone.restaurants WHERE id = %s", (restaurant_id,))
    restaurant = cursor.fetchone()
    cursor.close()
    db.close()
    
    if restaurant:
        restaurant_data = {
            "restaurant_id": restaurant['id'], 
            "name": restaurant['name'],
            "description": restaurant['description'],
            "address": restaurant['address'],
            "ratings": restaurant['ratings']
        }
        return templates.TemplateResponse("details.html", {"request": request, "restaurant": restaurant_data})
    return templates.TemplateResponse("details.html", {"request": request, "restaurant": None, "error": "Restaurant not found"})

@router.post("/userdb/book")
def book(
    people: Annotated[int, Form(...)],
    date: Annotated[str, Form(...)],
    time: Annotated[str, Form(...)],
    restaurant_id: Annotated[int, Form(...)],
    db: mysql.connector.MySQLConnection = Depends(get_db_connection)
):
    cursor = db.cursor()
    user_id = "userwefw"
    status = "pending"

    datetime = "2025-12-12"
    cursor.execute(
        "INSERT INTO newestone.bookings (order_id, restaurant_id, number_of_guests,booking_datetime, status) VALUES (%s, %s, %s, %s, %s)",
        (user_id, restaurant_id, people,datetime, status)
    )
    db.commit()
    
    cursor.close()
    db.close()
    
    return {"success": True, "message": f"Booking confirmed, status: {status}"}


