import os
import shutil
from typing import List, Annotated
from dotenv import load_dotenv
import mysql.connector
from fastapi import FastAPI, Form, Request, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

load_dotenv()

app = FastAPI()

# app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

templates = Jinja2Templates(directory="../frontend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def index_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/admin")
async def admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.post("/test")
async def login_user(email: Annotated[str, Form()], password: Annotated[str, Form()]):
    db_connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    cursor = db_connection.cursor()
    
    query = "SELECT * FROM newestone.users WHERE email = %s"
    cursor.execute(query, (email,))
    data = cursor.fetchone()
    
    cursor.close()
    db_connection.close()
    
    if not data or data[3] != password:
        return RedirectResponse(url="/admin")

    return RedirectResponse(url="/restaurants",status_code=status.HTTP_303_SEE_OTHER)

@app.post("/send")
async def send_data_of_restaurant(
    name: Annotated[str, Form()],
    description: Annotated[str, Form()],
    address: Annotated[str, Form()],
    pictures: Annotated[List[UploadFile], File()]
):
    upload_folder = "../frontend/uploads"

    db_connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    cursor = db_connection.cursor()

    restaurant_query = "INSERT INTO newestone.restaurants (user_id, name, description, address) VALUES (%s, %s, %s, %s)"
    cursor.execute(restaurant_query, (2, name, description, address))
    restaurant_id = cursor.lastrowid

    image_query = "INSERT INTO newestone.image_for_restaurant (restaurant_id, image_url) VALUES (%s, %s)"
    for picture in pictures:
        file_location = os.path.join(upload_folder, picture.filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(picture.file, buffer)
        cursor.execute(image_query, (restaurant_id, f"/uploads/{picture.filename}"))

    db_connection.commit()
    cursor.close()
    db_connection.close()
    
    return RedirectResponse(url="/restaurants", status_code= status.HTTP_303_SEE_OTHER)


@app.post("/editrestaurant")
async def edit_restaurant(
    id : Annotated[int, Form()],
    name: Annotated[str, Form()],
    description: Annotated[str, Form()],
    address: Annotated[str, Form()],
    pictures: Annotated[List[UploadFile], File()]
):
    upload_folder = "../frontend/uploads"

    
    db_connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    cursor = db_connection.cursor()

    delete_old_image_query = "delete from newestone.image_for_restaurant where restaurant_id = %s"
    cursor.execute(delete_old_image_query, (id,))
    db_connection.commit()
    
    
    restaurant_query = "UPDATE newestone.restaurants SET name = %s, description = %s, address = %s WHERE id = %s"    
    cursor.execute(restaurant_query, ( name, description, address, id))
    restaurant_id = id
    image_query = "INSERT INTO newestone.image_for_restaurant (restaurant_id, image_url) VALUES (%s, %s)"
    print(restaurant_id)
    print(name)
    print(description)
    for picture in pictures:
        file_location = os.path.join(upload_folder, picture.filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(picture.file, buffer)
        cursor.execute(image_query, (restaurant_id, f"/uploads/{picture.filename}"))

    db_connection.commit()
    cursor.close()
    db_connection.close()
    
    return RedirectResponse(url="/restaurants", status_code= status.HTTP_303_SEE_OTHER)
    
    
@app.get("/restaurants")
async def show_restaurants_page(request: Request):
    db_connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    cursor = db_connection.cursor()
    
    query = "SELECT * FROM newestone.restaurants"
    cursor.execute(query)
    
    columns = [column[0] for column in cursor.description]
    restaurant_data = [dict(zip(columns, row)) for row in cursor.fetchall()]

    cursor.close()
    db_connection.close()

    return templates.TemplateResponse("db.html", {
        "request": request,
        "restaurants": restaurant_data,
        "active_tab" : "restaurants"
    })


@app.post("/delete-restaurant")
async def delete_by_id(id : Annotated[int, Form()]):
    
    db_connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
     
    cursor = db_connection.cursor()
    
    query = " delete from newestone.restaurants where id = %s"
    print(id)
    cursor.execute(query, (id,))
    # cursor.close()
    db_connection.commit()
    
    return RedirectResponse(url= "/restaurants", status_code= status.HTTP_303_SEE_OTHER)
