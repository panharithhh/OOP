from typing import List, Annotated, Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import RedirectResponse
import mysql.connector, os, shutil
from models.database import get_db_connection

router = APIRouter(tags=["restaurants"])

@router.post("/send")
async def send_data_of_restaurant(
    name: Annotated[str, Form()],
    description: Annotated[str, Form()],
    longitude: Annotated[float, Form()],
    latitude: Annotated[float, Form()],
    tag: Annotated[Optional[str], Form()] = None,
    price_range: Annotated[str, Form()] = "1",            # <- accept "$", "$$", or "1".."4"
    pictures: Optional[List[UploadFile]] = File(None),
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    pr = price_range
    tag = tag or None

    upload_folder = "../frontend/static"
    os.makedirs(upload_folder, exist_ok=True)
    cur = db.cursor()

    cur.execute(
        "SELECT id FROM newestone.restaurants WHERE name=%s AND longitude=%s AND latitude=%s",
        (name, longitude, latitude),
    )
    row = cur.fetchone()
    if row:
        restaurant_id = row[0]
        cur.execute(
            """UPDATE newestone.restaurants
               SET description=%s, price_range=%s, tag=%s
               WHERE id=%s""",
            (description, pr, tag, restaurant_id),
        )
    else:
        cur.execute(
            """INSERT INTO newestone.restaurants
               (user_id, name, description, longitude, latitude, price_range, tag)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (2, name, description, longitude, latitude, pr, tag),
        )
        restaurant_id = cur.lastrowid

    if pictures:
        for picture in pictures:
            if not picture or not picture.filename:
                continue
            path = os.path.join(upload_folder, picture.filename)
            with open(path, "wb") as f:
                shutil.copyfileobj(picture.file, f)
            cur.execute(
                "INSERT INTO newestone.image_for_restaurant (restaurant_id, image_url) VALUES (%s,%s)",
                (restaurant_id, f"/static/{picture.filename}"),
                
                
            )

    
    db.commit()
    cur.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/editrestaurant")
async def edit_restaurant(
    id: Annotated[int, Form()],
    name: Annotated[str, Form()],
    description: Annotated[str, Form()],
    longitude: Annotated[float, Form()],
    latitude: Annotated[float, Form()],
    tag: Annotated[Optional[str], Form()] = None,
    price_range: Annotated[str, Form()] = "1",            # <- accept "$", "$$", or "1".."4"
    pictures: Optional[List[UploadFile]] = File(None),
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    pr = price_range
    tag = tag or None

    upload_folder = "../frontend/static"
    os.makedirs(upload_folder, exist_ok=True)
    cur = db.cursor()

    cur.execute(
        """UPDATE newestone.restaurants
           SET name=%s, description=%s, longitude=%s, latitude=%s, price_range=%s, tag=%s
           WHERE id=%s""",
        (name, description, longitude, latitude, pr, tag, id),
    )

    if pictures:
        cur.execute("DELETE FROM newestone.image_for_restaurant WHERE restaurant_id=%s", (id,))
        for picture in pictures:
            if not picture or not picture.filename:
                continue
            path = os.path.join(upload_folder, picture.filename)
            with open(path, "wb") as f:
                shutil.copyfileobj(picture.file, f)
            cur.execute(
                "INSERT INTO newestone.image_for_restaurant (restaurant_id, image_url) VALUES (%s,%s)",
                (id, f"/static/{picture.filename}"),
            )

    db.commit()
    cur.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/delete-restaurant", name="delete_restaurant")
async def delete_restaurant(
    id: Annotated[int, Form()],
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    cur = db.cursor()
    try:
        # delete children first (adjust table names to your schema)
        cur.execute("DELETE FROM newestone.image_for_restaurant WHERE restaurant_id=%s", (id,))
        cur.execute("DELETE FROM newestone.menu_items           WHERE restaurant_id=%s", (id,))
        cur.execute("DELETE FROM newestone.events               WHERE restaurant_id=%s", (id,))  # if you have this

        # delete the restaurant
        cur.execute("DELETE FROM newestone.restaurants WHERE id=%s", (id,))
        affected = cur.rowcount

        if affected == 0:
            db.rollback()
            # redirect with a message (or raise 404 if you prefer JSON)
            return RedirectResponse("/dashboard?msg=notfound", status_code=status.HTTP_303_SEE_OTHER)

        db.commit()
    except mysql.connector.Error as e:
        db.rollback()
        # If you still hit FK issues, your FKs don’t reference the tables above—inspect e.errno.
        raise HTTPException(status_code=409, detail=f"Delete failed: {e.msg}")
    finally:
        cur.close()

    return RedirectResponse("/dashboard?msg=deleted", status_code=status.HTTP_303_SEE_OTHER)