import os
import shutil
from typing import List, Annotated
from dotenv import load_dotenv
import mysql.connector
from fastapi import FastAPI, Form, Request, status, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

load_dotenv()

app = FastAPI()

templates = Jinja2Templates(directory="../frontend")

def get_db():
    db_connection = None
    try:
        db_connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        yield db_connection
    finally:
        if db_connection:
            db_connection.close()

@app.get("/")
async def index_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/authentication")
async def authentication(request : Request):
    pass
@app.get("/admin")
async def admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.post("/test")
async def login_user(
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db: mysql.connector.MySQLConnection = Depends(get_db),
):
    cursor = db.cursor()
    query = "SELECT * FROM newestone.users WHERE email = %s"
    cursor.execute(query, (email,))
    data = cursor.fetchone()
    cursor.close()
    
    if not data or data[3] != password:
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/dashboard")
async def dashboard(
    request: Request,
    db: mysql.connector.MySQLConnection = Depends(get_db),
):
    cursor = db.cursor(dictionary=True)
    
    q = "select * from newestone.restaurants"
    cursor.execute(q)
    restaurant_data = cursor.fetchall()
    
    q2 = "select * from newestone.menu_items"
    cursor.execute(q2)
    menu_data = cursor.fetchall()
    
    cursor.execute("select * from newestone.bookings") 
    bookings = cursor.fetchall()
    cursor.close() 
    return templates.TemplateResponse("db.html", {
        "request": request,
        "restaurants": restaurant_data,
        "menu_data": menu_data,
        "bookings" : bookings, 
        "active_tab" : "tab" 
    })

@app.post("/send")
async def send_data_of_restaurant(
    name: Annotated[str, Form()],
    description: Annotated[str, Form()],
    address: Annotated[str, Form()],
    pictures: Annotated[List[UploadFile], File()],
    db: mysql.connector.MySQLConnection = Depends(get_db),
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

@app.post("/editrestaurant")
async def edit_restaurant(
    id: Annotated[int, Form()],
    name: Annotated[str, Form()],
    description: Annotated[str, Form()],
    address: Annotated[str, Form()],
    pictures: Annotated[List[UploadFile], File()],
    db: mysql.connector.MySQLConnection = Depends(get_db),
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

@app.post("/delete-restaurant")
async def delete_by_id(
    id: Annotated[int, Form()],
    db: mysql.connector.MySQLConnection = Depends(get_db),
):
    cursor = db.cursor()
    cursor.execute("DELETE FROM newestone.restaurants WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/add-event")
async def add_event(
    restaurant_id: Annotated[int, Form()],
    name: Annotated[str, Form()],
    event_description: Annotated[str, Form()],
    datetime: Annotated[str, Form()],
    db: mysql.connector.MySQLConnection = Depends(get_db),
):
    cursor = db.cursor()
    update_query = "UPDATE newestone.restaurants SET event_name = %s, event_description = %s, event_datetime = %s WHERE id = %s"
    cursor.execute(update_query, (name, event_description, datetime, restaurant_id))
    db.commit()
    cursor.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/delete-event")
async def delete_event_by_id(
    id: Annotated[int, Form()],
    db: mysql.connector.MySQLConnection = Depends(get_db),
):
    cursor = db.cursor()
    cursor.execute("DELETE FROM newestone.restaurants WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/clear-event")
async def clear_event(
    id: Annotated[int, Form()],
    db: mysql.connector.MySQLConnection = Depends(get_db),
):
    cursor = db.cursor()
    clear_query = "UPDATE newestone.restaurants SET event_name = NULL, event_description = NULL, event_datetime = NULL WHERE id = %s"
    cursor.execute(clear_query, (id,))
    db.commit()
    cursor.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    

@app.post("/delete-menu-item")
async def delete_item(id : Annotated[int, Form()], db: mysql.connector.MySQLConnection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("delete from newestone.menu_items where id = %s",(id,))
    db.commit()
    cursor.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/confirm-booking")
async def confirm_booking(
    id : Annotated[int, Form()],     
    db: mysql.connector.MySQLConnection = Depends(get_db),
):
    cursor = db.cursor()
    cursor.execute ("Update newestone.bookings set status = 'confirmed' where id = %s",(id,) )
    db.commit()
    cursor.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/pend-booking")
async def cancel_booking(
    id : Annotated[int, Form()],     
    db: mysql.connector.MySQLConnection = Depends(get_db),
):
    cursor = db.cursor()
    cursor.execute("Update newestone.bookings set status = 'pending' where id = %s",(id,) )
    db.commit()
    cursor.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/cancel-booking")
async def cancel_booking(
    id : Annotated[int, Form()],     
    db: mysql.connector.MySQLConnection = Depends(get_db),
):
    cursor = db.cursor()
    cursor.execute("Update newestone.bookings set status = 'cancelled' where id = %s",(id,) )
    db.commit()
    cursor.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/clear-the-booking-board")
async def clear_booking_board():
    pass


@app.post("/add-menu-item")
async def add_menu_item(
    restaurant_id: Annotated[int, Form()],
    name: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price: Annotated[float, Form()],
    picture: Annotated[UploadFile, File()],
    db: mysql.connector.MySQLConnection = Depends(get_db),
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

