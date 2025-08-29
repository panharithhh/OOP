# routes/admin/menu.py
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Annotated, Optional
import mysql.connector
import os, shutil, uuid

from models.database import get_db_connection

router = APIRouter(tags=["menu"])

# --- Resolve paths robustly (independent of where uvicorn is started) ---
# This file lives at .../backend/routes/admin/menu.py
BACKEND_DIR = Path(__file__).resolve().parents[2]           # .../backend
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"              # .../frontend
TEMPLATES_DIR = FRONTEND_DIR / "templates"
STATIC_DIR = FRONTEND_DIR / "static"                        # <— where we will save images
STATIC_DIR.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.post("/admin_menu")
async def admin_menu_post(id: Annotated[int, Form()], request: Request):
    return RedirectResponse(url=f"/admin_menu/{id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/admin_menu/{restaurant_id}")
async def admin_menu(
    request: Request,
    restaurant_id: int,
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM newestone.restaurants WHERE id = %s", (restaurant_id,))
    restaurant = cur.fetchone()

    cur.execute("SELECT * FROM newestone.menu_items WHERE restaurant_id = %s", (restaurant_id,))
    menu_items = cur.fetchall()
    cur.close()

    if not restaurant:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        "menu.html",
        {"request": request, "restaurant": restaurant, "menu_items": menu_items},
    )


@router.post("/add-menu-item")
async def add_menu_item(
    restaurant_id: Annotated[int, Form(...)],
    name: Annotated[str, Form(...)],
    description: Annotated[str, Form(...)],
    price: Annotated[float, Form(...)],
    picture: Optional[UploadFile] = File(None),
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    """
    Saves the uploaded picture into frontend/static and writes '/static/<filename>'
    into newestone.menu_items.image_url.
    """
    image_url_path: Optional[str] = None

    if picture and picture.filename:
        # Create a unique, safe filename in /frontend/static
        suffix = Path(picture.filename).suffix.lower()[:10]  # keep extension
        unique_name = f"menu_{uuid.uuid4().hex[:12]}{suffix}"
        file_path = STATIC_DIR / unique_name

        # Persist bytes
        with open(file_path, "wb") as buf:
            shutil.copyfileobj(picture.file, buf)

        # URL that the browser can load (app must mount /static -> FRONTEND_DIR/static)
        image_url_path = f"/static/{unique_name}"

    cur = db.cursor()
    cur.execute(
        """
        INSERT INTO newestone.menu_items
            (item_name, description, price, image_url, restaurant_id)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (name, description, price, image_url_path, restaurant_id),
    )
    db.commit()
    cur.close()

    # Go back to this restaurant's menu page
    return RedirectResponse(url=f"/admin_menu/{restaurant_id}?msg=added", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/delete-menu-item")
async def delete_item(
    id: Annotated[int, Form(...)],
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    cur = db.cursor()

    # Optional: fetch image path to delete file from disk too
    cur.execute("SELECT image_url, restaurant_id FROM newestone.menu_items WHERE id=%s", (id,))
    row = cur.fetchone()
    restaurant_id = row[1] if row else None
    if row and row[0]:
        # Expecting URLs like /static/filename.jpg
        try:
            filename = Path(str(row[0])).name
            file_on_disk = STATIC_DIR / filename
            if file_on_disk.exists():
                file_on_disk.unlink(missing_ok=True)
        except Exception:
            pass

    cur.execute("DELETE FROM newestone.menu_items WHERE id=%s", (id,))
    db.commit()
    cur.close()

    # If we know the restaurant, take the user back there; else go to dashboard
    if restaurant_id:
        return RedirectResponse(url=f"/admin_menu/{restaurant_id}?msg=deleted", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)