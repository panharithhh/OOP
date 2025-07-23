
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
    tags=["menu"]
)

templates = Jinja2Templates(directory="../frontend/templates")



@router.post("/add-menu-item")
async def add_menu_item(
    restaurant_id: Annotated[int, Form()],
    name: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price: Annotated[float, Form()],
    picture: Annotated[UploadFile, File()],
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    upload_folder = "../frontend/uploads"
    os.makedirs(upload_folder, exist_ok=True)

    file_location = os.path.join(upload_folder, picture.filename)
    
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(picture.file, buffer)
        
    image_url_path = f"/uploads/{picture.filename}"

    cursor = db.cursor()
    
    query = """
        INSERT INTO newestone.menu_items 
        (item_name, description, price, image_url, restaurant_id) 
        VALUES (%s, %s, %s, %s, %s)
    """
    
    cursor.execute(query, (name, description, price, image_url_path, restaurant_id))
    
    db.commit()
    
    cursor.close()
    
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)



@router.post("/delete-menu-item")
async def delete_item(id : Annotated[int, Form()], db: mysql.connector.MySQLConnection = Depends(get_db_connection)):
    cursor = db.cursor()
    cursor.execute("delete from newestone.menu_items where id = %s",(id,))
    db.commit()
    cursor.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

