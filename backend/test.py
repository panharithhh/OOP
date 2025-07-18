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


@app.get("/admin")
async def admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.post("/test")
async def login_user(
    email: Annotated[str, Form()], 
    password: Annotated[str, Form()],
    db: mysql.connector.MySQLConnection = Depends(get_db)
):
    cursor = db.cursor()
    query = "SELECT * FROM newestone.users WHERE email = %s"
    cursor.execute(query, (email,))
    data = cursor.fetchone()
    cursor.close()
    
    if not data or data[3] != password:
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

    return RedirectResponse(url="/restaurants", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/restaurants")
async def show_restaurants_page(request: Request, db: mysql.connector.MySQLConnection = Depends(get_db)):
    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM newestone.restaurants")
    
    columns = []
    for column in cursor.description:
        columns.append(column[0])
    
    restaurant_data = []
    for row in cursor.fetchall():
        restaurant_data.append(dict(zip(columns, row)))

    cursor.execute("SELECT id, name, event_name, event_description, event_datetime FROM newestone.restaurants")
    
    columns_ev = []
    for col in cursor.description:
        columns_ev.append(col[0])

    event_data = []
    for row in cursor.fetchall():
        event_data.append(dict(zip(columns_ev, row)))

    cursor.close()
    return templates.TemplateResponse("db.html", {
        "request": request,
        "restaurants": restaurant_data,
        "events": event_data,
        "active_tab": "restaurants"
    })

@app.post("/send")
async def send_data_of_restaurant(
    name: Annotated[str, Form()],
    description: Annotated[str, Form()],
    address: Annotated[str, Form()],
    pictures: Annotated[List[UploadFile], File()],
    db: mysql.connector.MySQLConnection = Depends(get_db)
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
    return RedirectResponse(url="/restaurants", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/editrestaurant")
async def edit_restaurant(
    id: Annotated[int, Form()],
    name: Annotated[str, Form()],
    description: Annotated[str, Form()],
    address: Annotated[str, Form()],
    pictures: Annotated[List[UploadFile], File()],
    db: mysql.connector.MySQLConnection = Depends(get_db)
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
    return RedirectResponse(url="/restaurants", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/delete-restaurant")
async def delete_by_id(id: Annotated[int, Form()], db: mysql.connector.MySQLConnection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM newestone.restaurants WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return RedirectResponse(url="/restaurants", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/events")
async def show_events_page(request: Request, db: mysql.connector.MySQLConnection = Depends(get_db)):
    cursor = db.cursor()
    
    cursor.execute("SELECT id, name, event_name, event_description, event_datetime FROM newestone.restaurants")
    
    columns = []
    for column in cursor.description:
        columns.append(column[0])
        
    event_data = []
    for row in cursor.fetchall():
        event_data.append(dict(zip(columns, row)))

    cursor.execute("SELECT id, name FROM newestone.restaurants")
    
    columns_rest = []
    for col in cursor.description:
        columns_rest.append(col[0])

    restaurants = []
    for row in cursor.fetchall():
        restaurants.append(dict(zip(columns_rest, row)))

    cursor.close()
    return templates.TemplateResponse("db.html", {
        "request": request,
        "events": event_data,
        "restaurants": restaurants,
        "active_tab": "special-events"
    })

@app.post("/add-event")
async def add_event(
    restaurant_id: Annotated[int, Form()],
    name: Annotated[str, Form()],
    event_description: Annotated[str, Form()],
    datetime: Annotated[str, Form()],
    db: mysql.connector.MySQLConnection = Depends(get_db)
):
    cursor = db.cursor()
    update_query = "UPDATE newestone.restaurants SET event_name = %s, event_description = %s, event_datetime = %s WHERE id = %s"
    cursor.execute(update_query, (name, event_description, datetime, restaurant_id))
    db.commit()
    cursor.close()
    return RedirectResponse(url="/events", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/delete-event")
async def delete_event_by_id(id: Annotated[int, Form()], db: mysql.connector.MySQLConnection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM newestone.restaurants WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return RedirectResponse(url="/events", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/clear-event")
async def clear_event(id: Annotated[int, Form()], db: mysql.connector.MySQLConnection = Depends(get_db)):
    cursor = db.cursor()
    clear_query = "UPDATE newestone.restaurants SET event_name = NULL, event_description = NULL, event_datetime = NULL WHERE id = %s"
    cursor.execute(clear_query, (id,))
    db.commit()
    cursor.close()
    return RedirectResponse(url="/events", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/menu")
async def return_menu(request: Request, db: mysql.connector.MySQLConnection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM newestone.menu_items")
    
    columns = []
    for column in cursor.description:
        columns.append(column[0])
        
    menu_data = []
    for row in cursor.fetchall():
        menu_data.append(dict(zip(columns, row)))
        
    cursor.close()

    return templates.TemplateResponse("db.html", {
        "request": request,
        "menu_data": menu_data,
        "active_tab": "menu"
    })

@app.post("/add-menu-item")
async def add_menu(db: mysql.connector.MySQLConnection = Depends(get_db)):
    cursor = db.cursor()
    db.commit()
    cursor.close()
    return RedirectResponse(url="/menu", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/delete")
async def delete_item(db: mysql.connector.MySQLConnection = Depends(get_db)):
    cursor = db.cursor()
    db.commit()
    cursor.close()
    return RedirectResponse(url="/menu", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/confirmation")
async def confirm_booking():
    pass

@app.post("/cancel")
async def cancel_booking():
    pass

@app.post("/clear-the-booking-board")
async def clear_booking_board():
    pass

@app.post("/authentication")
async def authentication():
    pass


@app.post("/dashboard")
async def dashboard(request = Request):
    
    pass