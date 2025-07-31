
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

@router.post("/admin_menu")
async def admin_menu_post(id: Annotated[int, Form()], request: Request):
    return RedirectResponse(url=f"/admin_menu/{id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/admin_menu/{restaurant_id}")
async def admin_menu(request: Request, restaurant_id: int, db: mysql.connector.MySQLConnection = Depends(get_db_connection)):
    """Render the Manage Menu page for a specific restaurant."""
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM newestone.restaurants WHERE id = %s", (restaurant_id,))
    restaurant = cursor.fetchone()

    cursor.execute("SELECT * FROM newestone.menu_items WHERE restaurant_id = %s", (restaurant_id,))
    menu_items = cursor.fetchall()
    cursor.close()

    if not restaurant:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        "menu.html",
        {
            "request": request,
            "restaurant": restaurant,
            "menu_items": menu_items,
        },
    )



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

